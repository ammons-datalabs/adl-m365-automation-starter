'use client';

import React from 'react';
import { useTheme } from './ThemeProvider';

export default function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();

  const handleToggle = () => {
    if (theme === 'system') {
      setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
    } else {
      setTheme(theme === 'light' ? 'dark' : 'light');
    }
  };

  return (
    <button
      onClick={handleToggle}
      className="theme-toggle"
      aria-label={`Switch to ${resolvedTheme === 'light' ? 'dark' : 'light'} theme`}
      title={`Current theme: ${theme === 'system' ? `system (${resolvedTheme})` : theme}`}
    >
      {resolvedTheme === 'light' ? (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M10 3V1M10 19V17M17 10H19M1 10H3M15.657 4.343L17.071 2.929M2.929 17.071L4.343 15.657M15.657 15.657L17.071 17.071M2.929 2.929L4.343 4.343"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="10" cy="10" r="4" stroke="currentColor" strokeWidth="2" fill="none" />
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M10 2C5.582 2 2 5.582 2 10s3.582 8 8 8c.395 0 .779-.034 1.154-.098-2.458-1.048-4.154-3.516-4.154-6.402 0-3.86 3.14-7 7-7 .343 0 .677.029 1.006.084C14.34 3.169 12.32 2 10 2z" />
        </svg>
      )}
    </button>
  );
}
