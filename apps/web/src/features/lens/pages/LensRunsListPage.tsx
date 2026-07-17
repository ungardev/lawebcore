import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { DiscoveryRun, DiscoveryRunStatus } from '../types/discovery';

const STATUS_CONFIG: Record<DiscoveryRunStatus, { label: string; icon: React.ReactNode; className: string }> = {
  pending: { label: 'Pendiente', icon: <Clock className="w-4 h-4" />, className: 'bg-yellow-500/10 text-yellow-600' },
  running: { label: 'En curso', icon: <Loader2 className="w-4 h-4 animate-spin" />, className: 'bg-blue-500/10 text-blue-600' },
  completed: { label: 'Completado', icon: <CheckCircle className="w-4 h-4" />, className: 'bg-emerald-500/10 text-emerald-600' },
  failed: { label: 'Fallido', icon: <XCircle className="w-4 h-4" />, className: 'bg-red-500/10 text-red-600' },
  cancelled: { label: 'Cancelado', icon: <XCircle className="w-4 h-4" />, className: 'bg-muted text-muted-foreground' },
};

export function LensRunsListPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const limit = 20;

  const fetchRuns = async (pageNum: number) => {
    setIsLoading(true);
    try {
      const { data } = await import('@/lib/api').then((m) => m.api.get('/lens/discovery/runs', { params: { limit, offset: (pageNum - 1) * limit } }));
      if (pageNum === 1) setRuns(data);
      else setRuns((prev) => [...prev, ...data]);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchRuns(1); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 text-primary" />
            Historial de búsquedas
          </h1>
          <p className="text-sm text-muted-foreground">
            Todas las ejecuciones de Influencer Lens
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate('/influencer-lens/search')}>
          Nueva búsqueda
        </Button>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Fecha</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Brief</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Estado</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Candidatos</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Guardados</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Costo</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const cfg = STATUS_CONFIG[run.status];
                return (
                  <tr
                    key={run.id}
                    className="border-b hover:bg-muted/30 cursor-pointer transition-colors"
                    onClick={() => navigate(`/influencer-lens/search?run=${run.id}`)}
                  >
                    <td className="px-4 py-3 text-muted-foreground">
                      {run.created_at ? new Date(run.created_at).toLocaleDateString('es-ES', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      }) : '—'}
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <p className="truncate">{run.brief_text}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium', cfg.className)}>
                        {cfg.icon}
                        {cfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">{run.total_candidates}</td>
                    <td className="px-4 py-3 text-right">{run.accepted}</td>
                    <td className="px-4 py-3 text-right font-mono text-xs">
                      {run.actual_cost_usd != null ? `$${run.actual_cost_usd.toFixed(4)}` : run.estimated_cost_usd ? `~$${run.estimated_cost_usd.toFixed(4)}` : '—'}
                    </td>
                  </tr>
                );
              })}
              {runs.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-muted-foreground">
                    Sin búsquedas ejecutadas aún
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {runs.length > 0 && (
          <div className="p-4 border-t flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => { const next = page + 1; setPage(next); fetchRuns(next); }}
              disabled={isLoading}
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Cargar más'}
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
