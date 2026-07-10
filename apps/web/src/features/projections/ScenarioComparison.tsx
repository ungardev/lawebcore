import { Card, CardContent } from '@/components/ui/card';
import { ProjectionTotal } from '@/types/piar';

interface ScenarioComparisonProps {
  total: ProjectionTotal | null;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

export function ScenarioComparison({ total }: ScenarioComparisonProps) {
  if (!total) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <p className="text-sm text-muted-foreground">
            Ajusta los posts por tier y presiona "Calcular proyección"
          </p>
        </CardContent>
      </Card>
    );
  }

  const escenarios = [
    {
      key: 'conservador',
      label: 'Conservador',
      color: 'text-blue-600',
      bg: 'bg-blue-50 border-blue-200',
      ring: 'ring-blue-300',
      multiplier: '×0.75',
    },
    {
      key: 'base',
      label: 'Base',
      color: 'text-emerald-600',
      bg: 'bg-emerald-50 border-emerald-200',
      ring: 'ring-emerald-400',
      multiplier: '×1.0',
    },
    {
      key: 'optimista',
      label: 'Optimista',
      color: 'text-purple-600',
      bg: 'bg-purple-50 border-purple-200',
      ring: 'ring-purple-300',
      multiplier: '×1.30',
    },
  ] as const;

  const metrics = [
    { key: 'vistas' as const, label: 'Vistas' },
    { key: 'alcance' as const, label: 'Alcance' },
    { key: 'engagement' as const, label: 'Engagement' },
    { key: 'posts_virales' as const, label: 'Posts virales' },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        {escenarios.map((e) => {
          const vals = total[e.key];
          return (
            <Card key={e.key} className={`${e.bg} border-2 ${e.key === 'base' ? e.ring : ''}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm font-bold ${e.color}`}>{e.label}</span>
                  <span className="text-xs text-muted-foreground">{e.multiplier}</span>
                </div>
                <div className="space-y-1">
                  {metrics.map((m) => (
                    <div key={m.key} className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{m.label}</span>
                      <span className={`text-xs font-semibold ${e.color}`}>
                        {m.key === 'posts_virales'
                          ? vals[m.key]
                          : formatNumber(vals[m.key])}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
