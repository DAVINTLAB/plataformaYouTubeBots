/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        davint: {
          50:  '#edf7fa',
          100: '#d0eff5',
          200: '#a6e1ed',
          300: '#71cedd',
          400: '#38b5c9',
          500: '#2ea0b1',
          600: '#257f8d',
          700: '#1e6570',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideUp: {
          from: { transform: 'translateY(16px)', opacity: '0' },
          to:   { transform: 'translateY(0)',    opacity: '1' },
        },
      },
      animation: {
        'fade-in':  'fadeIn 0.15s ease',
        'slide-up': 'slideUp 0.2s ease',
      },
    },
  },
  plugins: [],
}
