import "./style.css";

// All API calls are relative ("/api/..."), so the frontend assumes the API
// is reachable on the SAME origin it was loaded from.
const API = "/api";

const form = document.getElementById("shorten-form");
const input = document.getElementById("url-input");
const message = document.getElementById("message");
const statusEl = document.getElementById("status");
const linksBody = document.getElementById("links-body");

function shortUrl(code) {
  return `${window.location.origin}${API}/r/${code}`;
}

function showMessage(text, kind = "info") {
  message.textContent = text;
  message.className = `message ${kind}`;
}

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    throw new Error(`${res.status} ${detail}`);
  }
  return body;
}

async function loadStatus() {
  try {
    const ready = await request("/ready");
    statusEl.textContent = `backend ${ready.status} · postgres ${ready.checks.postgres} · redis ${ready.checks.redis}`;
    statusEl.className = `status ${ready.status === "ready" ? "ok" : "warn"}`;
  } catch (err) {
    statusEl.textContent = `backend unreachable (${err.message})`;
    statusEl.className = "status error";
  }
}

async function loadStats() {
  try {
    const stats = await request("/stats");
    document.getElementById("total-links").textContent = stats.total_links;
    document.getElementById("total-clicks").textContent = stats.total_clicks;
  } catch {
    // status bar already explains what's wrong
  }
}

async function loadLinks() {
  try {
    const { links } = await request("/links");
    linksBody.replaceChildren(
      ...links.map((link) => {
        const row = document.createElement("tr");

        const shortCell = document.createElement("td");
        const a = document.createElement("a");
        a.href = shortUrl(link.code);
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = link.code;
        a.addEventListener("click", () => setTimeout(refresh, 500));
        shortCell.append(a);

        const urlCell = document.createElement("td");
        urlCell.className = "url";
        urlCell.textContent = link.url;

        const clicksCell = document.createElement("td");
        clicksCell.textContent = link.clicks;

        row.append(shortCell, urlCell, clicksCell);
        return row;
      }),
    );
  } catch {
    linksBody.replaceChildren();
  }
}

function refresh() {
  loadStatus();
  loadStats();
  loadLinks();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const link = await request("/links", {
      method: "POST",
      body: JSON.stringify({ url: input.value }),
    });
    showMessage(`Created ${shortUrl(link.code)}`, "ok");
    input.value = "";
    refresh();
  } catch (err) {
    showMessage(err.message, "error");
  }
});

refresh();
setInterval(refresh, 10000);
