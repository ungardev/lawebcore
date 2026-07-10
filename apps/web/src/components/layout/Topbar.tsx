import { useAuth } from '@/features/auth/AuthProvider';
import { Button } from '@/components/ui/button';
import { LogOut, Menu } from 'lucide-react';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { user, signOut } = useAuth();
  return (
    <header className="border-b bg-card px-4 md:px-6 h-16 flex items-center justify-between gap-2 md:gap-4">
      <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
        {onToggleSidebar && (
          <Button variant="ghost" size="icon" onClick={onToggleSidebar} className="flex-shrink-0">
            <Menu className="w-4 h-4" />
          </Button>
        )}
        <div className="min-w-0">
          <h2 className="text-xs md:text-sm text-muted-foreground hidden sm:block">Bienvenido,</h2>
          <p className="font-medium text-sm md:text-base truncate">{user?.email}</p>
        </div>
      </div>
      <Button variant="ghost" size="sm" onClick={signOut} className="flex-shrink-0">
        <LogOut className="w-4 h-4 md:mr-2" />
        <span className="hidden md:inline">Salir</span>
      </Button>
    </header>
  );
}
