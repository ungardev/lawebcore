import { useQuery } from '@tanstack/react-query';
import { brandsApi, clientsApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { useState } from 'react';

export function BrandsPage() {
  const [clientFilter, setClientFilter] = useState('');
  const { data: brands } = useQuery({
    queryKey: ['brands', { clientFilter }],
    queryFn: () => brandsApi.list({ client_id: clientFilter || undefined }),
  });
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });

  const clientMap = new Map((clients || []).map((c) => [c.id, c]));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Marcas</h1>
        <p className="text-muted-foreground">{brands?.length ?? 0} marcas registradas</p>
      </div>

      <Card className="p-4">
        <div className="mb-4">
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm"
          >
            <option value="">Todos los clientes</option>
            {clients?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Marca</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Categoria</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {brands?.map((b) => (
              <TableRow key={b.id}>
                <TableCell>
                  <div className="font-medium">{b.name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{b.code}</div>
                </TableCell>
                <TableCell>{clientMap.get(b.client_id)?.name || '—'}</TableCell>
                <TableCell>{b.category || '—'}</TableCell>
                <TableCell>{b.is_active ? 'Activo' : 'Inactivo'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}