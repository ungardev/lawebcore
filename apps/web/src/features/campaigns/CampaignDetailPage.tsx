import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { useState } from 'react';
import { ArrowLeft, ExternalLink, Sparkles, Loader2, TrendingUp, BarChart3, MessageCircle, Upload } from 'lucide-react';
import { campaignsApi, publicacionesApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { STATUS_COLORS, OBJECTIVE_COLORS, formatCurrency, formatNumber, formatPercent, CAMPAIGN_STATUSES } from '@/lib/utils';
import { KPITrendChart } from './components/KPITrendChart';
import { SentimentBreakdown } from './components/SentimentBreakdown';
import { PublicacionesList } from './components/PublicacionesList';
import { CSVImportButton } from '@/features/imports/CSVImportButton';
import { JSONImportPanel } from '@/features/imports/JSONImportPanel';
import { ManualPublicationForm } from '@/features/imports/ManualPublicationForm';
import { toast } from 'sonner';

type TabKey = 'overview' | 'publicaciones' | 'importar' | 'proyeccion';

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [aiOutput, setAiOutput] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => campaignsApi.get(id!),
    enabled: !!id,
  });

  const { data: pubStats } = useQuery({
    queryKey: ['publicaciones-stats', id],
    queryFn: () => publicacionesApi.stats(id!),
    enabled: !!id && activeTab === 'publicaciones',
    refetchInterval: 60_000,
  });

  const changeStatus = useMutation({
    mutationFn: (to_status: string) => campaignsApi.changeStatus(id!, to_status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', id] });
      toast.success('Status actualizado');
    },
  });

  const generate = useMutation({
    mutationFn: (promptCode: string) =>
      campaignsApi.create ? campaignsApi.create({} as any) : Promise.resolve(null),
    onError: () => toast.error('Error al generar con IA'),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Campaña no encontrada</p>
        <Link to="/campaigns" className="text-primary hover:underline mt-2 inline-block">
          Volver a campañas
        </Link>
      </div>
    );
  }

  const timeline = (pubStats as any)?.timeline || [];

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Link to="/campaigns" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center mb-2">
            <ArrowLeft className="w-4 h-4 mr-1" /> Campañas
          </Link>
          <h1 className="text-2xl md:text-3xl font-bold">{campaign.name}</h1>
          <p className="text-muted-foreground font-mono text-sm">{campaign.code}</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
          <Button
            variant="outline"
            onClick={() => {}}
            disabled
            className="w-full sm:w-auto"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Generar Brief
          </Button>
          <Button
            onClick={() => {}}
            disabled
            className="w-full sm:w-auto"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Post-Mortem IA
          </Button>
        </div>
      </div>

      {aiOutput && (
        <Card className="border-purple-200 bg-purple-50/50 dark:bg-purple-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-600" /> Resultado IA
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap text-sm font-sans">{aiOutput}</pre>
            <Button size="sm" variant="ghost" className="mt-3" onClick={() => setAiOutput(null)}>
              Cerrar
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-1 border-b overflow-x-auto">
        {([
          ['overview', 'Información', BarChart3],
          ['publicaciones', 'Publicaciones', MessageCircle],
          ['importar', 'Importar', Upload],
        ] as const).map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as TabKey)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === key
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
            {key === 'publicaciones' && pubStats && (
              <Badge variant="secondary" className="ml-1 text-xs">
                {(pubStats as any)?.total ?? 0}
              </Badge>
            )}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="space-y-4 md:space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>Información general</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Cliente</p>
                    <p className="font-medium">{campaign.client?.name || '—'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Marca</p>
                    <p className="font-medium">{campaign.brand?.name || '—'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Objetivo</p>
                    <Badge variant="outline" className={OBJECTIVE_COLORS[campaign.objective]}>
                      {campaign.objective}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Influencers</p>
                    <p className="font-medium">{campaign.num_influencers}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Presupuesto</p>
                    <p className="font-medium">{formatCurrency(campaign.budget_total, campaign.budget_currency)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Fechas</p>
                    <p className="font-medium">
                      {campaign.start_date || '—'} → {campaign.end_date || '—'}
                    </p>
                  </div>
                </div>

                <div>
                  <p className="text-muted-foreground text-sm mb-2">Cambiar status</p>
                  <div className="flex flex-wrap gap-2">
                    {CAMPAIGN_STATUSES.map((s) => (
                      <button
                        key={s}
                        onClick={() => changeStatus.mutate(s)}
                        className={`px-3 py-1 rounded-md text-xs border transition-all ${
                          campaign.status === s
                            ? STATUS_COLORS[s] + ' ring-2 ring-primary'
                            : 'bg-card hover:bg-accent'
                        }`}
                      >
                        {s.replace(/_/g, ' ')}
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="w-4 h-4" /> KPIs</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {campaign.kpis?.length === 0 && (
                  <p className="text-sm text-muted-foreground">Sin KPIs cargados</p>
                )}
                {campaign.kpis?.map((k) => (
                  <div key={k.kpi_code} className="flex items-center justify-between border-b pb-2 last:border-0">
                    <div>
                      <p className="text-xs text-muted-foreground">{k.kpi_name}</p>
                      <p className="text-xs text-muted-foreground">{k.category}</p>
                    </div>
                    <p className="font-bold">
                      {k.category === 'ENGAGEMENT' || k.kpi_code.includes('rate') || k.kpi_code.includes('retention')
                        ? formatPercent(Number(k.value))
                        : formatNumber(Number(k.value))}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {pubStats && timeline.length > 0 && (
            <KPITrendChart
              data={timeline}
              title="Evolución de métricas de publicaciones"
            />
          )}

          {pubStats && (pubStats as any)?.sentimiento_total && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <SentimentBreakdown data={(pubStats as any).sentimiento_total} />
              <Card>
                <CardHeader><CardTitle>Resumen de métricas</CardTitle></CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total publicaciones</span>
                    <span className="font-medium">{(pubStats as any).total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Vistas totales</span>
                    <span className="font-medium">{formatNumber((pubStats as any).sum_vistas)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Alcance total</span>
                    <span className="font-medium">{formatNumber((pubStats as any).sum_alcance)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Likes totales</span>
                    <span className="font-medium">{formatNumber((pubStats as any).sum_likes)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ER promedio</span>
                    <span className="font-medium">
                      {(pubStats as any).avg_er != null
                        ? formatPercent((pubStats as any).avg_er * 100)
                        : '—'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {campaign.links && campaign.links.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Links y documentos</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {campaign.links.map((l) => (
                    <a
                      key={l.id}
                      href={l.url.startsWith('http') ? l.url : '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent transition-colors text-sm"
                    >
                      <div>
                        <Badge variant="outline" className="text-xs mb-1">{l.link_type}</Badge>
                        <p className="font-medium">{l.title}</p>
                      </div>
                      <ExternalLink className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                    </a>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {campaign.insights && campaign.insights.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Insights</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {campaign.insights.map((i) => (
                  <div key={i.id} className="border-l-4 border-purple-400 pl-3 py-2">
                    <p className="font-medium text-sm flex items-center gap-2">
                      {i.title}
                      {i.generated_by_ai && <Badge variant="outline" className="text-xs">IA</Badge>}
                      {i.is_winning_format && <Badge className="text-xs">Formato ganador</Badge>}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">{i.description}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === 'publicaciones' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <KPITrendChart data={timeline} title="Evolución por publicación" />
            <SentimentBreakdown data={(pubStats as any)?.sentimiento_total || { positivo: 0, neutro: 0, negativo: 0 }} />
          </div>
          <PublicacionesList campaignId={id!} />
        </div>
      )}

      {activeTab === 'importar' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-4 h-4" />
                  Importar CSV / Excel
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Sube un archivo CSV o Excel con las métricas de las publicaciones de{' '}
                  <strong>{campaign.name}</strong>. El sistema detectará automáticamente las columnas
                  en español (Google Form) o inglés (Metricool).
                </p>
                <CSVImportButton
                  campaignId={id!}
                  campaignName={campaign.name}
                  onSuccess={() => {
                    qc.invalidateQueries({ queryKey: ['publicaciones-stats', id] });
                    qc.invalidateQueries({ queryKey: ['publicaciones', id] });
                  }}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                    <path d="M10 12l2 2 4-4"/>
                  </svg>
                  Importar JSON (Data Contract)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Pega el JSON array siguiendo el formato del Data Contract P.I.A.R.{' '}
                  <a
                    href="/13_data_contract_hub.md"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    Ver especificación →
                  </a>
                </p>
                <JSONImportPanel
                  onSuccess={() => {
                    qc.invalidateQueries({ queryKey: ['publicaciones-stats', id] });
                    qc.invalidateQueries({ queryKey: ['publicaciones', id] });
                  }}
                />
              </CardContent>
            </Card>
          </div>

          <ManualPublicationForm
            campaignId={id!}
            campaignName={campaign.name}
            onSuccess={() => {
              qc.invalidateQueries({ queryKey: ['publicaciones-stats', id] });
              qc.invalidateQueries({ queryKey: ['publicaciones', id] });
            }}
          />

          <Card>
            <CardHeader>
              <CardTitle>Fuentes de datos soportadas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div className="border rounded-lg p-3">
                  <p className="font-medium mb-1">Google Form (español)</p>
                  <p className="text-muted-foreground text-xs">Exportar CSV desde el formulario. Mapeo automático.</p>
                </div>
                <div className="border rounded-lg p-3">
                  <p className="font-medium mb-1">Metricool (inglés)</p>
                  <p className="text-muted-foreground text-xs">Exportar CSV desde Metricool. Mapeo automático.</p>
                </div>
                <div className="border rounded-lg p-3">
                  <p className="font-medium mb-1">HypeAuditor Reports</p>
                  <p className="text-muted-foreground text-xs">Copiar datos de los reportes públicos. JSON o CSV.</p>
                </div>
                <div className="border rounded-lg p-3">
                  <p className="font-medium mb-1">Meta Graph API</p>
                  <p className="text-muted-foreground text-xs">Integración directa via API (futuro).</p>
                </div>
                <div className="border rounded-lg p-3">
                  <p className="font-medium mb-1">TikTok Display API</p>
                  <p className="text-muted-foreground text-xs">Integración directa via API (futuro).</p>
                </div>
                <div className="border rounded-lg p-3">
                  <p className="font-medium mb-1">Manual / JSON</p>
                  <p className="text-muted-foreground text-xs">Entrada manual via formulario o JSON Data Contract.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'proyeccion' && (
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground">
              El motor de proyección P.I.A.R se accede desde la creación de una nueva campaña.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
