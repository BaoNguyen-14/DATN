/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "on-tertiary-fixed-variant": "#00429c",
        "outline-variant": "#c6c5d4",
        "primary": "#000666",
        "on-surface-variant": "#454652",
        "secondary": "#006e1c",
        "inverse-surface": "#2d3133",
        "on-secondary": "#ffffff",
        "on-background": "#191c1e",
        "on-error": "#ffffff",
        "tertiary-fixed-dim": "#b0c6ff",
        "tertiary-fixed": "#d9e2ff",
        "surface-tint": "#4c56af",
        "error-container": "#ffdad6",
        "secondary-container": "#91f78e",
        "on-primary-fixed-variant": "#343d96",
        "on-primary-container": "#8690ee",
        "secondary-fixed-dim": "#78dc77",
        "inverse-primary": "#bdc2ff",
        "surface-container": "#eceef1",
        "secondary-fixed": "#94f990",
        "background": "#f7f9fc",
        "surface-dim": "#d8dadd",
        "on-tertiary": "#ffffff",
        "on-error-container": "#93000a",
        "tertiary-container": "#002c6e",
        "surface-variant": "#e0e3e6",
        "on-primary-fixed": "#000767",
        "surface": "#f7f9fc",
        "primary-fixed-dim": "#bdc2ff",
        "surface-container-lowest": "#ffffff",
        "on-primary": "#ffffff",
        "surface-container-high": "#e6e8eb",
        "primary-fixed": "#e0e0ff",
        "on-surface": "#191c1e",
        "tertiary": "#001944",
        "error": "#ba1a1a",
        "on-secondary-fixed-variant": "#005313",
        "inverse-on-surface": "#eff1f4",
        "surface-bright": "#f7f9fc",
        "on-tertiary-container": "#6b95f3",
        "on-secondary-container": "#00731e",
        "primary-container": "#1a237e",
        "on-tertiary-fixed": "#001945",
        "on-secondary-fixed": "#002204",
        "surface-container-low": "#f2f4f7",
        "surface-container-highest": "#e0e3e6",
        "outline": "#767683"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "12px",
        "xl": "0.75rem",
        "full": "9999px"
      },
      fontFamily: {
        "headline": ["Manrope", "sans-serif"],
        "body": ["Inter", "sans-serif"],
        "label": ["Inter", "sans-serif"]
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}
