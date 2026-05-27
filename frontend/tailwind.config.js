/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gold: { DEFAULT: '#C9A96E', light: '#E8D5A8' },
        ivory: { DEFAULT: '#FDFBF7', warm: '#F8F4ED' },
        rose: '#C08081',
        charcoal: '#1C1C1E'
      }
    }
  },
  plugins: []
}
