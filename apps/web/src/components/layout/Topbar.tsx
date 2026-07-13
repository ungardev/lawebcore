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
    <header className="border-b bg-card px-4 md:px-6 h-16 flex items-center justify-between gap-2 md:gap-4">
      <div className="flex items-center gap-2 md:gap-3 min-w-0 flex-1">
        {onToggleSidebar && (
          <Button variant="ghost" size="icon" onClick={onToggleSidebar} className="flex-shrink-0">
            <Menu className="w-4 h-4" />
          </Button>
        )}
        <div className="w-9 h-9 rounded-full bg-primary/15 text-primary font-semibold text-sm flex items-center justify-center flex-shrink-0">
          {initialsOf(displayName)}
        </div>
        <div className="min-w-0">
          <h2 className="text-xs md:text-sm text-muted-foreground hidden sm:block">Bienvenido,</h2>
          <p className="font-medium text-sm md:text-base truncate">
            {displayName || (user?.email ? user.email.split('@')[0] : 'Usuario')}
          </p>
        </div>
      </div>
      <Button variant="ghost" size="sm" onClick={signOut} className="flex-shrink-0">
        <LogOut className="w-4 h-4 md:mr-2" />
        <span className="hidden md:inline">Salir</span>
      </Button>
    </header>
  );
}
