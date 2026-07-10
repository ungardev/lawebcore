import { useAuth } from '@/features/auth/AuthProvider';
import { Button } from '@/components/ui/button';
import { LogOut, Menu } from 'lucide-react';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { user, signOut } = useAuth();
  return (
    <header className="border-b bg-card px-6 py-3 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <Button variant="ghost" size="icon" onClick={onToggleSidebar}>
            <Menu className="w-4 h-4" />
          </Button>
        )}
        <div>
          <h2 className="text-sm text-muted-foreground">Bienvenido,</h2>
          <p className="font-medium">{user?.email}</p>
        </div>
      </div>
      <Button variant="ghost" size="sm" onClick={signOut}>
        <LogOut className="w-4 h-4 mr-2" />
        Salir
      </Button>
    </header>
  );
}
