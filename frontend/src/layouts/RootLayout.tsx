import { useState, useEffect } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Library,
  MessageSquareQuote,
  Share2,
  Settings,
  Zap,
  Menu,
  ChevronRight,
  X,
  Cloud,
  Lock,
  Loader2,
  Brain,
  FileQuestion,
  FileText,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../lib/utils';
import { Toaster } from '../components/ui/Toaster';
import { Button } from '../components/ui/Button';
import { useUIStore } from '../store/ui';
import { healthService } from '../services/health';
import { toast } from 'sonner';
import { ThemeToggle } from '../components/shared/ThemeToggle';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/vault', label: 'Knowledge Vault', icon: Library },
  { path: '/chat', label: 'Socratic Tutor', icon: MessageSquareQuote },
  { path: '/graph', label: 'Graph Explorer', icon: Share2 },
  { path: '/flashcards', label: 'Flashcards', icon: Brain },
  { path: '/quiz', label: 'Quiz Examiner', icon: FileQuestion },
  { path: '/notes', label: 'Zettelkasten', icon: FileText },
];

export default function RootLayout() {
  const location = useLocation();
  const { mobileMenuOpen, setMobileMenuOpen, llmMode, llmProvider, llmModel, setLlmInfo } = useUIStore();
  const [loadingHealth, setLoadingHealth] = useState(true);

  // Fetch health on mount
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const health = await healthService.checkHealth();
        setLlmInfo({
          mode: health.llm.mode,
          provider: health.llm.provider,
          model: health.llm.model,
        });
        setLoadingHealth(false);
      } catch (err) {
        console.error('Health check failed:', err);
        setLoadingHealth(false);
      }
    };

    fetchHealth();
  }, [setLlmInfo]);

  return (
    <div className="flex h-screen w-full bg-bg-primary text-text-primary overflow-hidden font-sans selection:bg-accent-primary/30">
      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-bg-overlay/60 z-30 md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-64 border-r border-border-primary glass-dark flex-col z-20 shadow-xl shadow-accent-primary/5">
        <SidebarContent />
      </aside>

      {/* Sidebar - Mobile Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            role="navigation"
            aria-label="Main navigation"
            className="fixed left-0 top-0 bottom-0 w-72 border-r border-border-primary glass-dark flex-col z-40 md:hidden shadow-xl"
          >
            <div className="absolute right-4 top-4">
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-2 rounded-xl hover:bg-bg-tertiary transition-colors"
              >
                <X className="w-5 h-5 text-text-primary" />
              </button>
            </div>
            <SidebarContent />
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="flex-1 relative flex flex-col overflow-hidden bg-bg-secondary">
        {/* Background Decorative Elements */}
        <div className="absolute top-[-10%] left-[20%] w-[50%] h-[30%] bg-accent-primary/20 blur-[150px] pointer-events-none opacity-40 rounded-full animate-pulse-slow" />
        <div className="absolute bottom-[-10%] right-[10%] w-[40%] h-[30%] bg-accent-primary/10 blur-[130px] pointer-events-none opacity-30 rounded-full" />

        <header className="h-20 border-b border-border-primary/50 flex items-center justify-between px-8 z-10 glass-dark">
          <div className="flex items-center gap-4">
            {/* P1.2: Hamburger button với logic toggle */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden rounded-xl"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu className="w-6 h-6" />
            </Button>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-accent-primary tracking-[0.15em] uppercase">Space</span>
              <h1 className="text-xl font-bold tracking-tight text-text-primary">
                {navItems.find(item => location.pathname.startsWith(item.path))?.label || 'AetherTutor'}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-6">
            {/* Theme Toggle */}
            <ThemeToggle />

            {/* P1.1: LLM Mode Badge */}
            <div className="hidden sm:flex items-center gap-3 px-4 py-2 rounded-xl bg-bg-tertiary/50 border border-border-primary" role="status" aria-label={`LLM mode: ${llmMode}`}>
              {loadingHealth ? (
                <Loader2 className="w-4 h-4 animate-spin text-text-tertiary" />
              ) : (
                <>
                  {llmMode === 'local' ? (
                    <Lock className="w-4 h-4 text-accent-success" />
                  ) : llmMode === 'cloud' ? (
                    <Cloud className="w-4 h-4 text-accent-primary" />
                  ) : null}
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-text-primary/80 uppercase tracking-wider">
                      {llmMode === 'local' ? 'Local' : llmMode === 'cloud' ? 'Cloud' : 'Unknown'}
                    </span>
                    <span className="text-[10px] text-text-tertiary leading-none">
                      {llmModel || llmProvider || '—'}
                    </span>
                  </div>
                </>
              )}
            </div>

            <div className="flex items-center gap-6">
              <div className="flex flex-col items-end hidden sm:flex">
                <span className="text-xs font-bold text-text-primary/80">Alpha Explorer</span>
                <span className="text-[10px] text-text-tertiary uppercase tracking-widest leading-none">System Online</span>
              </div>
              <div className="w-10 h-10 rounded-xl bg-bg-tertiary/50 border border-border-primary flex items-center justify-center hover:bg-bg-tertiary transition-colors cursor-pointer">
                 <div className="w-2 h-2 rounded-full bg-accent-success animate-pulse" />
              </div>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-8 z-10 scrollbar-hide">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <Toaster />
    </div>
  );
}

// Extracted Sidebar content for reuse
function SidebarContent() {
  const location = useLocation();

  return (
    <>
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-accent-primary to-blue-400 flex items-center justify-center shadow-lg shadow-accent-primary/20">
          <Zap className="w-6 h-6 text-text-inverse fill-text-inverse" />
        </div>
        <div className="flex flex-col">
          <span className="text-xl font-bold tracking-tight text-text-primary leading-tight">
            Aether<span className="text-accent-primary">Tutor</span>
          </span>
          <span className="text-[10px] text-text-tertiary font-bold tracking-[0.2em] uppercase">
            Agentic Learning
          </span>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-1.5 mt-6">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group relative",
              isActive
                ? "bg-accent-primary/10 text-accent-primary"
                : "text-text-tertiary hover:text-text-primary hover:bg-bg-tertiary/50"
            )}
          >
            {({ isActive }) => (
              <>
                <item.icon className={cn("w-5 h-5 transition-transform duration-300 group-hover:scale-110", isActive ? "text-accent-primary" : "text-text-tertiary group-hover:text-text-primary")} />
                <span className="font-semibold tracking-tight">{item.label}</span>
                {isActive ? (
                  <>
                    <motion.div
                      layoutId="active-nav-indicator"
                      className="absolute left-0 w-1.5 h-6 bg-accent-primary rounded-r-full shadow-[0_0_15px_rgba(59,130,246,0.5)]"
                    />
                    <ChevronRight className="w-4 h-4 ml-auto text-accent-primary opacity-50" />
                  </>
                ) : (
                  <ChevronRight className="w-4 h-4 ml-auto opacity-0 -translate-x-2 transition-all group-hover:opacity-30 group-hover:translate-x-0" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border-primary">
        <Button
          variant="ghost"
          className="w-full justify-start gap-3 rounded-xl font-semibold text-text-tertiary hover:text-text-primary"
          onClick={() => toast.info('Settings page coming soon in v2', { duration: 2000 })}
        >
          <Settings className="w-5 h-5" />
          Settings
        </Button>
      </div>
    </>
  );
}
