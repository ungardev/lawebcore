import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface TimelineEntry {
  fecha: string | null;
  vistas: number | null;
  alcance: number | null;
  likes: number | null;
  comentarios: number | null;
  er: number | null;
}

interface KPITrendChartProps {
  data: TimelineEntry[];
  title?: string;
}

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function formatDate(fecha: string | null): string {
  if (!fecha) return '';
  try {
    return new Date(fecha).toLocaleDateString('es-VE', {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return '';
  }
}

export function KPITrendChart({ data, title = 'Evolución de KPIs' }: KPITrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            No hay datos de publicaciones todavía
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData = data.map((d) => ({
    fecha: formatDate(d.fecha),
    vistas: d.vistas ?? 0,
    alcance: d.alcance ?? 0,
    likes: d.likes ?? 0,
    comentarios: d.comentarios ?? 0,
    er: d.er != null ? parseFloat(String(d.er)) * 100 : null,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="fecha"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'hsl(var(--border))' }}
            />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickFormatter={formatNumber}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              domain={[0, 'auto']}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value: number, name: string) => {
                if (name === 'er') return [`${value.toFixed(2)}%`, 'ER'];
                return [formatNumber(value), name === 'vistas' ? 'Vistas' : name === 'alcance' ? 'Alcance' : name];
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="vistas"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Vistas"
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="alcance"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="Alcance"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="er"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3 }}
              name="ER %"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
