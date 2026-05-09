/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 崩坏3主题色
        'honkai': {
          50: '#fdf2f8',
          100: '#fce7f3',
          200: '#fbcfe8',
          300: '#f9a8d4',
          400: '#f472b6',
          500: '#ec4899', // 主色调
          600: '#db2777',
          700: '#be185d',
          800: '#9d174d',
          900: '#831843',
        },
        // 游戏UI颜色
        'game': {
          'primary': '#4f46e5',
          'secondary': '#7c3aed',
          'accent': '#f59e0b',
          'success': '#10b981',
          'warning': '#f59e0b',
          'danger': '#ef4444',
          'info': '#3b82f6',
          'dark': '#1f2937',
          'light': '#f9fafb'
        },
        // 角色主题色
        'character': {
          'kiana': '#f472b6', // 琪亚娜
          'mei': '#8b5cf6',   // 芽衣
          'bronya': '#06b6d4', // 布洛妮娅
          'seele': '#10b981',  // 希儿
          'rita': '#ec4899',   // 丽塔
          'durandal': '#f59e0b' // 幽兰黛尔
        }
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace'],
        'game': ['"HYWenHei"', '"Microsoft YaHei"', 'sans-serif']
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.5s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' }
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' }
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(236, 72, 153, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(236, 72, 153, 0.8)' }
        }
      },
      backdropBlur: {
        'xs': '2px',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
      boxShadow: {
        'game': '0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2)',
        'inner-game': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.3)',
        'glow': '0 0 20px rgba(236, 72, 153, 0.5)',
      },
      backgroundImage: {
        'gradient-game': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'gradient-honkai': 'linear-gradient(135deg, #f472b6 0%, #8b5cf6 100%)',
        'gradient-character': 'linear-gradient(135deg, var(--character-color) 0%, #8b5cf6 100%)',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}