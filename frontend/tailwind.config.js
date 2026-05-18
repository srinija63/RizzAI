/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./App.{js,jsx,ts,tsx}', './src/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        ink: '#0f0f0f',
        rose: { soft: '#fda4af', glow: '#fb7185' },
        plum: { 400: '#c4b5fd', 500: '#a78bfa', 600: '#7c3aed' },
        ember: '#fb923c',
      },
    },
  },
  plugins: [],
};
