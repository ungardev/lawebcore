import { ReactNode } from 'react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { ResponsiveCards, CardField } from './ResponsiveCards';

interface Column<T> {
  key: string;
  label: string;
  render: (item: T) => ReactNode;
  className?: string;
}

interface ResponsiveTableProps<T> {
  data: T[];
  columns: Column<T>[];
  cardFields?: CardField<T>[];
  keyExtractor: (item: T) => string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  loading?: boolean;
}

export function ResponsiveTable<T extends { id: string }>({
  data,
  columns,
  cardFields,
  keyExtractor,
  onRowClick,
  emptyMessage,
  loading,
}: ResponsiveTableProps<T>) {
  return (
    <>
      {cardFields && (
        <ResponsiveCards
          data={data}
          fields={cardFields}
          keyExtractor={keyExtractor}
          onCardClick={onRowClick}
          emptyMessage={emptyMessage}
          loading={loading}
        />
      )}

      <div className="hidden md:block overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col.key} className={col.className}>{col.label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-8">
                  Cargando...
                </TableCell>
              </TableRow>
            )}
            {data.map((item) => (
              <TableRow
                key={keyExtractor(item)}
                className={onRowClick ? 'cursor-pointer hover:bg-accent' : ''}
                onClick={() => onRowClick?.(item)}
              >
                {columns.map((col) => (
                  <TableCell key={col.key} className={col.className}>
                    {col.render(item)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {!loading && data.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-8">
                  {emptyMessage || 'No hay datos'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </>
  );
}
