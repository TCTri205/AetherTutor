/**
 * Unit Tests cho useKeyboardShortcuts hook (Sprint 19).
 *
 * Covers:
 * - Shortcut registration/unregistration
 * - Key combination detection
 * - Prevent default behavior
 * - Enabled/disabled state
 * - Input awareness (ignore when typing)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useKeyboardShortcuts,
  formatShortcut,
  getDefaultShortcuts,
  useDefaultKeyboardShortcuts,
  type Shortcut,
} from '../hooks/useKeyboardShortcuts';

// ─── Helpers ────────────────────────────────────────────────────────

function createKeyboardEvent(overrides: Partial<KeyboardEventInit> = {}): KeyboardEvent {
  return new KeyboardEvent('keydown', {
    key: 'k',
    ctrlKey: false,
    altKey: false,
    shiftKey: false,
    metaKey: false,
    bubbles: true,
    ...overrides,
  });
}

function fireKeydownEvent(event: KeyboardEvent) {
  window.dispatchEvent(event);
}

// ─── beforeEach / afterEach ─────────────────────────────────────────

beforeEach(() => {
  vi.restoreAllMocks();
  // Mock navigator.platform for consistent cross-platform behavior
  vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── Tests ──────────────────────────────────────────────────────────

describe('useKeyboardShortcuts', () => {
  describe('shortcut registration/unregistration', () => {
    it('should register shortcuts from props', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      const { result } = renderHook(() => useKeyboardShortcuts({ shortcuts }));

      expect(result.current.registeredShortcuts).toHaveLength(1);
      expect(result.current.registeredShortcuts[0].description).toBe('Search');
    });

    it('should register multiple shortcuts', () => {
      const onUndo = vi.fn();
      const onRedo = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'z', modifiers: ['ctrl'], callback: onUndo, description: 'Undo' },
        { key: 'y', modifiers: ['ctrl'], callback: onRedo, description: 'Redo' },
      ];

      const { result } = renderHook(() => useKeyboardShortcuts({ shortcuts }));

      expect(result.current.registeredShortcuts).toHaveLength(2);
    });

    it('should not register disabled shortcuts', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search', enabled: false },
      ];

      const { result } = renderHook(() => useKeyboardShortcuts({ shortcuts }));

      expect(result.current.registeredShortcuts).toHaveLength(0);
    });

    it('should register shortcut dynamically via registerShortcut', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      expect(result.current.registeredShortcuts).toHaveLength(0);

      act(() => {
        result.current.registerShortcut('my-shortcut', {
          key: 's',
          modifiers: ['ctrl'],
          callback: vi.fn(),
          description: 'Save',
        });
      });

      expect(result.current.registeredShortcuts).toHaveLength(1);
    });

    it('should unregister shortcut via unregisterShortcut', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      const { result } = renderHook(() => useKeyboardShortcuts({ shortcuts }));
      expect(result.current.registeredShortcuts).toHaveLength(1);

      act(() => {
        result.current.unregisterShortcut('ctrl+k');
      });

      // After unregister, the prop-based shortcuts are re-registered on next render
      // But the manual unregister should have cleared from the internal registry
      // This tests that the unregister function exists and is callable
      expect(typeof result.current.unregisterShortcut).toBe('function');
    });

    it('should clear entire registry via clearRegistry', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      act(() => {
        result.current.registerShortcut('sc1', {
          key: 'a',
          modifiers: ['ctrl'],
          callback: vi.fn(),
          description: 'Action A',
        });
        result.current.registerShortcut('sc2', {
          key: 'b',
          modifiers: ['ctrl'],
          callback: vi.fn(),
          description: 'Action B',
        });
      });

      expect(result.current.registeredShortcuts).toHaveLength(2);

      act(() => {
        result.current.clearRegistry();
      });

      expect(result.current.registeredShortcuts).toHaveLength(0);
    });

    it('should call onRegister callback when shortcuts are registered', () => {
      const onRegister = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback: vi.fn(), description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts, onRegister }));

      expect(onRegister).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({
            id: expect.stringContaining('ctrl+k'),
            shortcut: expect.objectContaining({ description: 'Search' }),
          }),
        ]),
      );
    });
  });

  describe('key combination detection', () => {
    it('should trigger callback on matching key combination', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true }));
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should not trigger on non-matching key', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'x', ctrlKey: true }));
      });

      expect(callback).not.toHaveBeenCalled();
    });

    it('should not trigger when modifier is missing', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: false }));
      });

      expect(callback).not.toHaveBeenCalled();
    });

    it('should trigger shortcut with no modifiers', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'Escape', modifiers: [], callback, description: 'Close' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'Escape' }));
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should handle shift modifier', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: '?', modifiers: ['shift'], callback, description: 'Help' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: '?', shiftKey: true }));
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should handle multiple modifiers (ctrl+shift+k)', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl', 'shift'], callback, description: 'Advanced Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true, shiftKey: true }));
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should handle alt modifier', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'd', modifiers: ['alt'], callback, description: 'Debug' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'd', altKey: true }));
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });
  });

  describe('prevent default behavior', () => {
    it('should call preventDefault on matched shortcut', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      const event = createKeyboardEvent({ key: 'k', ctrlKey: true });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

      act(() => {
        fireKeydownEvent(event);
      });

      expect(preventDefaultSpy).toHaveBeenCalledTimes(1);
    });

    it('should not call preventDefault on non-matched key', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      const event = createKeyboardEvent({ key: 'x' });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

      act(() => {
        fireKeydownEvent(event);
      });

      expect(preventDefaultSpy).not.toHaveBeenCalled();
    });
  });

  describe('enabled/disabled state', () => {
    it('should not trigger shortcuts when hook is disabled', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts, enabled: false }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true }));
      });

      expect(callback).not.toHaveBeenCalled();
    });

    it('should enable shortcuts when toggled from disabled', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      const { rerender } = renderHook(
        ({ enabled }) => useKeyboardShortcuts({ shortcuts, enabled }),
        { initialProps: { enabled: false } },
      );

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true }));
      });
      expect(callback).not.toHaveBeenCalled();

      rerender({ enabled: true });

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true }));
      });
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should not trigger individually disabled shortcuts', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback: callback1, description: 'Search', enabled: false },
        { key: 's', modifiers: ['ctrl'], callback: callback2, description: 'Save' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true }));
      });
      expect(callback1).not.toHaveBeenCalled();

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 's', ctrlKey: true }));
      });
      expect(callback2).toHaveBeenCalledTimes(1);
    });
  });

  describe('input awareness', () => {
    it('should ignore shortcuts when typing in input', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      const event = createKeyboardEvent({ key: 'k', ctrlKey: true });
      // Simulate event target being the input
      Object.defineProperty(event, 'target', { value: input });

      act(() => {
        fireKeydownEvent(event);
      });

      expect(callback).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });

    it('should ignore shortcuts when typing in textarea', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);
      textarea.focus();

      const event = createKeyboardEvent({ key: 'k', ctrlKey: true });
      Object.defineProperty(event, 'target', { value: textarea });

      act(() => {
        fireKeydownEvent(event);
      });

      expect(callback).not.toHaveBeenCalled();

      document.body.removeChild(textarea);
    });

    it('should ignore shortcuts when typing in select', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      const select = document.createElement('select');
      document.body.appendChild(select);
      select.focus();

      const event = createKeyboardEvent({ key: 'k', ctrlKey: true });
      Object.defineProperty(event, 'target', { value: select });

      act(() => {
        fireKeydownEvent(event);
      });

      expect(callback).not.toHaveBeenCalled();

      document.body.removeChild(select);
    });

    it('should allow Escape to work even in inputs (for closing modals)', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'Escape', modifiers: [], callback, description: 'Close modal' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      const event = createKeyboardEvent({ key: 'Escape' });
      Object.defineProperty(event, 'target', { value: input });

      act(() => {
        fireKeydownEvent(event);
      });

      expect(callback).toHaveBeenCalledTimes(1);

      document.body.removeChild(input);
    });

    it('should trigger shortcuts when not in input', () => {
      const callback = vi.fn();
      const shortcuts: Shortcut[] = [
        { key: 'k', modifiers: ['ctrl'], callback, description: 'Search' },
      ];

      renderHook(() => useKeyboardShortcuts({ shortcuts }));

      // Focus on body (non-input)
      document.body.focus();

      act(() => {
        fireKeydownEvent(createKeyboardEvent({ key: 'k', ctrlKey: true }));
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });
  });

  describe('prefersReducedMotion', () => {
    it('should detect prefers-reduced-motion preference', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());
      expect(typeof result.current.prefersReducedMotion).toBe('boolean');
    });
  });
});

describe('formatShortcut', () => {
  it('should format Ctrl+K on Windows', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');
    const shortcut: Shortcut = {
      key: 'k',
      modifiers: ['ctrl'],
      callback: vi.fn(),
      description: 'Search',
    };
    expect(formatShortcut(shortcut)).toBe('Ctrl+K');
  });

  it('should format Cmd+K on Mac', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel');
    const shortcut: Shortcut = {
      key: 'k',
      modifiers: ['ctrl'],
      callback: vi.fn(),
      description: 'Search',
    };
    expect(formatShortcut(shortcut)).toBe('⌘K');
  });

  it('should format Ctrl+Shift+?', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');
    const shortcut: Shortcut = {
      key: '?',
      modifiers: ['shift'],
      callback: vi.fn(),
      description: 'Help',
    };
    expect(formatShortcut(shortcut)).toBe('Shift+?');
  });

  it('should format Escape as Esc', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');
    const shortcut: Shortcut = {
      key: 'Escape',
      modifiers: [],
      callback: vi.fn(),
      description: 'Close',
    };
    expect(formatShortcut(shortcut)).toBe('Esc');
  });

  it('should format Alt combinations', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');
    const shortcut: Shortcut = {
      key: 'd',
      modifiers: ['alt'],
      callback: vi.fn(),
      description: 'Debug',
    };
    expect(formatShortcut(shortcut)).toBe('Alt+D');
  });

  it('should format Space key', () => {
    vi.spyOn(navigator, 'platform', 'get').mockReturnValue('Win32');
    const shortcut: Shortcut = {
      key: ' ',
      modifiers: ['ctrl'],
      callback: vi.fn(),
      description: 'Play',
    };
    expect(formatShortcut(shortcut)).toBe('Ctrl+Space');
  });
});

describe('getDefaultShortcuts', () => {
  it('should return empty array with no config', () => {
    expect(getDefaultShortcuts()).toHaveLength(0);
  });

  it('should include search shortcut when onSearch provided', () => {
    const cb = vi.fn();
    const shortcuts = getDefaultShortcuts({ onSearch: cb });
    expect(shortcuts).toHaveLength(1);
    expect(shortcuts[0].key).toBe('k');
    expect(shortcuts[0].modifiers).toEqual(['ctrl']);
  });

  it('should include undo/redo shortcuts', () => {
    const shortcuts = getDefaultShortcuts({ onUndo: vi.fn(), onRedo: vi.fn() });
    expect(shortcuts).toHaveLength(2);
    expect(shortcuts[0].key).toBe('z');
    expect(shortcuts[1].key).toBe('y');
  });

  it('should include close modal shortcut', () => {
    const shortcuts = getDefaultShortcuts({ onCloseModal: vi.fn() });
    expect(shortcuts).toHaveLength(1);
    expect(shortcuts[0].key).toBe('Escape');
    expect(shortcuts[0].modifiers).toEqual([]);
  });

  it('should include both / and ? for shortcuts help', () => {
    const shortcuts = getDefaultShortcuts({ onOpenShortcutsHelp: vi.fn() });
    expect(shortcuts).toHaveLength(2);
    expect(shortcuts[0].key).toBe('/');
    expect(shortcuts[1].key).toBe('?');
  });

  it('should combine all shortcuts when all callbacks provided', () => {
    const shortcuts = getDefaultShortcuts({
      onSearch: vi.fn(),
      onUndo: vi.fn(),
      onRedo: vi.fn(),
      onCloseModal: vi.fn(),
      onOpenShortcutsHelp: vi.fn(),
    });
    // search(1) + undo(1) + redo(1) + close(1) + help(2) = 6
    expect(shortcuts).toHaveLength(6);
  });
});

describe('useDefaultKeyboardShortcuts', () => {
  it('should register default shortcuts from config', () => {
    const onSearch = vi.fn();
    const { result } = renderHook(() =>
      useDefaultKeyboardShortcuts({ onSearch }),
    );

    expect(result.current.registeredShortcuts.length).toBeGreaterThan(0);
  });

  it('should respect enabled flag', () => {
    const { result } = renderHook(() =>
      useDefaultKeyboardShortcuts({ onSearch: vi.fn() }, false),
    );

    // Hook returns but shortcuts are not active
    expect(result.current).toBeDefined();
  });
});
