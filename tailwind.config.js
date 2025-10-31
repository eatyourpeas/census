const typography = require("@tailwindcss/typography");
const daisyui = require("daisyui");

const daisyuiPlugin = daisyui?.default ?? daisyui;

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./checktick_app/templates/**/*.html",
    "./checktick_app/**/templates/**/*.html",
  ],
  theme: {
    extend: {
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
  plugins: [typography, daisyuiPlugin],
};
