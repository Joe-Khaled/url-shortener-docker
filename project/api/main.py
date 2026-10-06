"""Snip API -- a tiny URL shortener.

PostgreSQL is the source of truth for links and click counts.
Redis holds short-lived, rebuildable data:
  - a per-client rate limit on creating links
  - a cached copy of the /api/stats summary
If Redis is unavailable the API keeps working: the rate limit is
skipped and stats are read straight from PostgreSQL.
"""

import logging
import os
import secrets
import string
import time
from contextlib import asynccontextmanager

import psycopg2
import redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, HttpUrl

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("snip-api")


def read_setting(name: str, default: str | None = None) -> str | None:
    """Read NAME from the environment, or from the file at NAME_FILE.

    The *_FILE form lets a secret be mounted as a file instead of being
    passed as a plain environment variable.
    """
    file_path = os.environ.get(f"{name}_FILE")
    if file_path:
        with open(file_path, encoding="utf-8") as fh:
            return fh.read().strip()
    return os.environ.get(name, default)


APP_ENV = read_setting("APP_ENV", "development")

DB_HOST = read_setting("DB_HOST", "localhost")
DB_PORT = int(read_setting("DB_PORT", "5432"))
DB_NAME = read_setting("DB_NAME", "snip")
DB_USER = read_setting("DB_USER", "snip")
DB_PASSWORD = read_setting("DB_PASSWORD")

REDIS_HOST = read_setting("REDIS_HOST", "localhost")
REDIS_PORT = int(read_setting("REDIS_PORT", "6379"))
REDIS_PASSWORD = read_setting("REDIS_PASSWORD")

RATE_LIMIT_PER_MINUTE = int(read_setting("RATE_LIMIT_PER_MINUTE", "10"))
STATS_TTL_SECONDS = 10
CODE_LENGTH = 7
CODE_ALPHABET = string.ascii_letters + string.digits

cache = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    socket_connect_timeout=1,
    socket_timeout=1,
    decode_responses=True,
)


# --------------------------------------------------------------------------
# PostgreSQL
# --------------------------------------------------------------------------

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3,
    )


def init_db():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS links (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(16) NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    clicks INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Redis helpers -- every call is allowed to fail
# --------------------------------------------------------------------------

def cache_get(key: str) -> str | None:
    try:
        return cache.get(key)
    except redis.RedisError as exc:
        log.warning("redis unavailable on GET %s: %s", key, exc)
        return None


def cache_set(key: str, value: str, ttl: int) -> None:
    try:
        cache.set(key, value, ex=ttl)
    except redis.RedisError as exc:
        log.warning("redis unavailable on SET %s: %s", key, exc)


def cache_delete(key: str) -> None:
    try:
        cache.delete(key)
    except redis.RedisError as exc:
        log.warning("redis unavailable on DEL %s: %s", key, exc)


def client_ip(request: Request) -> str:
    # Behind a reverse proxy, request.client is the proxy, not the user.
    # A proxy that sets X-Real-IP lets us see the real caller.
    return request.headers.get("x-real-ip") or request.client.host


def over_rate_limit(ip: str) -> bool:
    key = f"ratelimit:{ip}:{int(time.time() // 60)}"
    try:
        count = cache.incr(key)
        if count == 1:
            cache.expire(key, 60)
        return count > RATE_LIMIT_PER_MINUTE
    except redis.RedisError as exc:
        log.warning("redis unavailable, skipping rate limit: %s", exc)
        return False


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info(
        "starting snip-api env=%s db=%s:%s redis=%s:%s",
        APP_ENV, DB_HOST, DB_PORT, REDIS_HOST, REDIS_PORT,
    )
    last_error = None
    for attempt in range(1, 11):
        try:
            init_db()
            log.info("database ready")
            break
        except psycopg2.OperationalError as exc:
            last_error = exc
            log.warning("database not reachable yet (attempt %s/10): %s", attempt, str(exc).strip())
            time.sleep(2)
    else:
        raise RuntimeError(f"could not reach database at {DB_HOST}:{DB_PORT}") from last_error
    yield
    log.info("snip-api shutting down")


app = FastAPI(title="snip-api", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")


class LinkIn(BaseModel):
    url: HttpUrl


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


@app.get("/api/health")
def health():
    """Liveness: the process is up and serving HTTP. Checks nothing else."""
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    """Readiness: can this instance reach its dependencies right now?"""
    checks = {}

    try:
        conn = get_connection()
        conn.close()
        checks["postgres"] = "ok"
    except psycopg2.OperationalError as exc:
        checks["postgres"] = f"error: {str(exc).strip()}"

    try:
        cache.ping()
        checks["redis"] = "ok"
    except redis.RedisError as exc:
        checks["redis"] = f"error: {exc}"

    # Redis is a cache, so it being down degrades us but doesn't make us unready.
    if checks["postgres"] != "ok":
        raise HTTPException(status_code=503, detail=checks)
    return {"status": "ready" if checks["redis"] == "ok" else "degraded", "checks": checks}


@app.post("/api/links", status_code=201)
def create_link(link: LinkIn, request: Request):
    ip = client_ip(request)
    if over_rate_limit(ip):
        log.info("rate limit hit for %s", ip)
        raise HTTPException(
            status_code=429,
            detail=f"slow down: max {RATE_LIMIT_PER_MINUTE} new links per minute ({ip})",
        )

    url = str(link.url)
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for _ in range(5):
                code = new_code()
                try:
                    cur.execute(
                        "INSERT INTO links (code, url) VALUES (%s, %s) "
                        "RETURNING code, url, clicks, created_at",
                        (code, url),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    break
                except psycopg2.IntegrityError:  # code collision, try another
                    conn.rollback()
            else:
                raise HTTPException(status_code=500, detail="could not generate a unique code")
    finally:
        conn.close()

    cache_delete("stats")
    log.info("created %s -> %s", row["code"], url)
    return row


@app.get("/api/links")
def list_links(limit: int = 50):
    limit = max(1, min(limit, 200))
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT code, url, clicks, created_at FROM links "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return {"links": cur.fetchall()}
    finally:
        conn.close()


@app.get("/api/r/{code}")
def follow(code: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE links SET clicks = clicks + 1 WHERE code = %s RETURNING url",
                (code,),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"no link with code {code!r}")

    cache_delete("stats")
    log.info("redirect %s -> %s", code, row[0])
    return RedirectResponse(row[0], status_code=307)


@app.get("/api/stats")
def stats():
    cached = cache_get("stats")
    if cached:
        total_links, total_clicks = (int(x) for x in cached.split(":"))
        return {"total_links": total_links, "total_clicks": total_clicks, "source": "cache"}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COALESCE(SUM(clicks), 0) FROM links")
            total_links, total_clicks = cur.fetchone()
    finally:
        conn.close()

    cache_set("stats", f"{total_links}:{total_clicks}", STATS_TTL_SECONDS)
    return {"total_links": total_links, "total_clicks": total_clicks, "source": "database"}
