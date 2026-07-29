import { useEffect, useState } from 'react';
import { CheckCircle, Clock, History, Loader2, XCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { discoveryRunsApi } from '@/lib/api';
import type { DiscoveryRun, DiscoveryRunStatus } from '../types/discovery';

const STATUS_CONFIG: Record<DiscoveryRunStatus, { label: string; icon: React.ReactNode; className: string }> = {
  pending: { label: 'Pendiente', icon: <Clock className="h-3.5 w-3.5" aria-hidden="true" />, className: 'border-warning/30 bg-warning/10 text-warning' },
  running: { label: 'En curso', icon: <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />, className: 'border-info/30 bg-info/10 text-info' },
  completed: { label: 'Completado', icon: <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />, className: 'border-success/30 bg-success/10 text-success' },
  failed: { label: 'Fallido', icon: <XCircle className="h-3.5 w-3.5" aria-hidden="true" />, className: 'border-destructive/30 bg-destructive/10 text-destructive' },
  cancelled: { label: 'Cancelado', icon: <XCircle className="h-3.5 w-3.5" aria-hidden="true" />, className: 'border-divider bg-surface-raised text-muted-foreground' },
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
      const data = await discoveryRunsApi.list({ limit, offset: (pageNum - 1) * limit });
      if (pageNum === 1) setRuns(Array.isArray(data) ? data : []);
      else setRuns((previous) => [...previous, ...(Array.isArray(data) ? data : [])]);
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void fetchRuns(1); }, []);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 border-b border-divider pb-5 md:flex-row md:items-end md:justify-between">
        <div className="flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary"><History className="h-4 w-4" aria-hidden="true" /></span><div><p className="text-eyebrow text-muted-foreground">Influencer Lens / operaciones</p><h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">Historial de búsquedas</h1><p className="mt-2 text-sm text-muted-foreground">Ejecuciones, resultados y costos de discovery.</p></div></div>
        <Button onClick={() => navigate('/influencer-lens/search')} className="w-full md:w-auto">Nueva búsqueda</Button>
      </header>

      <Card className="overflow-hidden border-divider bg-panel shadow-none">
        <Table>
          <TableHeader><TableRow className="bg-surface-sunken hover:bg-surface-sunken"><TableHead>Fecha</TableHead><TableHead>Brief</TableHead><TableHead>Estado</TableHead><TableHead className="text-right">Candidatos</TableHead><TableHead className="text-right">Guardados</TableHead><TableHead className="text-right">Costo</TableHead></TableRow></TableHeader>
          <TableBody>
            {runs.map((run) => {
              const config = STATUS_CONFIG[run.status];
              return <TableRow key={run.id} className="cursor-pointer" onClick={() => navigate(`/influencer-lens/search?runId=${run.id}`)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); navigate(`/influencer-lens/search?runId=${run.id}`); } }}><TableCell className="whitespace-nowrap text-xs text-muted-foreground">{run.created_at ? new Date(run.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'}</TableCell><TableCell className="max-w-xs"><span className="block truncate text-sm text-foreground">{run.brief_text || 'Nueva búsqueda'}</span><span className="mt-1 block font-mono text-[10px] text-muted-foreground">RUN-{run.id.slice(0, 8)}</span></TableCell><TableCell><Badge variant="outline" className={cn('gap-1.5', config.className)}>{config.icon}{config.label}</Badge></TableCell><TableCell className="text-right font-mono text-sm tabular-nums text-foreground">{run.total_candidates}</TableCell><TableCell className="text-right font-mono text-sm tabular-nums text-foreground">{run.accepted}</TableCell><TableCell className="text-right font-mono text-xs text-muted-foreground">{run.actual_cost_usd != null ? `$${run.actual_cost_usd.toFixed(4)}` : run.estimated_cost_usd ? `~$${run.estimated_cost_usd.toFixed(4)}` : '—'}</TableCell></TableRow>;
            })}
            {runs.length === 0 && !isLoading && <TableRow><TableCell colSpan={6} className="h-48 text-center text-sm text-muted-foreground">Sin búsquedas ejecutadas aún.</TableCell></TableRow>}
            {isLoading && <TableRow><TableCell colSpan={6} className="h-24 text-center"><Loader2 className="mx-auto h-4 w-4 animate-spin text-primary" aria-label="Cargando búsquedas" /></TableCell></TableRow>}
          </TableBody>
        </Table>
        {runs.length > 0 && <div className="flex justify-center border-t border-divider p-4"><Button variant="outline" size="sm" onClick={() => { const next = page + 1; setPage(next); void fetchRuns(next); }} disabled={isLoading}>{isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : 'Cargar más'}</Button></div>}
      </Card>
    </div>
  );
}
