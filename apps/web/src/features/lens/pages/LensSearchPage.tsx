import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Play } from 'lucide-react';
import { useDiscoveryRun } from '../hooks/useDiscoveryRun';
import { CandidateList } from '../components/CandidateList';
import { MatchScoreCircle } from '../components/MatchScoreCircle';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import type { Platform } from '../types/discovery';

const PLATFORMS: Platform[] = ['instagram', 'tiktok', 'youtube', 'x', 'facebook'];

export function LensSearchPage() {
  const navigate = useNavigate();
  const { run, candidates, isLoading, error, createRun, pollRun, saveCandidate, dismissCandidate } = useDiscoveryRun();

  const [form, setForm] = useState({
    product_name: '',
    industry: '',
    niches: '',
    audience_gender: 'all',
    audience_age_min: 18,
    audience_age_max: 45,
    audience_countries: '',
    budget_usd: '',
    platforms: [] as Platform[],
  });

  const setPlatform = (p: Platform) => {
    setForm((f) => ({
      ...f,
      platforms: f.platforms.includes(p)
        ? f.platforms.filter((x) => x !== p)
        : [...f.platforms, p],
    }));
  };

  const handleSearch = async () => {
    try {
      const brief = {
        product_name: form.product_name || undefined,
        industry: form.industry || undefined,
        niches: form.niches ? form.niches.split(',').map((s) => s.trim()) : [],
        audience_gender: form.audience_gender,
        audience_age_min: form.audience_age_min,
        audience_age_max: form.audience_age_max,
        audience_countries: form.audience_countries ? form.audience_countries.split(',').map((s) => s.trim()) : [],
        budget_usd: form.budget_usd ? parseFloat(form.budget_usd) : undefined,
        platforms: form.platforms.length > 0 ? form.platforms : undefined,
      };

      const newRun = await createRun(brief);
      toast.success('Búsqueda iniciada');
      await pollRun(newRun.id);
      toast.success('Búsqueda completada');
    } catch {
      toast.error('Error al ejecutar la búsqueda');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="w-6 text-primary" />
          Búsqueda Directa
        </h1>
        <p className="text-sm text-muted-foreground">
          Define los parámetros y ejecuta una búsqueda de influencers
        </p>
      </div>

      <Card className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Producto / Marca</Label>
            <Input
              value={form.product_name}
              onChange={(e) => setForm((f) => ({ ...f, product_name: e.target.value }))}
              placeholder="Ej: Protector solar Nivea"
            />
          </div>
          <div>
            <Label>Industria</Label>
            <Input
              value={form.industry}
              onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
              placeholder="Ej: Beauty, Fitness, Travel"
            />
          </div>
          <div>
            <Label> Nichos (separados por coma)</Label>
            <Input
              value={form.niches}
              onChange={(e) => setForm((f) => ({ ...f, niches: e.target.value }))}
              placeholder="Ej: skincare, makeup, belleza natural"
            />
          </div>
          <div>
            <Label>Países (separados por coma)</Label>
            <Input
              value={form.audience_countries}
              onChange={(e) => setForm((f) => ({ ...f, audience_countries: e.target.value }))}
              placeholder="Ej: Colombia, México, España"
            />
          </div>
          <div>
            <Label>Presupuesto USD</Label>
            <Input
              type="number"
              value={form.budget_usd}
              onChange={(e) => setForm((f) => ({ ...f, budget_usd: e.target.value }))}
              placeholder="Ej: 5000"
            />
          </div>
          <div>
            <Label>Género audiencia</Label>
            <select
              value={form.audience_gender}
              onChange={(e) => setForm((f) => ({ ...f, audience_gender: e.target.value }))}
              className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="all">Todos</option>
              <option value="female">Femenino</option>
              <option value="male">Masculino</option>
            </select>
          </div>
          <div>
            <Label>Edad mínima: {form.audience_age_min}</Label>
            <input
              type="range"
              min={13}
              max={65}
              value={form.audience_age_min}
              onChange={(e) => setForm((f) => ({ ...f, audience_age_min: parseInt(e.target.value) }))}
              className="w-full"
            />
          </div>
          <div>
            <Label>Edad máxima: {form.audience_age_max}</Label>
            <input
              type="range"
              min={13}
              max={65}
              value={form.audience_age_max}
              onChange={(e) => setForm((f) => ({ ...f, audience_age_max: parseInt(e.target.value) }))}
              className="w-full"
            />
          </div>
        </div>

        <div className="mt-4">
          <Label>Plataformas</Label>
          <div className="flex flex-wrap gap-2 mt-2">
            {PLATFORMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPlatform(p)}
                className={`px-3 py-1.5 rounded-md text-xs border transition-colors ${
                  form.platforms.includes(p)
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'border-border hover:bg-muted'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <Button onClick={handleSearch} disabled={isLoading} className="mt-6 gap-2 w-full md:w-auto">
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {isLoading ? 'Buscando...' : 'Ejecutar búsqueda'}
        </Button>
      </Card>

      {error && (
        <p className="text-sm text-red-400">Error: {error}</p>
      )}

      {run && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Resultados</h2>
              <p className="text-sm text-muted-foreground">
                {run.status === 'completed'
                  ? `${run.total_candidates} candidatos encontrados`
                  : run.status === 'running'
                  ? 'Búsqueda en progreso...'
                  : `Estado: ${run.status}`}
              </p>
            </div>
            {run.actual_cost_usd != null && (
              <span className="text-xs font-mono bg-emerald-500/10 text-emerald-600 px-2 py-1 rounded">
                ${run.actual_cost_usd.toFixed(4)} gastado
              </span>
            )}
          </div>

          {run.status === 'completed' && (
            <CandidateList
              candidates={candidates}
              onSave={saveCandidate}
              onDismiss={dismissCandidate}
              isLoading={isLoading}
              runId={run.id}
            />
          )}
        </Card>
      )}
    </div>
  );
}
