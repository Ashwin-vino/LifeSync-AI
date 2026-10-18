/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0A0A0A',
        surface: {
          DEFAULT: '#141414',
          subtle: '#181818',
          hover: '#1E1E1E',
          active: '#242424',
        },
        card: '#141414',
        border: {
          DEFAULT: '#303030',
          subtle: '#262626',
          strong: '#424242',
        },
        accent: {
          DEFAULT: '#EDEDED',
          muted: '#8E8E8E',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
