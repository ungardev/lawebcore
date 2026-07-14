import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Megaphone,
  Kanban,
  Users,
  Building2,
  Tags,
  Sparkles,
  Settings,
  X,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/campaigns', label: 'Campanas', icon: Megaphone, end: true },
  { to: '/campaigns/kanban', label: 'Pipeline', icon: Kanban },
  { to: '/clients', label: 'Clientes', icon: Building2 },
  { to: '/brands', label: 'Marcas', icon: Tags },
  { to: '/influencers', label: 'Influencers', icon: Users },
  { to: '/ai', label: 'Asistente IA', icon: Sparkles },
  { to: '/discovery', label: 'Discovery', icon: Search },
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
        'h-full border-r bg-card flex flex-col transition-all duration-200',
        collapsed ? 'md:w-16' : 'md:w-64',
        'w-64'
      )}
    >
      <div className={cn('border-b h-16 flex items-center justify-between', collapsed ? 'md:px-3 px-6' : 'px-6')}>
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-blue-500 flex items-center justify-center text-white font-bold flex-shrink-0 shadow-md">
            LW
          </div>
          <div className={cn('overflow-hidden', collapsed && 'md:hidden')}>
            <h1 className="font-bold text-foreground truncate">La Web Core</h1>
            <p className="text-xs text-muted-foreground truncate">Figital Agency</p>
          </div>
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
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground font-medium'
                  : 'text-muted-foreground hover:bg-hover hover:text-foreground',
                collapsed && 'md:justify-center'
              )
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            <span className={cn('truncate', collapsed && 'md:hidden')}>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className={cn('p-4 border-t text-xs text-muted-foreground', collapsed && 'md:p-2 md:text-center')}>
        <p className={cn(collapsed && 'md:hidden')}>v0.1.0 - MVP</p>
        <p className={cn('hidden', collapsed && 'md:block')}>v0.1</p>
      </div>
    </aside>
  );
}
