import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-undef': 'off',
    },
  },
  {
    ignores: ['dist', 'node_modules', '.next', '*.config.js'],
  },
  {
    files: [
      'src/features/lens/**',
      'src/features/projections/**',
      'src/features/settings/**',
      'src/features/imports/**',
      'src/features/dashboard/**',
      'src/features/campaigns/**',
      'src/features/auth/**',
      'src/hooks/**',
      'src/components/ui/badge.tsx',
      'src/components/ui/button.tsx',
      'src/components/ui/card.tsx',
      'src/components/ui/dialog.tsx',
      'src/components/ui/input.tsx',
      'src/components/ui/progress.tsx',
      'src/components/ui/table.tsx',
      'src/components/data-table/**',
      'src/components/layout/GlobalSearchDialog.tsx',
      'src/components/layout/Sidebar.tsx',
    ],
    rules: {
      '@typescript-eslint/no-unused-vars': 'off',
      'no-unused-vars': 'off',
    },
  },
];
