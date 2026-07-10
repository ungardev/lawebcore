import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface SentimentData {
  positivo: number;
  neutro: number;
  negativo: number;
}

interface SentimentBreakdownProps {
  data: SentimentData;
}

const COLORS = ['#10b981', '#f59e0b', '#ef4444'];
const LABELS = ['Positivo', 'Neutro', 'Negativo'];

export function SentimentBreakdown({ data }: SentimentBreakdownProps) {
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

  const pct = (v: number) => `${((v / total) * 100).toFixed(1)}%`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sentimiento de Comentarios</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-[180px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={75}
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
            <div key={entry.name} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                <span>{entry.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">{entry.value}</span>
                <span className="text-muted-foreground text-xs">({pct(entry.value)})</span>
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
