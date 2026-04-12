import { useEffect, useRef, useCallback, useState } from 'react';

export interface Shortcut {
  key: string;
  modifiers: Array<'ctrl' | 'alt' | 'shift' | 'meta'>;
  callback: () => void;
  description: string;
  enabled?: boolean;
}

export interface ShortcutRegistryEntry {
  id: string;
  shortcut: Shortcut;
}

interface ModifierState {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
}

const MODIFIER_KEYS = new Set(['Control', 'Alt', 'Shift', 'Meta']);

function isModifierKey(key: string): boolean {
  return MODIFIER_KEYS.has(key);
}

function getModifierState(event: KeyboardEvent): ModifierState {
  return {
    ctrl: event.ctrlKey,
    alt: event.altKey,
    shift: event.shiftKey,
    meta: event.metaKey,
  };
}

function modifiersMatch(
  eventModifiers: ModifierState,
  requiredModifiers: Array<'ctrl' | 'alt' | 'shift' | 'meta'>,
): boolean {
  const expected: ModifierState = {
    ctrl: false,
    alt: false,
    shift: false,
    meta: false,
  };

  requiredModifiers.forEach((mod) => {
    expected[mod] = true;
  });

  // On macOS, Cmd should be treated as Ctrl for common shortcuts
  const isMac = navigator.platform.toUpperCase().includes('MAC');
  const ctrlMatch =
    eventModifiers.ctrl === expected.ctrl &&
    eventModifiers.meta === expected.meta;

  // Allow Cmd to substitute for Ctrl (and vice versa) for UX consistency
  const primaryMatch =
    (eventModifiers.ctrl && (expected.ctrl || expected.meta)) ||
    (eventModifiers.meta && (expected.meta || expected.ctrl)) ||
    (!eventModifiers.ctrl && !eventModifiers.meta && !expected.ctrl && !expected.meta);

  return (
    primaryMatch &&
    eventModifiers.alt === expected.alt &&
    eventModifiers.shift === expected.shift
  );
}

export function formatShortcut(shortcut: Shortcut): string {
  const isMac = navigator.platform.toUpperCase().includes('MAC');
  const parts: string[] = [];

  const hasCtrl = shortcut.modifiers.includes('ctrl');
  const hasMeta = shortcut.modifiers.includes('meta');

  // On Mac, show Cmd symbol for Ctrl shortcuts and vice versa for UX
  if (isMac) {
    if (hasCtrl || hasMeta) {
      parts.push('⌘');
    }
  } else {
    if (hasCtrl) {
      parts.push('Ctrl');
    }
    if (hasMeta) {
      parts.push('Win');
    }
  }

  if (shortcut.modifiers.includes('alt')) {
    parts.push(isMac ? '⌥' : 'Alt');
  }
  if (shortcut.modifiers.includes('shift')) {
    parts.push(isMac ? '⇧' : 'Shift');
  }

  // Normalize key display
  let displayKey = shortcut.key.toUpperCase();
  if (shortcut.key === ' ') {
    displayKey = 'Space';
  } else if (shortcut.key === '/') {
    displayKey = '/';
  } else if (shortcut.key === '?') {
    displayKey = '?';
  } else if (shortcut.key === 'Escape') {
    displayKey = 'Esc';
  } else if (displayKey.length === 1) {
    displayKey = displayKey.toUpperCase();
  }

  parts.push(displayKey);

  const separator = isMac ? '' : '+';
  return parts.join(separator);
}

function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion;
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean;
  shortcuts?: Shortcut[];
  onRegister?: (registry: ShortcutRegistryEntry[]) => void;
}

