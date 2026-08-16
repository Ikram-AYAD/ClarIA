import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05060a",
          900: "#0a0c14",
          850: "#0e111c",
          800: "#131728",
          700: "#1b2036",
          600: "#262d4a",
        },
        accent: {
          400: "#8b9dff",
          500: "#6c7bff",
          600: "#5561e8",
        },
        violet: {
          400: "#c084fc",
          500: "#a855f7",
        },
        mint: {
          400: "#5eead4",
          500: "#2dd4bf",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(108, 123, 255, 0.45)",
        card: "0 8px 30px -12px rgba(0,0,0,0.5)",
      },
      backgroundImage: {
        "grid-glow":
          "radial-gradient(circle at 20% -10%, rgba(108,123,255,0.25), transparent 40%), radial-gradient(circle at 90% 10%, rgba(168,85,247,0.18), transparent 35%)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        shimmer: "shimmer 2.5s linear infinite",
        "fade-in-up": "fade-in-up 0.4s ease-out both",
        pulseGlow: "pulseGlow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
