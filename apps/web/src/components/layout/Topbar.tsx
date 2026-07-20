import { useQuery } from '@tanstack/react-query';
import { useLocation } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthProvider';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { LogOut, Menu, Search, Sparkles } from 'lucide-react';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

const ROUTE_TITLES: Record<string, string> = {
  '/home': 'Dashboard',
  '/campaigns': 'Campanas',
  '/campaigns/kanban': 'Pipeline',
  '/clients': 'Clientes',
  '/influencer-lens': 'Influencer Lens',
  '/settings': 'Configuracion',
};

function initialsOf(name: string | null | undefined): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?';
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { user, signOut } = useAuth();
  const location = useLocation();

  const { data: profile } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => authApi.me(),
    staleTime: 5 * 60 * 1000,
  });

  const displayName =
    profile?.full_name?.trim() ||
    (user?.user_metadata as Record<string, string> | null)?.full_name?.trim() ||
    null;

  const pageTitle =
    ROUTE_TITLES[location.pathname] ||
    ROUTE_TITLES[Object.keys(ROUTE_TITLES).find((k) =>
      location.pathname.startsWith(k)
    ) || ''] ||
    'Dashboard';

  return (
    <header className="h-14 glass border-b border-border/40 flex items-center justify-between px-4 gap-3 sticky top-0 z-20">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {onToggleSidebar && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onToggleSidebar}
            className="flex-shrink-0 h-8 w-8 hover:bg-hover"
          >
            <Menu className="w-4 h-4" />
          </Button>
        )}
        <div className="hidden sm:flex items-center gap-2 flex-1 max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Buscar..."
              className="w-full h-9 pl-9 pr-4 rounded-lg bg-muted/60 border border-border/60 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand-purple/30 focus:border-brand-purple/40 transition-all"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden md:inline-flex h-5 items-center gap-1 rounded border border-border/60 bg-muted/80 px-1.5 font-mono text-[10px] text-muted-foreground">
              <span className="text-xs">⌘</span>K
            </kbd>
          </div>
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <h1 className="text-sm font-semibold text-foreground truncate hidden md:block">
            {pageTitle}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 hover:bg-hover relative"
        >
          <Sparkles className="w-4 h-4 text-brand-purple" />
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-brand-pink animate-pulse" />
        </Button>

        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-pink via-brand-purple to-brand-blue flex items-center justify-center text-white font-semibold text-xs shadow-soft">
          {initialsOf(displayName)}
        </div>

        <div className="hidden sm:block min-w-0">
          <p className="text-xs text-muted-foreground truncate max-w-[120px]">
            {displayName || user?.email?.split('@')[0] || 'Usuario'}
          </p>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={signOut}
          className="h-8 px-2 text-xs gap-1 hover:bg-hover"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Salir</span>
        </Button>
      </div>
    </header>
  );
}
