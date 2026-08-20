import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Play, Search, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import type { DiscoveryRun, Platform, RunProgress } from '../types/discovery';
import { BulkActionBar } from '../components/BulkActionBar';
import { CandidateList } from '../components/CandidateList';
import { SearchProgress } from '../components/SearchProgress';
import { lensApi } from '../api/lensApi';
import { useDiscoveryRun } from '../hooks/useDiscoveryRun';
import { useSelectionStore } from '@/stores/selectionStore';

const PLATFORMS: Platform[] = ['instagram', 'tiktok', 'youtube', 'x', 'facebook'];

export function LensSearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { run, candidates, isLoading, error, createRun, pollRun, loadRun, cancelPoll, saveCandidate, dismissCandidate } = useDiscoveryRun();
  const [form, setForm] = useState({ product_name: '', industry: '', niches: '', audience_gender: 'all', audience_age_min: 18, audience_age_max: 65, audience_countries: '', platforms: [] as Platform[] });
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const { selectedHandles, clear: clearSelection } = useSelectionStore();
  const selectionMode = run?.status === 'explored';
  const isSelectionEmpty = selectedHandles.length === 0;

  useEffect(() => {
    const runId = searchParams.get('runId');
    if (runId) loadRun(runId).catch(() => toast.error('No se pudo cargar la búsqueda'));
  }, [loadRun, searchParams]);

  const setPlatform = (platform: Platform) => setForm((previous) => ({ ...previous, platforms: previous.platforms.includes(platform) ? previous.platforms.filter((item) => item !== platform) : [...previous.platforms, platform] }));

  const handleSearch = async () => {
    try {
      const brief = {
        product_name: form.product_name || undefined,
        industry: form.industry || undefined,
        niches: form.niches ? form.niches.split(',').map((item) => item.trim()).filter(Boolean) : [],
        audience_gender: form.audience_gender,
        audience_age_min: form.audience_age_min,
        audience_age_max: form.audience_age_max,
        audience_countries: form.audience_countries ? form.audience_countries.split(',').map((item) => item.trim()).filter(Boolean) : [],
        platforms: form.platforms.length > 0 ? form.platforms : undefined,
        discovery_mode: 'explore' as const,
      };
      const newRun = await createRun(brief);
      toast.success('Búsqueda iniciada');
      await pollRun(newRun.id);
      toast.success('Búsqueda completada');
    } catch (searchError) {
      if (searchError instanceof Error && searchError.message === 'SEARCH_CANCELLED') return;
      toast.error('Error al ejecutar la búsqueda');
    }
  };

  const handleAnalyzeSelected = async () => {
    if (!run || isSelectionEmpty) return;
    try {
      setAnalyzeLoading(true);
      const newRun = await lensApi.search.analyzeSelected(run.id, selectedHandles);
      clearSelection();
      toast.success('Análisis iniciado — mirá el progreso en el historial');
      navigate('/lens/runs');
    } catch {
      toast.error('Error al iniciar el análisis');
    } finally {
      setAnalyzeLoading(false);
    }
  };

  const hasResults = run?.status === 'completed' || run?.status === 'partial' || run?.status === 'explored';
  const statusLabel = run?.status === 'running'
    ? 'Discovery en curso'
    : run?.status === 'pending'
      ? 'En cola'
      : run?.status === 'partial'
        ? 'Resultados parciales'
        : run?.status === 'completed'
          ? 'Resultados listos'
          : run?.status === 'explored'
            ? 'Handles descubiertos — seleccioná los que quieras analizar'
            : run?.status === 'failed'
              ? 'La búsqueda falló'
              : run?.status === 'cancelled'
                ? 'Seguimiento detenido'
                : 'Sin ejecución';
  const runProgress = getRunProgress(run);

  return (
    <div className="flex min-h-[calc(100dvh-7rem)] flex-col gap-6">
      <header className="flex shrink-0 flex-col gap-4 border-b border-divider pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/lens')} className="mb-3 -ml-2 gap-1 text-xs text-muted-foreground"><ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />Volver a Lens</Button>
          <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary"><Search className="h-4 w-4" aria-hidden="true" /></span><h1 className="text-2xl font-semibold tracking-tight text-foreground">Nueva búsqueda</h1></div>
          <p className="mt-3 max-w-2xl text-sm text-muted-foreground">Define el contexto mínimo y ejecuta un discovery run trazable.</p>
        </div>
        <Button variant="outline" onClick={() => navigate('/lens/runs')} className="gap-2"><CheckCircle2 className="h-4 w-4" aria-hidden="true" />Ver historial</Button>
      </header>

      <div className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[20rem_minmax(0,1fr)]">
        <Card className="border-divider bg-panel p-5 shadow-none xl:max-h-[calc(100dvh-13rem)] xl:overflow-y-auto">
          <div className="mb-5"><p className="text-eyebrow text-muted-foreground">Brief directo</p><h2 className="mt-1 text-sm font-semibold text-foreground">Parámetros de búsqueda</h2></div>
          <div className="space-y-4">
            <Field label="Producto / marca"><Input value={form.product_name} onChange={(event) => setForm((previous) => ({ ...previous, product_name: event.target.value }))} placeholder="Ej: Protector solar Nivea" /></Field>
            <Field label="Industria"><Input value={form.industry} onChange={(event) => setForm((previous) => ({ ...previous, industry: event.target.value }))} placeholder="Ej: belleza, fitness, travel" /></Field>
            <Field label="Nichos"><Textarea rows={2} value={form.niches} onChange={(event) => setForm((previous) => ({ ...previous, niches: event.target.value }))} placeholder="skincare, makeup, belleza natural" className="min-h-16 resize-none" /><p className="mt-1 text-[10px] text-muted-foreground">Separa varios nichos con coma.</p></Field>
            <Field label="Países y ciudades"><Input value={form.audience_countries} onChange={(event) => setForm((previous) => ({ ...previous, audience_countries: event.target.value }))} placeholder="Venezuela, Caracas, Valencia" /></Field>
            <Field label="Género de audiencia"><Select value={form.audience_gender} onValueChange={(value) => setForm((previous) => ({ ...previous, audience_gender: value }))}><SelectTrigger><SelectValue placeholder="Selecciona un género" /></SelectTrigger><SelectContent><SelectItem value="all">Todos</SelectItem><SelectItem value="female">Femenino</SelectItem><SelectItem value="male">Masculino</SelectItem></SelectContent></Select></Field>
            <div><Label className="flex items-center justify-between text-xs font-medium">Rango de edad <span className="font-mono text-muted-foreground">{form.audience_age_min}–{form.audience_age_max}</span></Label><div className="mt-3 grid gap-3 sm:grid-cols-2"><div><span className="mb-1.5 block text-[10px] text-muted-foreground">Mínima</span><Slider min={13} max={64} value={form.audience_age_min} onChange={(event) => setForm((previous) => ({ ...previous, audience_age_min: Math.min(Number(event.target.value), previous.audience_age_max - 1) }))} aria-label="Edad mínima" /></div><div><span className="mb-1.5 block text-[10px] text-muted-foreground">Máxima</span><Slider min={14} max={65} value={form.audience_age_max} onChange={(event) => setForm((previous) => ({ ...previous, audience_age_max: Math.max(Number(event.target.value), previous.audience_age_min + 1) }))} aria-label="Edad máxima" /></div></div></div>
            <div><Label className="text-xs font-medium">Plataformas</Label><div className="mt-2 flex flex-wrap gap-2">{PLATFORMS.map((platform) => <Button key={platform} type="button" variant={form.platforms.includes(platform) ? 'default' : 'outline'} size="sm" onClick={() => setPlatform(platform)} className="capitalize" aria-pressed={form.platforms.includes(platform)}>{platform}</Button>)}</div></div>
            <Button onClick={handleSearch} disabled={isLoading} className="mt-2 w-full gap-2">{isLoading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}{isLoading ? 'Ejecutando discovery…' : 'Ejecutar búsqueda'}</Button>
          </div>
        </Card>

        <section className="min-w-0 space-y-5" aria-live="polite" aria-busy={isLoading}>
          <div className="rounded-lg border border-divider bg-panel p-5">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-eyebrow text-muted-foreground">Estado de ejecución</p><h2 className="mt-1 text-lg font-semibold text-foreground">{statusLabel}</h2></div>{run && <Badge variant="outline" className="font-mono text-[10px]">{run.id.slice(0, 8)}</Badge>}</div>
            {!run && <div className="mt-8 flex flex-col items-center justify-center border-t border-divider pt-8 text-center"><Sparkles className="h-5 w-5 text-primary" aria-hidden="true" /><p className="mt-3 text-sm font-medium text-foreground">Configura una búsqueda</p><p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">Los resultados, el progreso y el costo aparecerán aquí sin perder el contexto del brief.</p></div>}
            {run && !hasResults && run.status !== 'cancelled' && <div className="mt-5"><SearchProgress progress={runProgress} /><Button type="button" variant="ghost" size="sm" onClick={cancelPoll} className="mt-2 text-xs text-muted-foreground">Detener seguimiento</Button></div>}
            {run?.status === 'cancelled' && <div className="mt-5 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">Se detuvo el seguimiento en esta vista. El run puede continuar en segundo plano; vuelve a cargarlo desde el historial.</div>}
            {error && <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">{error}</p>}
            {run?.error && <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">{run.error}</p>}
          </div>

          {run && hasResults && <Card className="border-divider bg-panel p-5 shadow-none"><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><p className="text-eyebrow text-muted-foreground">Salida del run</p><h2 className="mt-1 text-lg font-semibold text-foreground">{run.total_candidates} candidatos encontrados</h2></div>{run.actual_cost_usd != null && <Badge variant="outline" className="border-success/30 bg-success/10 font-mono text-success">${run.actual_cost_usd.toFixed(4)} gastado</Badge>}</div><CandidateList candidates={candidates} onSave={saveCandidate} onDismiss={dismissCandidate} isLoading={isLoading} runId={run.id} selectionMode={selectionMode} /></Card>}
        </section>
        {selectionMode && <BulkActionBar count={selectedHandles.length} onAnalyze={handleAnalyzeSelected} onClear={clearSelection} isLoading={analyzeLoading} isDisabled={isSelectionEmpty} />}
      </div>
    </div>
  );
}

function getRunProgress(run: DiscoveryRun | null): RunProgress {
  const metadata = run?.metadata ?? {};
  return {
    current_step: typeof metadata.current_step === 'string' ? metadata.current_step : run?.status === 'pending' ? 'parsing_brief' : run?.status === 'failed' ? 'failed' : run?.status === 'cancelled' ? 'cancelled' : 'building_queries',
    completed_steps: Array.isArray(metadata.completed_steps) ? metadata.completed_steps.filter((step): step is string => typeof step === 'string') : [],
    current_hashtag: typeof metadata.current_hashtag === 'string' ? metadata.current_hashtag : undefined,
    candidates_found: typeof metadata.candidates_found === 'number' ? metadata.candidates_found : run?.total_candidates ?? 0,
    platforms: Array.isArray(metadata.platforms) ? metadata.platforms.filter((platform): platform is string => typeof platform === 'string') : undefined,
    total_queries: typeof metadata.total_queries === 'number' ? metadata.total_queries : undefined,
  };
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <div><Label className="mb-1.5 block text-xs font-medium">{label}</Label>{children}</div>;
}
