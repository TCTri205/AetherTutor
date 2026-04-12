/**
 * Unit Tests cho ThemeProvider (Sprint 14).
 *
 * Covers:
 * - Theme persistence to localStorage
 * - System preference detection
 * - Theme switching
 * - useTheme hook behavior
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, useTheme, type Theme } from '../providers/ThemeProvider';

// ─── Test Component ────────────────────────────────────────────────
/** Wrapper component để expose context values trong test */
function ThemeDisplay() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="resolved-theme">{resolvedTheme}</span>
      <button onClick={() => setTheme('light')} data-testid="set-light">
        Set Light
      </button>
      <button onClick={() => setTheme('dark')} data-testid="set-dark">
        Set Dark
      </button>
      <button onClick={() => setTheme('system')} data-testid="set-system">
        Set System
      </button>
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────
const THEME_KEY = 'aethertutor-theme';

function renderThemeProvider() {
  return render(
    <ThemeProvider>
      <ThemeDisplay />
    </ThemeProvider>,
  );
}

// ─── beforeEach / afterEach ─────────────────────────────────────────
beforeEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove('light', 'dark');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── Tests ──────────────────────────────────────────────────────────

describe('ThemeProvider', () => {
  describe('initialization', () => {
    it('should default to "system" when no stored theme', () => {
      renderThemeProvider();
      expect(screen.getByTestId('theme').textContent).toBe('system');
    });

    it('should read stored theme from localStorage', () => {
      localStorage.setItem(THEME_KEY, 'dark');
      renderThemeProvider();
      expect(screen.getByTestId('theme').textContent).toBe('dark');
    });

    it('should resolve to "dark" when stored theme is "dark"', () => {
      localStorage.setItem(THEME_KEY, 'dark');
      renderThemeProvider();
      expect(screen.getByTestId('resolved-theme').textContent).toBe('dark');
    });

    it('should resolve to "light" when stored theme is "light"', () => {
      localStorage.setItem(THEME_KEY, 'light');
      renderThemeProvider();
      expect(screen.getByTestId('resolved-theme').textContent).toBe('light');
    });

    it('should resolve to system preference when theme is "system"', () => {
      // Simulate dark system preference
      vi.spyOn(window, 'matchMedia').mockImplementation(
        (query: string) =>
          ({
            matches: query.includes('dark'),
            media: query,
            onchange: null,
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
          }) as unknown as MediaQueryList,
      );

      renderThemeProvider();
      // "system" theme resolves to dark because matchMedia says dark is preferred
      expect(screen.getByTestId('resolved-theme').textContent).toBe('dark');
    });

    it('should apply resolved theme class to document.documentElement', () => {
      localStorage.setItem(THEME_KEY, 'dark');
      renderThemeProvider();
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(document.documentElement.classList.contains('light')).toBe(false);
    });
  });

  describe('theme switching', () => {
    it('should switch to light theme and persist to localStorage', async () => {
      const user = userEvent.setup();
      renderThemeProvider();

      await user.click(screen.getByTestId('set-light'));

      expect(screen.getByTestId('theme').textContent).toBe('light');
      expect(screen.getByTestId('resolved-theme').textContent).toBe('light');
      expect(localStorage.getItem(THEME_KEY)).toBe('light');
      expect(document.documentElement.classList.contains('light')).toBe(true);
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should switch to dark theme and persist to localStorage', async () => {
      const user = userEvent.setup();
      localStorage.setItem(THEME_KEY, 'light');
      renderThemeProvider();

      await user.click(screen.getByTestId('set-dark'));

      expect(screen.getByTestId('theme').textContent).toBe('dark');
      expect(screen.getByTestId('resolved-theme').textContent).toBe('dark');
      expect(localStorage.getItem(THEME_KEY)).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should switch to system theme', async () => {
      const user = userEvent.setup();
      localStorage.setItem(THEME_KEY, 'dark');
      renderThemeProvider();

      await user.click(screen.getByTestId('set-system'));

      expect(screen.getByTestId('theme').textContent).toBe('system');
      expect(localStorage.getItem(THEME_KEY)).toBe('system');
    });
  });

  describe('system preference detection', () => {
    it('should listen to prefers-color-scheme changes', () => {
      const addEventListener = vi.fn();
      const removeEventListener = vi.fn();

      vi.spyOn(window, 'matchMedia').mockImplementation(
        (query: string) =>
          ({
            matches: false,
            media: query,
            onchange: null,
            addEventListener,
            removeEventListener,
            dispatchEvent: vi.fn(),
          }) as unknown as MediaQueryList,
      );

      renderThemeProvider();

      // Should have added listener for dark scheme query
      expect(addEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function),
      );
    });

    it('should clean up event listener on unmount', () => {
      const removeEventListener = vi.fn();
      const addEventListener = vi.fn((_event: string, handler: () => void) => {
        // Capture handler for later use
      });

      vi.spyOn(window, 'matchMedia').mockImplementation(
        (query: string) =>
          ({
            matches: false,
            media: query,
            onchange: null,
            addEventListener,
            removeEventListener,
            dispatchEvent: vi.fn(),
          }) as unknown as MediaQueryList,
      );

      const { unmount } = renderThemeProvider();
      unmount();

      // Cleanup happens via useEffect return
      expect(removeEventListener).toHaveBeenCalled();
    });
  });

  describe('localStorage persistence', () => {
    it('should save theme to localStorage on setTheme call', async () => {
      const user = userEvent.setup();
      renderThemeProvider();

      expect(localStorage.getItem(THEME_KEY)).toBeNull();

      await user.click(screen.getByTestId('set-dark'));
      expect(localStorage.getItem(THEME_KEY)).toBe('dark');

      await user.click(screen.getByTestId('set-light'));
      expect(localStorage.getItem(THEME_KEY)).toBe('light');
    });

    it('should restore theme from localStorage on mount', () => {
      localStorage.setItem(THEME_KEY, 'light');
      renderThemeProvider();
      expect(screen.getByTestId('theme').textContent).toBe('light');
      expect(screen.getByTestId('resolved-theme').textContent).toBe('light');
    });

    it('should handle invalid stored value by defaulting to "system"', () => {
      localStorage.setItem(THEME_KEY, 'invalid-value');
      renderThemeProvider();
      expect(screen.getByTestId('theme').textContent).toBe('system');
    });
  });

  describe('useTheme hook', () => {
    it('should throw error when used outside ThemeProvider', () => {
      // Suppress console.error for expected error
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      function BrokenComponent() {
        useTheme();
        return null;
      }

      expect(() => render(<BrokenComponent />)).toThrow(
        'useTheme must be used within a ThemeProvider',
      );

      consoleError.mockRestore();
    });

    it('should provide theme, resolvedTheme, and setTheme', () => {
      renderThemeProvider();
      expect(screen.getByTestId('theme')).toBeInTheDocument();
      expect(screen.getByTestId('resolved-theme')).toBeInTheDocument();
      expect(screen.getByTestId('set-light')).toBeInTheDocument();
    });
  });
});
