import { Search } from 'lucide-react';

interface KanbanFiltersProps {
  search: string;
  onSearchChange: (s: string) => void;
  clientFilter: string;
  onClientFilterChange: (c: string) => void;
  clients: { id: string; name: string }[];
}

export function KanbanFilters({
  search,
  onSearchChange,
  clientFilter,
  onClientFilterChange,
  clients,
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
        onChange={(e) => onClientFilterChange(e.target.value)}
        className="px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="">Todos los clientes</option>
        {clients.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}
