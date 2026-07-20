import { NavLink } from 'react-router-dom';
import {
  Home,
  Megaphone,
  Kanban,
  Building2,
  Sparkles,
  Settings,
  X,
  ChevronLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_MAIN = [
  { to: '/home', label: 'Home', icon: Home, end: true },
  { to: '/campaigns', label: 'Campañas', icon: Megaphone, end: true },
  { to: '/campaigns/kanban', label: 'Pipeline', icon: Kanban },
  { to: '/clients', label: 'Clientes', icon: Building2 },
];

const NAV_AI = [
  { to: '/influencer-lens', label: 'Influencer Lens', icon: Sparkles, badge: 'AI' },
];

const NAV_FOOTER = [
  { to: '/settings', label: 'Configuración', icon: Settings },
];

interface SidebarProps {
  collapsed?: boolean;
  onNavigate?: () => void;
  onCollapse?: () => void;
}

export function Sidebar({ collapsed = false, onNavigate, onCollapse }: SidebarProps) {
  const renderItem = (item: (typeof NAV_MAIN)[number] & { badge?: string; end?: boolean }) => {
    const Icon = item.icon;
    return (
      <NavLink
        key={item.to}
        to={item.to}
        end={item.end}
        onClick={onNavigate}
        className={({ isActive }) =>
          cn(
            'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200',
            collapsed && 'md:justify-center md:px-2.5',
            isActive
              ? 'bg-gradient-to-r from-primary/15 via-accent/10 to-transparent text-foreground shadow-soft'
              : 'text-muted-foreground hover:bg-hover hover:text-foreground'
          )
        }
      >
        {({ isActive }) => (
          <>
            <span
              className={cn(
                'absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full bg-gradient-to-b from-primary via-accent to-secondary transition-all',
                isActive ? 'opacity-100' : 'opacity-0'
              )}
            />
            <Icon
              className={cn(
                'h-[18px] w-[18px] shrink-0 transition-transform group-hover:scale-110',
                isActive && 'text-primary'
              )}
              strokeWidth={isActive ? 2.4 : 2}
            />
            {!collapsed && (
              <>
                <span className="truncate">{item.label}</span>
                {item.badge && (
                  <span className="ml-auto rounded-md bg-gradient-to-r from-primary to-accent px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary-foreground shadow-glow">
                    {item.badge}
                  </span>
                )}
              </>
            )}
            {collapsed && (
              <span className="pointer-events-none absolute left-full ml-3 hidden whitespace-nowrap rounded-md border border-border bg-popover px-2 py-1 text-xs font-medium text-popover-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 md:block">
                {item.label}
              </span>
            )}
          </>
        )}
      </NavLink>
    );
  };

  return (
    <aside
      className={cn(
        'relative flex h-full flex-col border-r border-border/60 bg-sidebar/95 backdrop-blur-xl transition-all duration-300',
        collapsed ? 'w-[72px]' : 'w-64'
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/[0.03] via-transparent to-accent/[0.03]" />

      <div className="relative flex h-16 items-center justify-between border-b border-border/60 px-4">
        <NavLink to="/home" onClick={onNavigate} className="flex items-center gap-2.5">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-accent to-secondary shadow-glow">
            <span className="text-sm font-black text-primary-foreground">W</span>
            <span className="absolute inset-0 rounded-xl bg-gradient-to-tr from-white/20 to-transparent" />
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-bold tracking-tight text-foreground">La Web Figital</span>
              <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Agency · AI
              </span>
            </div>
          )}
        </NavLink>

        {onNavigate && (
          <button
            onClick={onNavigate}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-hover hover:text-foreground md:hidden"
            aria-label="Cerrar menú"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className="relative flex-1 space-y-6 overflow-y-auto px-3 py-5">
        <div className="space-y-1">
          {!collapsed && (
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/70">
              Workspace
            </p>
          )}
          {NAV_MAIN.map(renderItem)}
        </div>

        <div className="space-y-1">
          {!collapsed && (
            <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/70">
              Inteligencia
            </p>
          )}
          {NAV_AI.map(renderItem)}
        </div>
      </nav>

      {!collapsed && (
        <div className="relative mx-3 mb-3 overflow-hidden rounded-xl border border-border/60 bg-gradient-to-br from-primary/8 via-accent/5 to-secondary/8 p-3">
          <div className="absolute -right-6 -top-6 h-16 w-16 rounded-full bg-primary/20 blur-2xl" />
          <div className="relative flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
            </span>
            <span className="text-[11px] font-semibold text-foreground">Motor AI activo</span>
          </div>
          <p className="relative mt-1 text-[10px] leading-relaxed text-muted-foreground">
            Apify + análisis semántico ejecutándose en tiempo real.
          </p>
        </div>
      )}

      <div className="relative border-t border-border/60 px-3 py-3">
        <div className="space-y-1">{NAV_FOOTER.map(renderItem)}</div>

        {onCollapse && (
          <button
            onClick={onCollapse}
            className={cn(
              'mt-2 hidden w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-hover hover:text-foreground md:flex',
              collapsed && 'justify-center'
            )}
            aria-label={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
          >
            <ChevronLeft
              className={cn('h-4 w-4 transition-transform', collapsed && 'rotate-180')}
            />
            {!collapsed && <span>Colapsar</span>}
          </button>
        )}
      </div>
    </aside>
  );
}
