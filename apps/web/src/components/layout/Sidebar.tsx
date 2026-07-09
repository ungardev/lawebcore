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
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/campaigns', label: 'Campanas', icon: Megaphone },
  { to: '/campaigns/kanban', label: 'Pipeline', icon: Kanban },
  { to: '/clients', label: 'Clientes', icon: Building2 },
  { to: '/brands', label: 'Marcas', icon: Tags },
  { to: '/influencers', label: 'Influencers', icon: Users },
  { to: '/ai', label: 'Asistente IA', icon: Sparkles },
  { to: '/settings', label: 'Configuracion', icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      <div className="p-6 border-b">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center text-white font-bold">
            LW
          </div>
          <div>
            <h1 className="font-bold text-foreground">La Web Core</h1>
            <p className="text-xs text-muted-foreground">Figital Agency</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/dashboard'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
              )
            }
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t text-xs text-muted-foreground">
        <p>v0.1.0 - MVP</p>
      </div>
    </aside>
  );
}