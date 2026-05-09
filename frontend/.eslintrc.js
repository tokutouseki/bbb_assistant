module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  plugins: ['vue'],
  rules: {
    // Vue规则
    'vue/multi-word-component-names': 'off',
    'vue/no-v-html': 'off',
    'vue/require-default-prop': 'off',
    'vue/require-explicit-emits': 'off',
    'vue/prop-name-casing': ['error', 'camelCase'],
    'vue/component-definition-name-casing': ['error', 'PascalCase'],
    'vue/component-name-in-template-casing': ['error', 'PascalCase'],
    'vue/html-self-closing': [
      'error',
      {
        html: {
          void: 'always',
          normal: 'always',
          component: 'always',
        },
        svg: 'always',
        math: 'always',
      },
    ],

    // JavaScript/TypeScript规则
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      },
    ],
    'prefer-const': 'error',
    'no-var': 'error',
    eqeqeq: ['error', 'always'],
    'no-else-return': 'error',
    'no-empty-function': 'off',
    '@typescript-eslint/no-empty-function': 'off',
    'no-multi-spaces': 'error',
    'no-trailing-spaces': 'error',
    'no-multiple-empty-lines': ['error', { max: 1, maxEOF: 0 }],
    'space-before-function-paren': [
      'error',
      {
        anonymous: 'always',
        named: 'never',
        asyncArrow: 'always',
      },
    ],
    'arrow-spacing': 'error',
    'block-spacing': 'error',
    'comma-spacing': 'error',
    'key-spacing': 'error',
    'keyword-spacing': 'error',
    'object-curly-spacing': ['error', 'always'],
    'space-infix-ops': 'error',
    'space-unary-ops': 'error',
    'spaced-comment': ['error', 'always', { markers: ['/'] }],
    'template-curly-spacing': 'error',

    // 导入规则
    'import/order': [
      'error',
      {
        groups: [
          'builtin',
          'external',
          'internal',
          'parent',
          'sibling',
          'index',
          'object',
          'type',
        ],
        pathGroups: [
          {
            pattern: 'vue',
            group: 'external',
            position: 'before',
          },
          {
            pattern: '@/**',
            group: 'internal',
          },
        ],
        pathGroupsExcludedImportTypes: ['vue'],
        'newlines-between': 'always',
        alphabetize: {
          order: 'asc',
          caseInsensitive: true,
        },
      },
    ],

    // 代码复杂度
    complexity: ['warn', 10],
    'max-depth': ['warn', 4],
    'max-params': ['warn', 5],
    'max-lines': ['warn', 300],
    'max-lines-per-function': ['warn', 50],
    'max-statements': ['warn', 15],
    'max-nested-callbacks': ['warn', 3],

    // 安全规则
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-script-url': 'error',
    'no-new-func': 'error',

    // 异步规则
    'no-promise-executor-return': 'error',
    'require-atomic-updates': 'error',

    // 其他规则
    'no-duplicate-imports': 'error',
    'no-useless-return': 'error',
    'no-await-in-loop': 'warn',
    'require-await': 'warn',
  },
  overrides: [
    {
      files: ['*.vue'],
      parser: 'vue-eslint-parser',
      parserOptions: {
        parser: '@typescript-eslint/parser',
        sourceType: 'module',
        ecmaVersion: 'latest',
      },
      rules: {
        // Vue文件特定规则
        'vue/html-indent': ['error', 2],
        'vue/max-attributes-per-line': [
          'error',
          {
            singleline: 3,
            multiline: 1,
          },
        ],
        'vue/first-attribute-linebreak': [
          'error',
          {
            singleline: 'ignore',
            multiline: 'below',
          },
        ],
        'vue/singleline-html-element-content-newline': 'off',
        'vue/multiline-html-element-content-newline': 'off',
      },
    },
    {
      files: ['**/__tests__/*.{j,t}s?(x)', '**/tests/unit/**/*.spec.{j,t}s?(x)'],
      env: {
        jest: true,
      },
    },
    {
      files: ['electron/**/*.{js,ts}'],
      env: {
        node: true,
      },
      rules: {
        'no-console': 'off',
      },
    },
  ],
  settings: {
    'import/resolver': {
      alias: {
        map: [
          ['@', './src'],
          ['@assets', './src/assets'],
          ['@components', './src/components'],
          ['@views', './src/views'],
          ['@stores', './src/stores'],
          ['@utils', './src/utils'],
          ['@types', './src/types'],
        ],
        extensions: ['.js', '.jsx', '.ts', '.tsx', '.vue'],
      },
    },
  },
}