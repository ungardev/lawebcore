/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: { '2xl': '1400px' },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        hover: {
          DEFAULT: 'hsl(var(--hover))',
          foreground: 'hsl(var(--hover-foreground))',
        },
        surface: {
          DEFAULT: 'hsl(var(--surface-1))',
          raised: 'hsl(var(--surface-2))',
          sunken: 'hsl(var(--surface-0))',
        },
        divider: 'hsl(var(--divider))',
        focus: 'hsl(var(--focus))',
        success: 'hsl(var(--success))',
        warning: 'hsl(var(--warning))',
        info: 'hsl(var(--info))',
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar))',
          foreground: 'hsl(var(--sidebar-foreground))',
          primary: 'hsl(var(--sidebar-primary))',
          'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
          accent: 'hsl(var(--sidebar-accent))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
          border: 'hsl(var(--sidebar-border))',
          ring: 'hsl(var(--sidebar-ring))',
        },
        brand: {
          pink: 'hsl(var(--brand-pink))',
          'pink-hover': 'hsl(var(--brand-pink-hover))',
          purple: 'hsl(var(--brand-purple))',
          blue: 'hsl(var(--brand-blue))',
          'blue-hover': 'hsl(var(--brand-blue-hover))',
        },
    },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        display: ['Instrument Serif', 'Georgia', 'serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      boxShadow: {
        card: 'none',
        'card-hover': '0 0 0 1px rgba(59, 130, 246, 0.24)',
        elevated: '0 18px 48px rgba(0, 0, 0, 0.34)',
        soft: '0 1px 2px rgba(0, 0, 0, 0.18), 0 8px 24px rgba(0, 0, 0, 0.12)',
        elevated2: '0 12px 40px rgba(0, 0, 0, 0.26)',
        glow: '0 0 0 1px rgba(59, 130, 246, 0.28), 0 8px 24px rgba(15, 23, 42, 0.24)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, hsl(var(--brand-pink)), hsl(var(--brand-purple)), hsl(var(--brand-blue)))',
        'brand-gradient-hover': 'linear-gradient(135deg, hsl(var(--brand-pink-hover)), hsl(var(--brand-purple)), hsl(var(--brand-blue-hover)))',
        'brand-gradient-soft': 'linear-gradient(135deg, hsl(var(--brand-pink) / 0.15), hsl(var(--brand-purple) / 0.15), hsl(var(--brand-blue) / 0.15))',
        'gradient-dark': 'linear-gradient(135deg, #14181F 0%, #2B303B 100%)',
        'gradient-subtle': 'linear-gradient(180deg, #FAFBFB 0%, #F1F2F4 100%)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(var(--tw-gradient-stops))',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [import('tailwindcss-animate')],
};
