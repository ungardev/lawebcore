import { NavLink } from 'react-router-dom';
import {
  Home,
  Megaphone,
  Kanban,
  Building2,
  Sparkles,
  Settings,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { to: '/home', label: 'Home', icon: Home, end: true },
  { to: '/campaigns', label: 'Campanas', icon: Megaphone, end: true },
  { to: '/campaigns/kanban', label: 'Pipeline', icon: Kanban },
  { to: '/clients', label: 'Clientes', icon: Building2 },
  { to: '/influencer-lens', label: 'Influencer Lens', icon: Sparkles },
  { to: '/settings', label: 'Configuracion', icon: Settings },
];

interface SidebarProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

export function Sidebar({ collapsed = false, onNavigate }: SidebarProps) {
  return (
    <aside
      className={cn(
        'h-full flex flex-col glass border-r border-border/40 transition-all duration-200 relative',
        collapsed ? 'md:w-16' : 'md:w-56',
        'w-56'
      )}
    >
      <div
        className={cn(
          'border-b border-border/40 h-14 flex items-center justify-between',
          collapsed ? 'md:px-3 px-4' : 'px-4'
        )}
      >
        <div className="flex items-center gap-3 overflow-hidden">
          {collapsed ? (
            <div className="w-10 h-10 rounded-xl gradient-brand flex items-center justify-center text-white shadow-glow flex-shrink-0">
              <span className="text-lg leading-none font-bold">W</span>
            </div>
          ) : (
            <div className="h-11 flex items-center flex-shrink-0">
              <img
                src="/logo-laweb.png"
                alt="La Web Figital Agency"
                className="h-11 w-auto object-contain"
              />
            </div>
          )}
        </div>
        {onNavigate && (
          <button
            onClick={onNavigate}
            className="md:hidden p-2 hover:bg-hover rounded-lg"
            aria-label="Cerrar menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end ?? false}
            title={collapsed ? item.label : undefined}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150',
                isActive
                  ? 'bg-gradient-to-r from-brand-pink/10 via-brand-purple/10 to-brand-blue/10 text-foreground font-medium shadow-soft'
                  : 'text-muted-foreground hover:bg-hover hover:text-foreground',
                collapsed && 'md:justify-center'
              )
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            <span className={cn('truncate', collapsed && 'md:hidden')}>
              {item.label}
            </span>
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-border/40">
        <div
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg bg-gradient-to-r from-brand-pink/5 via-brand-purple/5 to-brand-blue/5',
            collapsed && 'md:justify-center'
          )}
        >
          <div className="w-6 h-6 rounded-md gradient-brand flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-3 h-3 text-white" />
          </div>
          <span
            className={cn(
              'text-xs font-medium text-foreground/80',
              collapsed && 'md:hidden'
            )}
          >
            AI Assistant
          </span>
        </div>
      </div>
    </aside>
  );
}
