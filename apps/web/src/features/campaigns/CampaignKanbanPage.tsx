import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { campaignsApi, clientsApi } from '@/lib/api';
import { CAMPAIGN_STATUSES } from '@/lib/utils';
import { toast } from 'sonner';
import { KanbanColumn } from './components/KanbanColumn';
import { KanbanFilters } from './components/KanbanFilters';
import type { KanbanCardData } from './components/KanbanCard';

const COLUMNS = CAMPAIGN_STATUSES.filter((s) => !['CANCELADA', 'PAUSADA'].includes(s));

export function CampaignKanbanPage() {
  const qc = useQueryClient();
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  const { data: kanban } = useQuery({
    queryKey: ['campaigns-kanban'],
    queryFn: () => campaignsApi.kanban(),
  });

  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
    staleTime: 5 * 60 * 1000,
  });

  const changeStatus = useMutation({
    mutationFn: ({ id, to_status }: { id: string; to_status: string }) =>
      campaignsApi.changeStatus(id, to_status),
    onMutate: async ({ id, to_status }) => {
      await qc.cancelQueries({ queryKey: ['campaigns-kanban'] });
      const previous = qc.getQueryData<any>(['campaigns-kanban']);
      qc.setQueryData<any>(['campaigns-kanban'], (old: any) => {
        if (!old) return old;
        const newColumns = { ...old.columns };
        let movedCard: KanbanCardData | null = null;
        for (const col of Object.keys(newColumns)) {
          const idx = newColumns[col].findIndex((c: any) => c.id === id);
          if (idx >= 0) {
            [movedCard] = newColumns[col].splice(idx, 1);
            break;
          }
        }
        if (movedCard) {
          newColumns[to_status] = [...(newColumns[to_status] || []), movedCard];
        }
        return { ...old, columns: newColumns };
      });
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) qc.setQueryData(['campaigns-kanban'], ctx.previous);
      toast.error('Error al cambiar status');
    },
    onSuccess: () => toast.success('Status actualizado'),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['campaigns-kanban'] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const filteredColumns = useMemo(() => {
    if (!kanban?.columns) return {};
    const result: Record<string, KanbanCardData[]> = {};
    const s = search.toLowerCase();
    for (const status of COLUMNS) {
      const cards = kanban.columns[status] || [];
      result[status] = cards.filter((c: any) => {
        if (clientFilter && c.client_id !== clientFilter) return false;
        if (search) {
          const name = (c.name || '').toLowerCase();
          const code = (c.code || '').toLowerCase();
          if (!name.includes(s) && !code.includes(s)) return false;
        }
        return true;
      });
    }
    return result;
  }, [kanban, search, clientFilter]);

  const columnStats = useMemo(() => {
    const stats: Record<string, number> = {};
    for (const status of COLUMNS) {
      stats[status] = (filteredColumns[status] || []).reduce(
        (sum, c) => sum + (c.budget_total || 0),
        0
      );
    }
    return stats;
  }, [filteredColumns]);

  const totalCards = useMemo(
    () => Object.values(filteredColumns).reduce((sum, arr) => sum + arr.length, 0),
    [filteredColumns]
  );

  const onDragStart = (e: React.DragEvent, id: string) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = (e: React.DragEvent, status?: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (status) setDragOverColumn(status);
  };

  const onDragLeave = () => setDragOverColumn(null);

  const onDrop = (e: React.DragEvent, to_status: string) => {
    e.preventDefault();
    const id = draggedId;
    setDraggedId(null);
    setDragOverColumn(null);
    if (!id) return;
    changeStatus.mutate({ id, to_status });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Pipeline de Campanas</h1>
          <p className="text-muted-foreground">
            {totalCards} campanas · Arrastra y suelta para mover entre estados
          </p>
        </div>
      </div>

      <KanbanFilters
        search={search}
        onSearchChange={setSearch}
        clientFilter={clientFilter}
        onClientFilterChange={setClientFilter}
        clients={clients.map((c: any) => ({ id: c.id, name: c.name }))}
      />

      <div
        className="overflow-x-auto pb-4 -mx-6 px-6"
        onDragLeave={onDragLeave}
      >
        <div className="flex gap-4 min-w-max pb-2">
          {COLUMNS.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              cards={filteredColumns[status] || []}
              totalBudget={columnStats[status] || 0}
              onDragStart={onDragStart}
              onDragOver={(e) => onDragOver(e, status)}
              onDrop={onDrop}
              isDragOver={dragOverColumn === status}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
