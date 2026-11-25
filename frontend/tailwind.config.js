/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        card: "#111827",
        cardHover: "#1f2937",
        border: "#374151",
        accent: "#3b82f6",
        accentGreen: "#10b981",
        accentOrange: "#f59e0b",
        accentRed: "#ef4444",
      },
    },
  },
  plugins: [],
}
