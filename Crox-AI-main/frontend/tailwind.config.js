/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#08090a",
          raised: "#131416",
          border: "#26282c",
        },
        accent: {
          DEFAULT: "#c7cdd6",
          soft: "#e8ebf0",
          dim: "#565d68",
        },
      },
      fontFamily: {
        display: ['"Fraunces Variable"', "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
