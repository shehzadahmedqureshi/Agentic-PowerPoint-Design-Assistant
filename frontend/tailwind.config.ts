import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        mist: "#f4f6fb",
        accent: "#6d5dfc",
      },
      boxShadow: {
        soft: "0 24px 70px rgba(30, 41, 59, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;

