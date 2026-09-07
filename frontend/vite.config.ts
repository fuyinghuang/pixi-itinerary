import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // The backend's CORS allowlist names this port. Without strictPort, Vite
    // would quietly move to 5174 when 5173 is taken and every API call would
    // fail CORS — a confusing failure mid-demo. Fail loudly instead.
    port: 5173,
    strictPort: true,
  },
});
