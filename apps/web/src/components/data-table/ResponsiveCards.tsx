import { ReactNode } from 'react';
import { Card } from '@/components/ui/card';

export interface CardField<T> {
  key: string;
  label: string;
  render: (item: T) => ReactNode;
  primary?: boolean;
}

interface ResponsiveCardsProps<T> {
  data: T[];
  fields: CardField<T>[];
  keyExtractor: (item: T) => string;
  onCardClick?: (item: T) => void;
  emptyMessage?: string;
  loading?: boolean;
}

export function ResponsiveCards<T extends { id: string }>({
  data,
  fields,
  keyExtractor,
  onCardClick,
  emptyMessage = 'No hay datos',
  loading = false,
}: ResponsiveCardsProps<T>) {
  if (loading) {
    return (
      <div className="text-center text-muted-foreground py-8 md:hidden">
        Cargando...
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8 md:hidden">
        {emptyMessage}
      </div>
    );
  }

  const primaryField = fields.find((f) => f.primary);
  const secondaryFields = fields.filter((f) => !f.primary);

  return (
    <div className="space-y-3 md:hidden">
      {data.map((item) => (
        <Card
          key={keyExtractor(item)}
          className={`p-4 ${onCardClick ? 'cursor-pointer hover:bg-hover transition-colors' : ''}`}
          onClick={() => onCardClick?.(item)}
        >
          {primaryField && (
            <div className="font-medium text-sm mb-2 pb-2 border-b">
              {primaryField.render(item)}
            </div>
          )}
          <div className="space-y-1.5">
            {secondaryFields.map((field) => (
              <div key={field.key} className="flex items-start justify-between gap-2 text-xs">
                <span className="text-muted-foreground flex-shrink-0">{field.label}</span>
                <span className="text-right">{field.render(item)}</span>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
