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
              ? 'bg-gradient-brand text-white shadow-glow'
              : 'text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-foreground'
          )
        }
      >
        {({ isActive }) => (
          <>
            <Icon
              className={cn(
                'h-4 w-4 shrink-0 transition-transform group-hover:scale-110',
                isActive ? 'text-white' : ''
              )}
              strokeWidth={isActive ? 2.2 : 2}
            />
            {!collapsed && (
              <>
                <span className="truncate">{item.label}</span>
                {item.badge && !isActive && (
                  <span className="ml-auto rounded-full bg-gradient-brand px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-white">
                    {item.badge}
                  </span>
                )}
              </>
            )}
            {collapsed && (
              <span className="pointer-events-none absolute left-full ml-3 hidden whitespace-nowrap rounded-md border border-sidebar-border bg-sidebar px-2 py-1 text-xs font-medium text-sidebar-foreground opacity-0 shadow-lg transition-opacity group-hover:opacity-100 md:block">
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
        'relative flex h-full flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300 overflow-hidden',
        collapsed ? 'w-[72px]' : 'w-64'
      )}
    >
      <div className="relative flex h-16 items-center justify-between border-b border-sidebar-border px-4">
        <NavLink to="/home" onClick={onNavigate} className="flex items-center gap-2.5">
          {collapsed ? (
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-brand text-sm font-bold text-white shadow-glow">
              W
            </div>
          ) : (
            <div className="shrink-0">
              <img
                src="/logo-laweb.png"
                alt="La Web"
                className="h-10 w-10 object-contain"
              />
            </div>
          )}
        </NavLink>

        <div className="flex items-center gap-1">
          {onCollapse && (
            <button
              onClick={onCollapse}
              className="hidden md:flex items-center justify-center rounded-lg p-1.5 text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              aria-label={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
            >
              <ChevronLeft
                className={cn('h-4 w-4 transition-transform duration-200', collapsed && 'rotate-180')}
              />
            </button>
          )}
          {onNavigate && (
            <button
              onClick={onNavigate}
              className="rounded-lg p-1.5 text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground md:hidden"
              aria-label="Cerrar menú"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <nav className="relative flex-1 min-w-0 px-3 py-5">
        <div className="h-full space-y-6 overflow-y-auto">
          <div className="space-y-1">
            {!collapsed && (
              <p className="mb-2 px-3 text-[10px] font-medium uppercase tracking-[0.16em] text-sidebar-foreground/40">
                Workspace
              </p>
            )}
            {NAV_MAIN.map(renderItem)}
          </div>

          <div className="space-y-1">
            {!collapsed && (
              <p className="mb-2 px-3 text-[10px] font-medium uppercase tracking-[0.16em] text-sidebar-foreground/40">
                Inteligencia
              </p>
            )}
            {NAV_AI.map(renderItem)}
          </div>
        </div>
      </nav>

      <div className="relative border-t border-sidebar-border px-3 py-3">
        <div className="space-y-1">{NAV_FOOTER.map(renderItem)}</div>

        {!collapsed ? (
          <div className="mt-3 rounded-xl border border-sidebar-border bg-sidebar-accent/40 p-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-brand text-xs font-semibold text-white">
                UV
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-sidebar-foreground">Ungar Villamizar</p>
                <p className="truncate text-[10px] text-sidebar-foreground/50">Agency Owner</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-3 mx-auto flex h-8 w-8 items-center justify-center rounded-full bg-gradient-brand text-xs font-semibold text-white">
            UV
          </div>
        )}
      </div>
    </aside>
  );
}
