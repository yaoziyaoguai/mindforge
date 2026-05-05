import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f7f5f1",
        panel: "#ffffff",
        ink: "#23211d",
        muted: "#6d685f",
        line: "#ddd8cf",
        primary: "#2368d1",
        safe: "#237a57",
        warn: "#b66b13",
        danger: "#b42318"
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(35, 33, 29, 0.08)"
      }
    }
  },
  plugins: []
} satisfies Config;
