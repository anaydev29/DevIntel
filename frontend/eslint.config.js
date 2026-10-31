import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  { ignores: ['dist'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: { ecmaVersion: 2023, sourceType: 'module', globals: globals.browser, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { react, 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react/jsx-uses-vars': 'error',
      // Loading flags are reset at the start of data-loading effects on purpose; the extra render is harmless
      'react-hooks/set-state-in-effect': 'off',
      'no-unused-vars': ['error', { varsIgnorePattern: '^_', argsIgnorePattern: '^_', caughtErrors: 'none' }],
    },
  },
  { files: ['vite.config.js', 'eslint.config.js'], languageOptions: { globals: globals.node } },
]
