/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        // 清爽紫罗兰 · 设计令牌
        primary: {
          DEFAULT: '#6B5CE7',
          50: '#F4F3FB',
          100: '#EAE8FA',
          200: '#D6D1F5',
          300: '#B8AEEF',
          400: '#9787EA',
          500: '#6B5CE7',
          600: '#5A4BD4',
          700: '#493DB0',
          800: '#3A308C',
          900: '#2A2366',
        },
        ink: '#1F1B33',
        sub: '#6E698C',
        faint: '#A5A0C2',
        blush: '#F0A6C8',
        canvas: '#F4F3FB',
        cream: '#FBFBFF',
      },
      fontFamily: {
        sans: [
          'Noto Sans SC',
          'HarmonyOS Sans SC',
          'HarmonyOS Sans',
          'PingFang SC',
          'Microsoft YaHei',
          'system-ui',
          'sans-serif',
        ],
      },
      borderRadius: {
        xl2: '1.25rem',
      },
      boxShadow: {
        soft: '0 8px 30px rgba(107, 92, 231, 0.08)',
        glass: '0 8px 24px rgba(31, 27, 51, 0.06)',
        glow: '0 12px 40px rgba(107, 92, 231, 0.25)',
      },
      backgroundImage: {
        'hero-gradient':
          'linear-gradient(135deg, #6B5CE7 0%, #8B7CF0 45%, #F0A6C8 100%)',
      },
    },
  },
  plugins: [],
}