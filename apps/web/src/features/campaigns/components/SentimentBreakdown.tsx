import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export interface SentimentData {
  positivo: number;
  neutro: number;
  negativo: number;
}

export interface SentimentBreakdownProps {
  data: SentimentData;
  confidence?: number | null;
  compact?: boolean;
}

const COLORS = ['#10b981', '#f59e0b', '#ef4444'];
const LABELS = ['Positivo', 'Neutro', 'Negativo'];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function SentimentBreakdown({ data, confidence, compact = false }: SentimentBreakdownProps) {
  const total = data.positivo + data.neutro + data.negativo;

  if (total === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>Sentimiento de Comentarios</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-6">
            No hay datos de sentimiento todavía
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData = [
    { name: 'Positivo', value: data.positivo, color: COLORS[0] },
    { name: 'Neutro', value: data.neutro, color: COLORS[1] },
    { name: 'Negativo', value: data.negativo, color: COLORS[2] },
  ];

  const pct = (v: number) => ((v / total) * 100).toFixed(1);

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="text-emerald-600 font-medium">+{data.positivo}</span>
        <span className="text-amber-600 font-medium">~{data.neutro}</span>
        <span className="text-red-600 font-medium">-{data.negativo}</span>
        {confidence != null && confidence > 0 && (
          <span className="text-muted-foreground">({confidence}%)</span>
        )}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Sentimiento de Comentarios</span>
          {confidence != null && confidence > 0 && (
            <span className="text-xs font-normal text-muted-foreground">
              Confianza: {confidence}%
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div style={{ height: '200px', minHeight: '200px' }}>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [value, '']}
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-2">
          {chartData.map((entry, i) => (
            <div key={entry.name}>
              <div className="flex items-center justify-between text-sm mb-1">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                  <span>{entry.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{entry.value}</span>
                  <span className="text-muted-foreground text-xs">({pct(entry.value)}%)</span>
                </div>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${pct(entry.value)}%`,
                    backgroundColor: entry.color,
                  }}
                />
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between text-sm font-semibold pt-2 border-t">
            <span>Total</span>
            <span>{total}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
