/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./census_app/templates/**/*.html",
    "./census_app/**/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        "tea_rose_(red)": {
          DEFAULT: "#f8c7cc",
          100: "#500a11",
          200: "#a01422",
          300: "#e5293c",
          400: "#ee7984",
          500: "#f8c7cc",
          600: "#fad3d7",
          700: "#fbdee1",
          800: "#fce9eb",
          900: "#fef4f5",
        },
        flax: {
          DEFAULT: "#f4e285",
          100: "#453b06",
          200: "#8a750d",
          300: "#cfb013",
          400: "#edd141",
          500: "#f4e285",
          600: "#f6e79e",
          700: "#f8edb6",
          800: "#faf3ce",
          900: "#fdf9e7",
        },
        ultra_violet: {
          DEFAULT: "#6d5aa5",
          100: "#161221",
          200: "#2c2442",
          300: "#413663",
          400: "#574884",
          500: "#6d5aa5",
          600: "#8a7bb7",
          700: "#a79cc9",
          800: "#c5bddb",
          900: "#e2deed",
        },
        electric_blue: {
          DEFAULT: "#50e6ff",
          100: "#003943",
          200: "#007287",
          300: "#00acca",
          400: "#0edbff",
          500: "#50e6ff",
          600: "#74eaff",
          700: "#97efff",
          800: "#baf5ff",
          900: "#dcfaff",
        },
        mint: {
          DEFAULT: "#37b77c",
          100: "#0b2519",
          200: "#164a32",
          300: "#216f4a",
          400: "#2c9463",
          500: "#37b77c",
          600: "#58cd97",
          700: "#82dab1",
          800: "#ace6cb",
          900: "#d5f3e5",
        },
      },
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            // Keep DaisyUI button styles for anchors with .btn inside prose
            'a.btn, a[class~="btn"]': {
              textDecoration: "none",
            },
            'a.btn:hover, a[class~="btn"]:hover': {
              textDecoration: "none",
            },
          },
        },
      }),
    },
  },
  plugins: [require("@tailwindcss/typography"), require("daisyui")],
  daisyui: {
    themes: [
      {
        census: {
          primary: "#6d5aa5",
          secondary: "#50e6ff",
          accent: "#98b6b1",
          neutral: "#e9ecf5",
          "base-100": "#ffffff",
          "base-200": "#f6f7f8",
          info: "#629677",
          success: "#37b77c",
          warning: "#ffffff",
          error: "#FFA500",
        },
      },
      "light",
      "dark",
    ],
  },
};
