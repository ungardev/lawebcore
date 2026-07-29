import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Building2,
  History,
  Home,
  Megaphone,
  Settings,
  Sparkles,
} from 'lucide-react';
import type { LucideProps } from 'lucide-react';
import { useAuth } from '@/features/auth/AuthProvider';
import { authApi } from '@/lib/api';
import { cn } from '@/lib/utils';

const NAV_MAIN = [
  { to: '/home', label: 'Resumen', description: 'Estado general del negocio', icon: Home, end: true },
  { to: '/campaigns', label: 'Campañas', description: 'Gestión y ejecución', icon: Megaphone, end: true },
  { to: '/campaigns/kanban', label: 'Pipeline', description: 'Flujo operativo', icon: Activity },
  { to: '/clients', label: 'Clientes', description: 'Marcas y contactos', icon: Building2 },
];

const NAV_INTELLIGENCE = [
  { to: '/influencer-lens', label: 'Influencer Lens', description: 'Descubrimiento asistido', icon: Sparkles, badge: 'AI' },
  { to: '/influencer-lens/runs', label: 'Historial Lens', description: 'Ejecuciones y resultados', icon: History },
];

const NAV_FOOTER = [
  { to: '/settings', label: 'Configuración', description: 'Preferencias y acceso', icon: Settings },
];

type NavigationItem = {
  to: string;
  label: string;
  description: string;
  icon: React.ForwardRefExoticComponent<Omit<LucideProps, 'ref'> & React.RefAttributes<SVGSVGElement>>;
  end?: boolean;
  badge?: string;
};

interface SidebarProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

export function Sidebar({ collapsed = false, onNavigate }: SidebarProps) {
  const { user } = useAuth();
  const { data: profile } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => authApi.me(),
    staleTime: 5 * 60 * 1000,
  });

  const displayName = profile?.full_name?.trim() || user?.full_name?.trim() || null;
  const initials = displayName
    ? ((displayName.trim().split(/\s+/)[0]?.[0] ?? '') + (displayName.trim().split(/\s+/)[1]?.[0] ?? '')).toUpperCase()
    : '?';

  const renderItem = (item: NavigationItem) => {
    const Icon = item.icon;
    return (
      <NavLink
        key={item.to}
        to={item.to}
        end={item.end}
        onClick={onNavigate}
        title={collapsed ? item.label : undefined}
        className={({ isActive }) =>
          cn(
            'group relative flex min-h-10 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-ring',
            collapsed && 'md:justify-center md:px-1',
            isActive
              ? 'bg-sidebar-accent text-sidebar-foreground'
              : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground',
          )
        }
      >
        {({ isActive }) => (
          <>
            <span className={cn('absolute inset-y-2 left-0 w-0.5 rounded-full transition-colors', isActive ? 'bg-sidebar-primary' : 'bg-transparent group-hover:bg-sidebar-primary/40')} />
            <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-sidebar-primary' : 'text-sidebar-foreground/50 group-hover:text-sidebar-foreground')} strokeWidth={isActive ? 2.2 : 1.8} aria-hidden="true" />
            {!collapsed && (
              <>
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
                {item.badge && <span className="rounded border border-sidebar-primary/30 bg-sidebar-primary/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-sidebar-primary">{item.badge}</span>}
              </>
            )}
            {collapsed && (
              <span className="pointer-events-none absolute right-full z-30 mr-2 hidden whitespace-nowrap rounded border border-divider bg-panel-raised px-2 py-1 text-xs font-medium text-foreground opacity-0 shadow-elevated transition-opacity group-hover:opacity-100 md:block">
                {item.label}
              </span>
            )}
          </>
        )}
      </NavLink>
    );
  };

  return (
    <aside className={cn('flex h-full flex-col overflow-hidden overflow-x-hidden border-r border-divider bg-sidebar transition-[width] duration-200', collapsed ? 'w-16' : 'w-60')}>
      <div className={cn('flex h-16 shrink-0 items-center justify-center border-b border-sidebar-border', collapsed ? 'px-2' : 'px-4')}>
        <NavLink to="/home" onClick={onNavigate} className="focus-ring rounded-md" aria-label="Ir al resumen">
          {collapsed ? (
            <img src="/logo-laweb-collapsed.png" alt="La Web" className="h-8 w-8 object-contain" />
          ) : (
            <img src="/logo-laweb.png" alt="La Web" className="h-11 w-auto object-contain" />
          )}
        </NavLink>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-2 py-5" aria-label="Navegación principal">
        <NavGroup label="Workspace" items={NAV_MAIN} collapsed={collapsed} renderItem={renderItem} />
        <NavGroup label="Inteligencia" items={NAV_INTELLIGENCE} collapsed={collapsed} renderItem={renderItem} />
      </nav>

      <div className="shrink-0 border-t border-sidebar-border px-2 py-3">
        <div className="space-y-1">{NAV_FOOTER.map(renderItem)}</div>
        {collapsed ? (
          <div className="mx-auto mt-3 flex h-8 w-8 items-center justify-center rounded-md border border-sidebar-border bg-sidebar-accent text-xs font-semibold text-sidebar-foreground" title={displayName || 'Usuario'}>
            {initials}
          </div>
        ) : (
          <div className="mt-3 flex items-center gap-2 rounded-md border border-sidebar-border bg-sidebar-accent/60 p-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary/15 text-xs font-semibold text-sidebar-primary">{initials}</div>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-sidebar-foreground">{displayName || (user?.email ? user.email.split('@')[0] : 'Usuario')}</p>
              <p className="truncate text-[10px] text-sidebar-foreground/50">Agency Owner</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

function NavGroup({
  label,
  items,
  collapsed,
  renderItem,
}: {
  label: string;
  items: readonly NavigationItem[];
  collapsed: boolean;
  renderItem: (item: NavigationItem) => React.ReactNode;
}) {
  return (
    <div className="mb-6 last:mb-0">
      {!collapsed && <p className="mb-2 px-3 text-eyebrow text-sidebar-foreground/35">{label}</p>}
      <div className="space-y-1">{items.map(renderItem)}</div>
    </div>
  );
}
