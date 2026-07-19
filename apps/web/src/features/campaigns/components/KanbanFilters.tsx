import { Search } from 'lucide-react';
import { Brand, Client } from '@/types';

interface KanbanFiltersProps {
  search: string;
  onSearchChange: (_s: string) => void;
  clientFilter: string;
  onClientFilterChange: (_c: string) => void;
  brandFilter: string;
  onBrandFilterChange: (_b: string) => void;
  clients: Client[];
  brands: Brand[];
}

export function KanbanFilters({
  search,
  onSearchChange,
  clientFilter,
  onClientFilterChange,
  brandFilter,
  onBrandFilterChange,
  clients,
  brands,
}: KanbanFiltersProps) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="relative flex-1 min-w-[200px] max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Buscar campana..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>
      <select
        value={clientFilter}
        onChange={(e) => { onClientFilterChange(e.target.value); onBrandFilterChange(''); }}
        className="px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">Todos los clientes</option>
        {clients.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <select
        value={brandFilter}
        onChange={(e) => { onBrandFilterChange(e.target.value); onClientFilterChange(''); }}
        className="px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">Todas las marcas</option>
        {brands.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
          </option>
        ))}
      </select>
    </div>
  );
}
