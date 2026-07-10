import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { clientsApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { useState } from 'react';
import { ResponsiveTable } from '@/components/data-table/ResponsiveTable';

export function ClientsPage() {
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients', { search }],
    queryFn: () => clientsApi.list({ search: search || undefined }),
  });

  return (
    <div className="space-y-4 md:space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Clientes</h1>
        <p className="text-sm md:text-base text-muted-foreground">{clients?.length ?? 0} clientes corporativos</p>
      </div>

      <Card className="p-3 md:p-4">
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Buscar cliente..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <ResponsiveTable
          data={clients || []}
          keyExtractor={(c) => c.id}
          loading={isLoading}
          emptyMessage="No hay clientes"
          columns={[
            { key: 'code', label: 'Codigo', render: (c: any) => <span className="font-mono text-xs">{c.code}</span> },
            { key: 'name', label: 'Nombre', render: (c: any) => <span className="font-medium">{c.name}</span> },
            { key: 'industry', label: 'Industria', render: (c: any) => c.industry || '—' },
            {
              key: 'website',
              label: 'Website',
              render: (c: any) =>
                c.website ? (
                  <a href={c.website} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    {c.website}
                  </a>
                ) : '—',
            },
            { key: 'is_active', label: 'Estado', render: (c: any) => c.is_active ? 'Activo' : 'Inactivo' },
          ]}
          cardFields={[
            { key: 'name', label: '', primary: true, render: (c: any) => <span className="font-medium">{c.name}</span> },
            { key: 'code', label: 'Codigo', render: (c: any) => <span className="font-mono text-xs">{c.code}</span> },
            { key: 'industry', label: 'Industria', render: (c: any) => c.industry || '—' },
            { key: 'website', label: 'Website', render: (c: any) => c.website || '—' },
            { key: 'is_active', label: 'Estado', render: (c: any) => c.is_active ? 'Activo' : 'Inactivo' },
          ]}
        />
      </Card>
    </div>
  );
}
