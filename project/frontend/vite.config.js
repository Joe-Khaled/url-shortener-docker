import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    // Local development only: `npm run dev` forwards /api/* to an API
    // running on this machine. `npm run build` just emits static files
    // into dist/ -- nothing in the build output knows where the API is.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
