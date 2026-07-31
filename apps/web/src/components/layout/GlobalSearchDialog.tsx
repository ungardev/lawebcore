import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Command, Search } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface SearchDestination {
  label: string;
  description: string;
  path: string;
  keywords: string[];
  badge?: string;
}

const DESTINATIONS: SearchDestination[] = [
  {
    label: 'Resumen ejecutivo',
    description: 'Estado de campañas, KPIs y pipeline operativo',
    path: '/home',
    keywords: ['home', 'dashboard', 'resumen', 'kpi'],
  },
  {
    label: 'Lens',
    description: 'Descubre y evalúa creadores con datos propios',
    path: '/lens',
    keywords: ['lens', 'ia', 'influencers', 'creadores', 'buscar'],
    badge: 'AI',
  },
  {
    label: 'Nueva búsqueda',
    description: 'Configura filtros y ejecuta un discovery run',
    path: '/lens/search',
    keywords: ['nueva', 'búsqueda', 'search', 'discovery'],
  },
  {
    label: 'Historial de búsquedas',
    description: 'Revisa ejecuciones, candidatos y costos',
    path: '/lens/runs',
    keywords: ['historial', 'runs', 'ejecuciones', 'costo'],
  },
  {
    label: 'Campañas',
    description: 'Gestiona campañas y su pipeline',
    path: '/campaigns',
    keywords: ['campaigns', 'campañas', 'pipeline'],
  },
  {
    label: 'Clientes',
    description: 'Consulta marcas, clientes y contactos',
    path: '/clients',
    keywords: ['clientes', 'marcas', 'accounts'],
  },
];

interface GlobalSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function GlobalSearchDialog({ open, onOpenChange }: GlobalSearchDialogProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        onOpenChange(true);
      }
    };

    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, [onOpenChange]);

  useEffect(() => {
    if (!open) setQuery('');
  }, [open]);

  const destinations = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return DESTINATIONS;

    return DESTINATIONS.filter((destination) =>
      [destination.label, destination.description, ...destination.keywords]
        .join(' ')
        .toLowerCase()
        .includes(normalized),
    );
  }, [query]);

  const handleSelect = (path: string) => {
    onOpenChange(false);
    if (path !== location.pathname) navigate(path);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl gap-0 overflow-hidden p-0">
        <div className="border-b border-divider px-5 pb-4 pt-5">
          <DialogTitle className="flex items-center gap-2 text-sm font-semibold">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Search className="h-4 w-4" aria-hidden="true" />
            </span>
            Buscar en La Web Core
          </DialogTitle>
          <DialogDescription className="mt-1 text-xs text-muted-foreground">
            Navega rápido a una vista o inicia una búsqueda de creadores.
          </DialogDescription>
          <div className="relative mt-4">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar vistas, campañas, Lens…"
              className="h-11 pl-10 pr-16"
              aria-label="Buscar vistas y acciones"
            />
            <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-divider bg-surface-raised px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
              ESC
            </kbd>
          </div>
        </div>

        <div className="max-h-[min(24rem,55vh)] overflow-y-auto p-2" role="listbox" aria-label="Resultados de navegación">
          {destinations.length > 0 ? (
            destinations.map((destination) => (
              <Button
                key={destination.path}
                type="button"
                variant="ghost"
                onClick={() => handleSelect(destination.path)}
                className={cn(
                  'h-auto w-full justify-start gap-3 rounded-md px-3 py-3 text-left hover:bg-surface-raised',
                  destination.path === location.pathname && 'bg-surface-raised',
                )}
                role="option"
                aria-selected={destination.path === location.pathname}
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-divider bg-background text-muted-foreground">
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                    {destination.label}
                    {destination.badge && <Badge variant="outline" className="px-1.5 py-0.5 text-[9px]">{destination.badge}</Badge>}
                  </span>
                  <span className="mt-0.5 block truncate text-xs font-normal text-muted-foreground">{destination.description}</span>
                </span>
              </Button>
            ))
          ) : (
            <div className="px-4 py-10 text-center">
              <Command className="mx-auto h-5 w-5 text-muted-foreground" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-foreground">Sin coincidencias</p>
              <p className="mt-1 text-xs text-muted-foreground">Prueba con otra palabra o abre Lens.</p>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-divider bg-surface-sunken px-5 py-3 text-[10px] text-muted-foreground">
          <span>Atajo global</span>
          <span className="inline-flex items-center gap-1 rounded border border-divider bg-surface-raised px-1.5 py-0.5 font-mono">
            <Command className="h-3 w-3" aria-hidden="true" /> K
          </span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