export function useKeyboardShortcuts({
  enabled = true,
  shortcuts = [],
  onRegister,
}: UseKeyboardShortcutsOptions = {}) {
  const prefersReducedMotion = useReducedMotion();
  const shortcutsRef = useRef<Shortcut[]>(shortcuts);
  const registryRef = useRef<Map<string, Shortcut>>(new Map());
  const [registeredShortcuts, setRegisteredShortcuts] = useState<Shortcut[]>(
    [],
  );

  // Keep ref in sync
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  // Update registry when shortcuts change
  useEffect(() => {
    const newRegistry = new Map<string, Shortcut>();

    // Add built-in shortcuts first
    shortcuts.forEach((shortcut) => {
      const id = `${shortcut.modifiers.join('+')}+${shortcut.key}`;
      if (shortcut.enabled !== false) {
        newRegistry.set(id, shortcut);
      }
    });

    registryRef.current = newRegistry;
    setRegisteredShortcuts(Array.from(newRegistry.values()));

    if (onRegister) {
      onRegister(
        Array.from(newRegistry.entries()).map(([id, shortcut]) => ({
          id,
          shortcut,
        })),
      );
    }
  }, [shortcuts, onRegister]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) {
        return;
      }

      // Ignore if user is typing in an input
      const target = event.target as HTMLElement;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable;

      // Allow Escape to work even in inputs (for closing modals)
      if (isInput && event.key !== 'Escape') {
        return;
      }

      // Skip modifier keys themselves
      if (isModifierKey(event.key)) {
        return;
      }

      const eventModifiers = getModifierState(event);

      const registry = registryRef.current;
      for (const shortcut of registry.values()) {
        if (shortcut.enabled === false) {
          continue;
        }

        const keyMatch =
          event.key.toLowerCase() === shortcut.key.toLowerCase() ||
          event.key === shortcut.key;

        if (keyMatch && modifiersMatch(eventModifiers, shortcut.modifiers)) {
          event.preventDefault();
          shortcut.callback();
          break;
        }
      }
    },
    [enabled],
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Respect prefers-reduced-motion: if enabled, disable certain animations
    // The hook still works, but callbacks can use this info
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown, prefersReducedMotion]);

  // Registry management functions
  const registerShortcut = useCallback(
    (id: string, shortcut: Shortcut) => {
      const newRegistry = new Map(registryRef.current);
      newRegistry.set(id, shortcut);
      registryRef.current = newRegistry;
      setRegisteredShortcuts(Array.from(newRegistry.values()));
    },
    [],
  );

  const unregisterShortcut = useCallback((id: string) => {
    const newRegistry = new Map(registryRef.current);
    newRegistry.delete(id);
    registryRef.current = newRegistry;
    setRegisteredShortcuts(Array.from(newRegistry.values()));
  }, []);

  const clearRegistry = useCallback(() => {
    registryRef.current.clear();
    setRegisteredShortcuts([]);
  }, []);

  return {
    registeredShortcuts,
    registerShortcut,
    unregisterShortcut,
    clearRegistry,
    prefersReducedMotion,
  };
}

// Default built-in shortcuts configuration
export interface DefaultShortcutsConfig {
  onSearch?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onCloseModal?: () => void;
  onOpenShortcutsHelp?: () => void;
}

export function getDefaultShortcuts(
  config: DefaultShortcutsConfig = {},
): Shortcut[] {
  const {
    onSearch,
    onUndo,
    onRedo,
    onCloseModal,
    onOpenShortcutsHelp,
  } = config;

  const shortcuts: Shortcut[] = [];

  if (onSearch) {
    shortcuts.push({
      key: 'k',
      modifiers: ['ctrl'],
      callback: onSearch,
      description: 'Open search',
    });
  }

  if (onUndo) {
    shortcuts.push({
      key: 'z',
      modifiers: ['ctrl'],
      callback: onUndo,
      description: 'Undo',
    });
  }

  if (onRedo) {
    shortcuts.push({
      key: 'y',
      modifiers: ['ctrl'],
      callback: onRedo,
      description: 'Redo',
    });
  }

  if (onCloseModal) {
    shortcuts.push({
      key: 'Escape',
      modifiers: [],
      callback: onCloseModal,
      description: 'Close modal/panel',
    });
  }

  if (onOpenShortcutsHelp) {
    shortcuts.push(
      {
        key: '/',
        modifiers: ['ctrl'],
        callback: onOpenShortcutsHelp,
        description: 'Show keyboard shortcuts',
      },
      {
        key: '?',
        modifiers: ['shift'],
        callback: onOpenShortcutsHelp,
        description: 'Show keyboard shortcuts',
      },
    );
  }

  return shortcuts;
}

// Hook wrapper for default shortcuts
export function useDefaultKeyboardShortcuts(
  config: DefaultShortcutsConfig = {},
  enabled = true,
) {
  const shortcuts = getDefaultShortcuts(config);
  return useKeyboardShortcuts({ enabled, shortcuts });
}
