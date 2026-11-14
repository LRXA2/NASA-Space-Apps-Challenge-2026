import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// A relative base lets the built site run from any folder, such as a GitHub Pages project path.
export default defineConfig({
  base: "./",
  plugins: [react()],
});
