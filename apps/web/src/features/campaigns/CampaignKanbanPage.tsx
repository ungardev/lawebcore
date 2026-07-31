import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState, useRef } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { campaignsApi, clientsApi, brandsApi } from '@/lib/api';
import { CAMPAIGN_STATUSES } from '@/lib/utils';
import { toast } from 'sonner';
import { KanbanColumn } from './components/KanbanColumn';
import { KanbanFilters } from './components/KanbanFilters';
import { KanbanCard, KanbanCardData } from './components/KanbanCard';
import { RotateCcw } from 'lucide-react';

const COLUMNS = CAMPAIGN_STATUSES.filter((s) => !['CANCELADA', 'PAUSADA'].includes(s));

const STATUS_LABELS: Record<string, string> = {
  BRIEF: 'Brief',
  PULL: 'Pull',
  CONTACTANDO: 'Contactando',
  PLAN_DE_CUENTAS: 'Plan de Cuentas',
  CAMPAÑA_INTERNA: 'Campaña Interna',
  REPORTE: 'Reporte',
  TERMINADA: 'Terminada',
};

export function CampaignKanbanPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [brandFilter, setBrandFilter] = useState('');
  const [activeCard, setActiveCard] = useState<KanbanCardData | null>(null);
  const [originalStatus, setOriginalStatus] = useState<string | null>(null);
  const undoRef = useRef<{ id: string; previousStatus: string } | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 12 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 300, tolerance: 10 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const { data: kanban } = useQuery({
    queryKey: ['campaigns-kanban'],
    queryFn: () => campaignsApi.kanban(),
  });

  const { data: clients = [] } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: brands = [] } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.list(),
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
    onSuccess: (_data, vars) => {
      const undo = undoRef.current;
      toast.success(
        `Campaña movida a ${STATUS_LABELS[vars.to_status] || vars.to_status}`,
        {
          action: undo
            ? {
                label: 'Deshacer',
                onClick: () => {
                  changeStatus.mutate({ id: undo.id, to_status: undo.previousStatus });
                  undoRef.current = null;
                },
              }
            : undefined,
          duration: 5000,
          icon: undo ? <RotateCcw className="w-4 h-4" /> : undefined,
        },
      );
      undoRef.current = null;
    },
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
        if (brandFilter && c.brand_id !== brandFilter) return false;
        if (search) {
          const name = (c.name || '').toLowerCase();
          const code = (c.code || '').toLowerCase();
          if (!name.includes(s) && !code.includes(s)) return false;
        }
        return true;
      });
    }
    return result;
  }, [kanban, search, clientFilter, brandFilter]);

  const columnStats = useMemo(() => {
    const stats: Record<string, number> = {};
    for (const status of COLUMNS) {
      stats[status] = (filteredColumns[status] || []).reduce(
        (sum, c) => sum + (c.budget_total || 0),
        0,
      );
    }
    return stats;
  }, [filteredColumns]);

  const totalCards = useMemo(
    () => Object.values(filteredColumns).reduce((sum, arr) => sum + arr.length, 0),
    [filteredColumns],
  );

  const findCardColumn = (id: string): string | null => {
    for (const col of COLUMNS) {
      if ((filteredColumns[col] || []).some((c) => c.id === id)) return col;
    }
    return null;
  };

  const handleDragStart = (event: DragStartEvent) => {
    const card = findCardColumn(event.active.id as string);
    setOriginalStatus(card);
    const cardData = kanban
      ? (Object.values(kanban.columns || {}) as any[])
          .flat()
          .find((c: any) => c.id === event.active.id) as KanbanCardData | null
      : null;
    if (cardData) setActiveCard(cardData);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    let sourceCol: string | null = null;
    let targetCol: string | null = null;

    for (const col of COLUMNS) {
      if ((filteredColumns[col] || []).some((c) => c.id === activeId)) sourceCol = col;
      if (overId === col || (filteredColumns[col] || []).some((c) => c.id === overId)) targetCol = col;
    }

    if (!sourceCol || !targetCol || sourceCol === targetCol) return;

    qc.setQueryData<any>(['campaigns-kanban'], (old: any) => {
      if (!old) return old;
      const newColumns = { ...old.columns };
      const idx = (newColumns[sourceCol!] || []).findIndex((c: any) => c.id === activeId);
      if (idx >= 0) {
        const [moved] = newColumns[sourceCol!].splice(idx, 1);
        newColumns[targetCol!] = [...(newColumns[targetCol!] || []), moved];
      }
      return { ...old, columns: newColumns };
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCard(null);
    const id = active.id as string;

    if (!over) {
      setOriginalStatus(null);
      return;
    }

    const finalStatus = findCardColumn(id);

    if (finalStatus === null || finalStatus === originalStatus) {
      setOriginalStatus(null);
      return;
    }

    undoRef.current = { id, previousStatus: originalStatus! };
    changeStatus.mutate({ id, to_status: finalStatus });
    setOriginalStatus(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Pipeline de Campañas</h1>
          <p className="text-sm md:text-base text-muted-foreground">
            {totalCards} campañas · Manten click y arrastra para mover · Deshacer disponible por 5s
          </p>
        </div>
      </div>

      <KanbanFilters
        search={search}
        onSearchChange={setSearch}
        clientFilter={clientFilter}
        onClientFilterChange={setClientFilter}
        brandFilter={brandFilter}
        onBrandFilterChange={setBrandFilter}
        clients={clients}
        brands={brands}
      />

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div
          className="overflow-x-auto pb-4 -mx-6 px-6
                          touch-pan-y
                          [&::-webkit-scrollbar]:h-2
                          [&::-webkit-scrollbar-track]:bg-muted
                          [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30
                          [&::-webkit-scrollbar-thumb]:rounded-full
                          hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/50"
        >
          <div className="flex gap-3 md:gap-4 min-w-max pb-2">
            {COLUMNS.map((status) => (
              <KanbanColumn
                key={status}
                status={status}
                cards={filteredColumns[status] || []}
                totalBudget={columnStats[status] || 0}
                className="w-64 sm:w-72 flex-shrink-0"
              />
            ))}
          </div>
        </div>

        <DragOverlay>
          {activeCard ? (
            <div className="rotate-3 opacity-90 scale-105">
              <KanbanCard card={activeCard} isOverlay />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
