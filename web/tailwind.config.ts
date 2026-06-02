import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#faf9f5",  // --mf-bg
        panel: "#ffffff",     // --mf-surface
        ink: "#1c1b18",       // --mf-text-primary
        muted: "#5e5c56",     // --mf-text-secondary
        line: "#ddd8cf",      // border (keep hex; --mf-border uses rgba)
        primary: "#2d7d5f",   // --mf-accent (green, was blue #2368d1)
        safe: "#2d7d5f",      // --mf-approved
        warn: "#cc7a00",      // --mf-warning
        danger: "#c04040",    // --mf-error
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(35, 33, 29, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
