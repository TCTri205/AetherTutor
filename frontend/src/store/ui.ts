import { create } from 'zustand';

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean;
  mobileMenuOpen: boolean;
  toggleSidebar: () => void;
  setMobileMenuOpen: (open: boolean) => void;

  // Theme
  isDark: boolean;
  toggleTheme: () => void;

  // LLM Health
  llmMode: 'local' | 'cloud' | 'unknown';
  llmProvider: string;
  llmModel: string;
  setLlmInfo: (info: { mode: 'local' | 'cloud'; provider: string; model: string }) => void;
}

export const useUIStore = create<UIState>((set) => ({
  // Sidebar
  sidebarCollapsed: false,
  mobileMenuOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),

  // Theme
  isDark: true,
  toggleTheme: () => set((state) => ({ isDark: !state.isDark })),

  // LLM Health
  llmMode: 'unknown',
  llmProvider: '',
  llmModel: '',
  setLlmInfo: (info) => set({
    llmMode: info.mode,
    llmProvider: info.provider,
    llmModel: info.model,
  }),
}));
