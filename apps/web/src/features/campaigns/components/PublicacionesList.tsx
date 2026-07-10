import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { publicacionesApi, sentimentApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Publicacion } from '@/types/piar';
import { toast } from 'sonner';
import { MessageCircle, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

interface PublicacionesListProps {
  campaignId: string;
  onInfluencerClick?: (influencerId: string) => void;
}

const FORMAT_COLORS: Record<string, string> = {
  reel: 'bg-purple-100 text-purple-700',
  story: 'bg-blue-100 text-blue-700',
  post: 'bg-slate-100 text-slate-700',
  video: 'bg-rose-100 text-rose-700',
};

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function formatDate(fecha: string | null): string {
  if (!fecha) return '—';
  try {
    return new Date(fecha).toLocaleDateString('es-VE', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return '—';
  }
}

function SentimentBadge({ pub }: { pub: Publicacion }) {
  const hasSentiment = (pub.sentimiento_positivo ?? 0) > 0
    || (pub.sentimiento_neutro ?? 0) > 0
    || (pub.sentimiento_negativo ?? 0) > 0;

  const queryClient = useQueryClient();

  const analyzeMutation = useMutation({
    mutationFn: () => sentimentApi.analyze(pub.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['publicaciones'] });
      toast.success('Comentarios analizados');
    },
    onError: () => {
      toast.error('Error analizando comentarios');
    },
  });

  if (!hasSentiment) {
    return (
      <Button
        size="sm"
        variant="outline"
        onClick={() => analyzeMutation.mutate()}
        disabled={analyzeMutation.isPending}
        className="text-xs h-7 gap-1"
      >
        {analyzeMutation.isPending ? (
          <RefreshCw className="w-3 h-3 animate-spin" />
        ) : (
          <MessageCircle className="w-3 h-3" />
        )}
        Analizar
      </Button>
    );
  }

  const total = (pub.sentimiento_positivo ?? 0)
    + (pub.sentimiento_neutro ?? 0)
    + (pub.sentimiento_negativo ?? 0);

  return (
    <div className="flex items-center gap-1.5">
      <div className="flex gap-1 text-xs">
        <span className="text-emerald-600 font-medium" title="Positivos">
          +{pub.sentimiento_positivo ?? 0}
        </span>
        <span className="text-amber-600 font-medium" title="Neutros">
          ~{pub.sentimiento_neutro ?? 0}
        </span>
        <span className="text-red-600 font-medium" title="Negativos">
          -{pub.sentimiento_negativo ?? 0}
        </span>
      </div>
      <span className="text-muted-foreground text-xs">({total})</span>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => analyzeMutation.mutate()}
        disabled={analyzeMutation.isPending}
        className="h-6 w-6 p-0"
        title="Re-analizar"
      >
        <RefreshCw className={`w-3 h-3 ${analyzeMutation.isPending ? 'animate-spin' : ''}`} />
      </Button>
    </div>
  );
}

export function PublicacionesList({ campaignId, onInfluencerClick }: PublicacionesListProps) {
  const { data: publicaciones, isLoading } = useQuery({
    queryKey: ['publicaciones', campaignId],
    queryFn: () => publicacionesApi.list({ campaign_id: campaignId, limit: 200 }),
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground text-center py-8">Cargando publicaciones...</p>
        </CardContent>
      </Card>
    );
  }

  if (!publicaciones || publicaciones.length === 0) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground text-center py-8">
            No hay publicaciones registradas para esta campaña
          </p>
        </CardContent>
      </Card>
    );
  }

  const analyzedCount = publicaciones.filter(
    (p) => (p.sentimiento_positivo ?? 0) > 0 || (p.sentimiento_neutro ?? 0) > 0 || (p.sentimiento_negativo ?? 0) > 0
  ).length;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-1">
        <p className="text-xs text-muted-foreground">
          {publicaciones.length} publicaciones · {analyzedCount} con sentimiento
        </p>
      </div>

      {publicaciones.map((pub: Publicacion) => (
        <Card key={pub.id} className="p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                {pub.formato && (
                  <Badge variant="outline" className={`text-xs ${FORMAT_COLORS[pub.formato.toLowerCase()] || 'bg-slate-100 text-slate-700'}`}>
                    {pub.formato}
                  </Badge>
                )}
                <Badge variant="outline" className="text-xs">
                  {pub.plataforma}
                </Badge>
                <span className="text-xs text-muted-foreground">{formatDate(pub.fecha_publicacion)}</span>
                {pub.url_publicacion && (
                  <a
                    href={pub.url_publicacion}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    Ver post
                  </a>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs">
                <div>
                  <span className="text-muted-foreground">Vistas: </span>
                  <span className="font-medium">{formatNumber(pub.vistas)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Alcance: </span>
                  <span className="font-medium">{formatNumber(pub.alcance)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Likes: </span>
                  <span className="font-medium">{formatNumber(pub.likes)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Comments: </span>
                  <span className="font-medium">{formatNumber(pub.comentarios)}</span>
                </div>
                {pub.er_alcance != null && (
                  <div>
                    <span className="text-muted-foreground">ER: </span>
                    <span className="font-medium">{(parseFloat(String(pub.er_alcance)) * 100).toFixed(2)}%</span>
                  </div>
                )}
                {pub.retencion != null && (
                  <div>
                    <span className="text-muted-foreground">Retención: </span>
                    <span className="font-medium">{(parseFloat(String(pub.retencion)) * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>

              <div className="flex items-center mt-2">
                <SentimentBadge pub={pub} />
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
