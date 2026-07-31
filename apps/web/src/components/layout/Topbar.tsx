import { useState } from 'react';
import { Bell, ChevronRight, Menu, PanelLeft, PanelLeftClose, Search } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { GlobalSearchDialog } from './GlobalSearchDialog';
import { useAuth } from '@/features/auth/AuthProvider';
import { authApi } from '@/lib/api';

interface TopbarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onOpenMobileMenu?: () => void;
}

const ROUTE_LABELS: Record<string, string> = {
  '/home': 'Home',
  '/campaigns': 'Campañas',
  '/campaigns/kanban': 'Pipeline',
  '/clients': 'Clientes',
  '/lens': 'Lens',
  '/lens/runs': 'Historial Lens',
  '/lens/search': 'Nueva búsqueda',
  '/settings': 'Configuración',
};

export function Topbar({ collapsed = false, onToggleCollapse, onOpenMobileMenu }: TopbarProps) {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const [searchOpen, setSearchOpen] = useState(false);
  const { data: profile } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => authApi.me(),
    staleTime: 5 * 60 * 1000,
  });

  const displayName = profile?.full_name?.trim() || user?.full_name?.trim() || null;
  const currentLabel = ROUTE_LABELS[location.pathname] ?? (location.pathname.startsWith('/campaigns/') ? 'Campaña' : 'La Web Core');

  return (
    <>
      <header className="z-30 flex min-h-16 shrink-0 items-center gap-3 border-b border-divider bg-background px-4 md:px-6">
        {onOpenMobileMenu && (
          <Button variant="ghost" size="icon" onClick={onOpenMobileMenu} className="md:hidden" aria-label="Abrir navegación">
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>
        )}
        {onToggleCollapse && (
          <Button variant="ghost" size="icon" onClick={onToggleCollapse} className="hidden text-muted-foreground hover:text-foreground md:inline-flex" aria-label={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}>
            {collapsed ? <PanelLeft className="h-4 w-4" aria-hidden="true" /> : <PanelLeftClose className="h-4 w-4" aria-hidden="true" />}
          </Button>
        )}

        <div className="hidden items-center gap-2 text-xs text-muted-foreground md:flex" aria-label="Ubicación actual">
          <span className="font-medium text-foreground">P.I.A.R.</span>
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" aria-hidden="true" />
          <span>{currentLabel}</span>
        </div>

        <Button
          type="button"
          variant="outline"
          onClick={() => setSearchOpen(true)}
          className="group ml-auto h-9 min-w-0 flex-1 justify-start gap-2 border-divider bg-surface-sunken px-3 text-left font-normal text-muted-foreground hover:border-primary/50 hover:bg-surface-raised md:ml-6 md:max-w-xl"
          aria-label="Abrir búsqueda global"
        >
          <Search className="h-4 w-4 shrink-0 transition-colors group-hover:text-primary" aria-hidden="true" />
          <span className="truncate text-xs">Buscar campañas, clientes, creadores…</span>
          <kbd className="ml-auto hidden shrink-0 items-center gap-1 rounded border border-divider bg-surface-raised px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground sm:inline-flex">⌘ K</kbd>
        </Button>

        <div className="ml-auto flex items-center gap-1.5 md:gap-2">
          <Button variant="ghost" size="icon" className="relative text-muted-foreground hover:text-foreground" aria-label="Notificaciones">
            <Bell className="h-[17px] w-[17px]" aria-hidden="true" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
          </Button>
          <div className="hidden max-w-[150px] border-l border-divider pl-3 leading-tight sm:block">
            <span className="block truncate text-[10px] text-muted-foreground">Sesión activa</span>
            <span className="block truncate text-xs font-semibold text-foreground">{displayName || (user?.email ? user.email.split('@')[0] : 'Usuario')}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => signOut()} className="text-xs text-muted-foreground hover:text-foreground">
            Salir
          </Button>
        </div>
      </header>
      <GlobalSearchDialog open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  );
}
