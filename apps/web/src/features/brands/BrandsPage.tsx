import { useQuery } from '@tanstack/react-query';
import { brandsApi, clientsApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { useState } from 'react';
import { ResponsiveTable } from '@/components/data-table/ResponsiveTable';

export function BrandsPage() {
  const [clientFilter, setClientFilter] = useState('');
  const { data: brands, isLoading } = useQuery({
    queryKey: ['brands', { clientFilter }],
    queryFn: () => brandsApi.list({ client_id: clientFilter || undefined }),
  });
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });

  const clientMap = new Map((clients || []).map((c) => [c.id, c]));

  return (
    <div className="space-y-4 md:space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Marcas</h1>
        <p className="text-sm md:text-base text-muted-foreground">{brands?.length ?? 0} marcas registradas</p>
      </div>

      <Card className="p-3 md:p-4">
        <div className="mb-4">
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm w-full sm:w-auto"
          >
            <option value="">Todos los clientes</option>
            {clients?.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <ResponsiveTable
          data={brands || []}
          keyExtractor={(b) => b.id}
          loading={isLoading}
          emptyMessage="No hay marcas"
          columns={[
            {
              key: 'name',
              label: 'Marca',
              render: (b: any) => (
                <div>
                  <div className="font-medium">{b.name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{b.code}</div>
                </div>
              ),
            },
            { key: 'client', label: 'Cliente', render: (b: any) => clientMap.get(b.client_id)?.name || '—' },
            { key: 'category', label: 'Categoria', render: (b: any) => b.category || '—' },
            { key: 'is_active', label: 'Estado', render: (b: any) => b.is_active ? 'Activo' : 'Inactivo' },
          ]}
          cardFields={[
            { key: 'name', label: '', primary: true, render: (b: any) => <div><div className="font-medium">{b.name}</div><div className="text-xs text-muted-foreground font-mono">{b.code}</div></div> },
            { key: 'client', label: 'Cliente', render: (b: any) => clientMap.get(b.client_id)?.name || '—' },
            { key: 'category', label: 'Categoria', render: (b: any) => b.category || '—' },
            { key: 'is_active', label: 'Estado', render: (b: any) => b.is_active ? 'Activo' : 'Inactivo' },
          ]}
        />
      </Card>
    </div>
  );
}
