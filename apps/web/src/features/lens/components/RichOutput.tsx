import { Card } from '@/components/ui/card';

interface TableColumn {
  key: string;
  label: string;
}

interface TableRow {
  [key: string]: string | number | null;
}

interface RichTableProps {
  title?: string;
  columns: TableColumn[];
  rows: TableRow[];
  caption?: string;
}

function formatValue(val: string | number | null): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'number') {
    if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
    if (val >= 1_000) return `${(val / 1_000).toFixed(1)}K`;
    return val.toString();
  }
  return String(val);
}

export function RichTable({ title, columns, rows, caption }: RichTableProps) {
  return (
    <Card className="overflow-hidden mt-2 mb-2">
      {title && (
        <div className="px-4 py-2 border-b bg-muted/30">
          <p className="text-xs font-semibold text-foreground">{title}</p>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b bg-muted/20">
              {columns.map((col) => (
                <th key={col.key} className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-muted/30 transition-colors">
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2 whitespace-nowrap font-medium">
                    {formatValue(row[col.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {caption && (
        <div className="px-4 py-1.5 border-t bg-muted/20">
          <p className="text-[10px] text-muted-foreground italic">{caption}</p>
        </div>
      )}
    </Card>
  );
}
