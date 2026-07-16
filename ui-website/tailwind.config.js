/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#0E0E0E',
        surface: '#131313',
        'surface-low': '#1B1B1B',
        'surface-high': '#2A2A2A',
        border: '#3A2A28',
        foreground: '#E2E2E2',
        muted: '#8D8583',
        danger: '#DC2626',
        'danger-soft': '#FFB4AB',
        success: '#22C55E',
        info: '#60A5FA',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Courier', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
