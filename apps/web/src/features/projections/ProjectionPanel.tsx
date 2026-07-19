import { useState } from 'react';
import { Calculator, Info, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { TierSliders } from './TierSliders';
import { ScenarioComparison } from './ScenarioComparison';
import { projectionsApi } from '@/lib/api';
import { ProjectionCalculateResponse } from '@/types/piar';
import { toast } from 'sonner';

interface ProjectionPanelProps {
  brandId: string;
  brandName?: string;
  onClose?: () => void;
}

const DEFAULT_POSTS: Record<string, number> = {
  NANO: 20,
  MICRO: 5,
  MID: 2,
  MACRO: 1,
  MEGA: 0,
};

export function ProjectionPanel({ brandId, brandName, onClose: _onClose }: ProjectionPanelProps) {
  const [postsPerTier, setPostsPerTier] = useState<Record<string, number>>(DEFAULT_POSTS);
  const [result, setResult] = useState<ProjectionCalculateResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTierChange = (tier: string, value: number) => {
    setPostsPerTier((prev) => ({ ...prev, [tier]: value }));
  };

  const totalPosts = Object.values(postsPerTier).reduce((sum, v) => sum + v, 0);

  const handleCalculate = async () => {
    if (totalPosts === 0) {
      toast.warning('Define al menos un post para calcular');
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const data = await projectionsApi.calculate(brandId, postsPerTier);
      setResult(data);
    } catch (_err) {
      toast.error('Error calculando proyección');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-primary" />
            Proyección P.I.A.R
          </CardTitle>
          {brandName && (
            <p className="text-sm text-muted-foreground">Marca: {brandName}</p>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="bg-muted/50 rounded-lg p-3 border border-border">
            <div className="flex items-start gap-2 text-xs text-muted-foreground">
              <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
              <p>
                Ingresá el número de posts planeados por tier. El motor P.I.A.R usa
                el histórico de campañas de esta marca (o del sector si tiene menos de 3 campañas)
                para proyectar vistas, alcance y engagement en 3 escenarios.
              </p>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold mb-3">Posts planeados por tier</h4>
            <TierSliders postsPerTier={postsPerTier} onChange={handleTierChange} />
            <div className="flex justify-between items-center mt-3 pt-3 border-t">
              <span className="text-sm font-medium">Total posts</span>
              <span className="text-lg font-bold">{totalPosts}</span>
            </div>
          </div>

          <Button
            onClick={handleCalculate}
            disabled={loading || totalPosts === 0}
            className="w-full"
          >
            {loading ? 'Calculando...' : 'Calcular proyección'}
          </Button>

          {result && (
            <>
              {result.industry && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Info className="w-3 h-3 text-purple-600" />
                    <span className="text-xs font-semibold text-purple-700">Fuente de datos</span>
                  </div>
                  {result.resultados_por_tier[0]?.fuente === 'marca' ? (
                    <p className="text-xs text-purple-700">
                      Histórico propio de la marca ({result.resultados_por_tier[0]?.num_campanas} campañas)
                    </p>
                  ) : (
                    <p className="text-xs text-purple-700">
                      Fallback al sector: <span className="font-semibold">{result.industry}</span> (marca sin suficiente histórico propio)
                    </p>
                  )}
                </div>
              )}

              {result.calidad_creadores && (
                <div className={`rounded-lg p-3 border ${
                  result.calidad_creadores.decision_dominante === 'ESCALAR' ? 'bg-emerald-50 border-emerald-200' :
                  result.calidad_creadores.decision_dominante === 'DESCARTAR' ? 'bg-red-50 border-red-200' :
                  result.calidad_creadores.decision_dominante === 'DATOS_INSUFICIENTES' ? 'bg-slate-50 border-slate-200' :
                  'bg-amber-50 border-amber-200'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-3 h-3" />
                    <span className="text-xs font-semibold">Calidad de creadores</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                      result.calidad_creadores.ajuste_aplicado === 'optimista_ajustado' ? 'bg-emerald-100 text-emerald-700' :
                      result.calidad_creadores.ajuste_aplicado === 'conservador_ajustado' ? 'bg-red-100 text-red-700' :
                      'bg-amber-100 text-amber-700'
                    }`}>
                      {result.calidad_creadores.ajuste_aplicado.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div>
                      <span className="text-xs text-muted-foreground">Decisión dominante: </span>
                      <span className={`text-xs font-semibold ${
                        result.calidad_creadores.decision_dominante === 'ESCALAR' ? 'text-emerald-700' :
                        result.calidad_creadores.decision_dominante === 'DESCARTAR' ? 'text-red-700' :
                        result.calidad_creadores.decision_dominante === 'DATOS_INSUFICIENTES' ? 'text-slate-600' :
                        'text-amber-700'
                      }`}>{result.calidad_creadores.decision_dominante}</span>
                    </div>
                    {result.calidad_creadores.score_promedio != null && (
                      <div>
                        <span className="text-xs text-muted-foreground">Score promedio: </span>
                        <span className="text-xs font-semibold">{result.calidad_creadores.score_promedio.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-sm font-semibold mb-3">Proyección por escenario</h4>
                <ScenarioComparison total={result.total} />
              </div>

              {result.resultados_por_tier.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold mb-2">Desglose por tier</h4>
                  <div className="space-y-2">
                    {result.resultados_por_tier.map((r) => (
                      <div key={r.tier} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-bold">{r.tier}</span>
                          <div className="flex items-center gap-2">
                            {r.fuente === 'marca' ? (
                              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">
                                Marca
                              </span>
                            ) : (
                              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                                Sector
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {r.num_campanas} campan{r.num_campanas === 1 ? 'a' : 'as'}
                            </span>
                          </div>
                        </div>
                        {r.tasas.er_promedio != null && (
                          <p className="text-xs text-muted-foreground">
                            ER promedio: <span className="font-medium">{(r.tasas.er_promedio * 100).toFixed(2)}%</span>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
