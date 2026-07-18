import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/features/auth/AuthProvider';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { LogOut, Menu } from 'lucide-react';

interface TopbarProps {
  onToggleSidebar?: () => void;
}

function initialsOf(name: string | null | undefined): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?';
}

export function Topbar({ onToggleSidebar }: TopbarProps) {
  const { user, signOut } = useAuth();
  const { data: profile } = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => authApi.me(),
    staleTime: 5 * 60 * 1000,
  });
  const displayName =
    profile?.full_name?.trim() ||
    (user?.user_metadata as Record<string, string> | null)?.full_name?.trim() ||
    null;

  return (
    <header className="border-b bg-card px-4 h-14 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {onToggleSidebar && (
          <Button variant="ghost" size="icon" onClick={onToggleSidebar} className="flex-shrink-0 h-8 w-8">
            <Menu className="w-4 h-4" />
          </Button>
        )}
        <div className="w-8 h-8 rounded-full bg-primary/15 text-primary font-semibold text-xs flex items-center justify-center flex-shrink-0">
          {initialsOf(displayName)}
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground hidden sm:block">Bienvenido,</p>
          <p className="text-sm font-medium truncate">
            {displayName || (user?.email ? user.email.split('@')[0] : 'Usuario')}
          </p>
        </div>
      </div>
      <Button variant="ghost" size="sm" onClick={signOut} className="flex-shrink-0 h-8 text-xs gap-1.5">
        <LogOut className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Salir</span>
      </Button>
    </header>
  );
}
