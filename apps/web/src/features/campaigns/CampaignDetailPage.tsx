import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { useState } from 'react';
import { ArrowLeft, ExternalLink, Sparkles, Loader2 } from 'lucide-react';
import { campaignsApi, aiApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { STATUS_COLORS, OBJECTIVE_COLORS, formatCurrency, formatNumber, formatPercent, CAMPAIGN_STATUSES } from '@/lib/utils';
import { toast } from 'sonner';

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [aiOutput, setAiOutput] = useState<string | null>(null);

  const { data: campaign, isLoading } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => campaignsApi.get(id!),
    enabled: !!id,
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
      aiApi.generate({ prompt_code: promptCode, campaign_id: id! }),
    onSuccess: (data) => setAiOutput(data.generated_content),
    onError: () => toast.error('Error al generar con IA'),
  });

  if (isLoading) return <div className="text-muted-foreground">Cargando...</div>;
  if (!campaign) return <div>No encontrada</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Link to="/campaigns" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center mb-2">
            <ArrowLeft className="w-4 h-4 mr-1" /> Campanas
          </Link>
          <h1 className="text-2xl md:text-3xl font-bold">{campaign.name}</h1>
          <p className="text-muted-foreground font-mono text-sm">{campaign.code}</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
          <Button variant="outline" onClick={() => generate.mutate('brief_generator_v1')} disabled={generate.isPending} className="w-full sm:w-auto">
            {generate.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
            Generar Brief
          </Button>
          <Button onClick={() => generate.mutate('post_mortem_v1')} disabled={generate.isPending} className="w-full sm:w-auto">
            {generate.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
            Post-Mortem IA
          </Button>
        </div>
      </div>

      {aiOutput && (
        <Card className="border-purple-200 bg-purple-50/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-600" /> Resultado IA
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap text-sm font-sans">{aiOutput}</pre>
            <Button size="sm" variant="ghost" className="mt-3" onClick={() => setAiOutput(null)}>Cerrar</Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Informacion general</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Cliente</p>
                <p className="font-medium">{campaign.client?.name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Marca</p>
                <p className="font-medium">{campaign.brand?.name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Objetivo</p>
                <Badge variant="outline" className={OBJECTIVE_COLORS[campaign.objective]}>{campaign.objective}</Badge>
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
                      campaign.status === s ? STATUS_COLORS[s] + ' ring-2 ring-primary' : 'bg-card hover:bg-accent'
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
          <CardHeader><CardTitle>KPI Values</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {campaign.kpis?.length === 0 && <p className="text-sm text-muted-foreground">Sin KPIs cargados</p>}
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

        {campaign.links && campaign.links.length > 0 && (
          <Card className="lg:col-span-3">
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
                    <ExternalLink className="w-4 h-4 text-muted-foreground" />
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {campaign.insights && campaign.insights.length > 0 && (
          <Card className="lg:col-span-3">
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
    </div>
  );
}
