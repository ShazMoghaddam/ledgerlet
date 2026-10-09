import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "playwright-report", "test-results", "src/api/schema.d.ts"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended, jsxA11y.flatConfigs.strict],
    languageOptions: { ecmaVersion: 2022, globals: globals.browser },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Money must never pass through parseFloat or Number(); see src/lib/money.ts.
      "no-restricted-globals": [
        "error",
        { name: "parseFloat", message: "Use lib/money for amounts." },
      ],
    },
  },
);
