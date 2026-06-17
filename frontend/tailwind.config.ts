import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        emeraldTech: "#047857",
        emeraldDeep: "#064e3b",
        emeraldInk: "#022c22",
        emeraldMist: "#eef8f1",
        amberValue: "#d49a00",
        amberSoft: "#fff6df",
        graphite: "#1f2937",
        field: "#f6f8f6"
      },
      boxShadow: {
        panel: "0 14px 34px rgba(15, 23, 42, 0.08)",
        soft: "0 1px 2px rgba(15, 23, 42, 0.08)",
        glow: "0 24px 70px rgba(4, 120, 87, 0.18)"
      },
      borderRadius: {
        panel: "14px"
      }
    }
  },
  plugins: []
};

export default config;
