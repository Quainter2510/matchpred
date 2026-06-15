/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Более насыщённый индиго вместо дефолтного синего — отстройка от
        // «стокового» вида; гармонирует с индиго-акцентами (режим суперадмина).
        brand: {
          DEFAULT: "#4f46e5", // indigo-600
          dark: "#4338ca", // indigo-700
          light: "#eef2ff", // indigo-50
        },
      },
      boxShadow: {
        // Мягкая тень карточек, чтобы белые блоки «всплывали» над фоном.
        card: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 2px 8px -3px rgb(15 23 42 / 0.10)",
        "card-hover":
          "0 4px 14px -4px rgb(15 23 42 / 0.14), 0 2px 6px -3px rgb(15 23 42 / 0.08)",
      },
    },
  },
  plugins: [],
};
