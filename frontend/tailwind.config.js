/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // "Ledger" palette: a paper-toned analyst workspace, not a
        // marketing landing page. Ink for text/structure, teal for
        // verified-positive evidence, rust for verified-risk evidence,
        // amber for anything still pending human review.
        paper: {
          DEFAULT: "#F6F4EF",
          raised: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#1C2430",
          soft: "#3D4756",
          faint: "#7C8697",
        },
        line: "#DCD7CB",
        teal: {
          DEFAULT: "#2F6F62",
          soft: "#E4EEEA",
        },
        rust: {
          DEFAULT: "#B3492F",
          soft: "#F5E7E2",
        },
        amber: {
          DEFAULT: "#B3821F",
          soft: "#F3EAD3",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        sm: "3px",
        DEFAULT: "4px",
      },
    },
  },
  plugins: [],
};
