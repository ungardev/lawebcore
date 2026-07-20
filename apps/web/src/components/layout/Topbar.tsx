import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/features/auth/AuthProvider';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { LogOut, Search, Bell, Command, PanelLeftClose, PanelLeft } from 'lucide-react';

interface TopbarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Topbar({ collapsed = false, onToggleCollapse }: TopbarProps) {
  const { user, signOut } = useAuth();
  const { data: profile } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => authApi.me(),
    staleTime: 5 * 60 * 1000,
  });

  const displayName =
    profile?.full_name?.trim() ||
    (user?.user_metadata as Record<string, string> | null)?.full_name?.trim() ||
    null;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border/60 bg-background/80 px-4 backdrop-blur-xl md:px-6">
      {onToggleCollapse && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="text-muted-foreground hover:text-foreground"
          aria-label={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
        >
          {collapsed ? (
            <PanelLeft className="h-5 w-5" />
          ) : (
            <PanelLeftClose className="h-5 w-5" />
          )}
        </Button>
      )}

      <div className="flex-1 md:max-w-2xl">
        <div className="group relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
          <input
            type="text"
            placeholder="Buscar campañas, clientes, creadores…"
            className="h-10 w-full rounded-xl border border-border/60 bg-muted/40 pl-10 pr-16 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
          />
          <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-1 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-mono font-medium text-muted-foreground md:inline-flex">
            <Command className="h-3 w-3" /> K
          </kbd>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <Button variant="ghost" size="icon" className="relative" aria-label="Notificaciones">
          <Bell className="h-[18px] w-[18px]" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-gradient-to-br from-primary to-accent shadow-glow" />
        </Button>

        <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/40 py-1.5 pl-1.5 pr-3">
          <div className="hidden flex-col leading-tight sm:flex">
            <span className="text-[11px] text-muted-foreground">Bienvenido</span>
            <span className="max-w-[160px] truncate text-xs font-semibold text-foreground">
              {displayName || (user?.email ? user.email.split('@')[0] : 'Usuario')}
            </span>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => signOut()}
          className="gap-2 text-muted-foreground hover:text-foreground"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden lg:inline">Salir</span>
        </Button>
      </div>
    </header>
  );
}
