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
  { to: '/settings', label: 'Configuracion', icon: Settings },
];

interface SidebarProps {
  collapsed?: boolean;
}

export function Sidebar({ collapsed = false }: SidebarProps) {
  return (
    <aside
      className={cn(
        'border-r bg-card flex flex-col transition-all duration-200',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className={cn('border-b', collapsed ? 'p-3' : 'p-6')}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-rose-300 via-purple-400 to-blue-600 flex items-center justify-center text-white font-bold flex-shrink-0 shadow-md">
            LW
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="font-bold text-foreground truncate">La Web Core</h1>
              <p className="text-xs text-muted-foreground truncate">Figital Agency</p>
            </div>
          )}
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end ?? false}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                collapsed && 'justify-center'
              )
            }
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span className="truncate">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className={cn('p-4 border-t text-xs text-muted-foreground', collapsed && 'p-2 text-center')}>
        {!collapsed && <p>v0.1.0 - MVP</p>}
        {collapsed && <p>v0.1</p>}
      </div>
    </aside>
  );
}
