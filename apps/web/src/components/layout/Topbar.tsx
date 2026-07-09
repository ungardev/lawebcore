import { useAuth } from '@/features/auth/AuthProvider';
import { Button } from '@/components/ui/button';
import { LogOut } from 'lucide-react';

export function Topbar() {
  const { user, signOut } = useAuth();
  return (
    <header className="border-b bg-card px-6 py-3 flex items-center justify-between">
      <div>
        <h2 className="text-sm text-muted-foreground">Bienvenido,</h2>
        <p className="font-medium">{user?.email}</p>
      </div>
      <Button variant="ghost" size="sm" onClick={signOut}>
        <LogOut className="w-4 h-4 mr-2" />
        Salir
      </Button>
    </header>
  );
}