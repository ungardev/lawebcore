import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { campaignsApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { CAMPAIGN_STATUSES, STATUS_COLORS, cn } from '@/lib/utils';
import { toast } from 'sonner';

const COLUMNS = CAMPAIGN_STATUSES.filter((s) => !['CANCELADA', 'PAUSADA'].includes(s));

export function CampaignKanbanPage() {
  const qc = useQueryClient();
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const { data: kanban } = useQuery({ queryKey: ['campaigns-kanban'], queryFn: () => campaignsApi.kanban() });

  const changeStatus = useMutation({
    mutationFn: ({ id, to_status }: { id: string; to_status: string }) =>
      campaignsApi.changeStatus(id, to_status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns-kanban'] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Status actualizado');
    },
    onError: () => toast.error('Error al cambiar status'),
  });

  const onDragStart = (e: React.DragEvent, id: string) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const onDrop = (e: React.DragEvent, to_status: string) => {
    e.preventDefault();
    const id = draggedId;
    setDraggedId(null);
    if (!id) return;
    changeStatus.mutate({ id, to_status });
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Pipeline de Campanas</h1>
        <p className="text-muted-foreground">Arrastra y suelta para mover entre estados</p>
      </div>

      <div className="overflow-x-auto pb-4">
        <div className="flex gap-4 min-w-max">
          {COLUMNS.map((status) => {
            const cards = kanban?.columns?.[status] || [];
            return (
              <div
                key={status}
                className="w-72 flex-shrink-0"
                onDragOver={onDragOver}
                onDrop={(e) => onDrop(e, status)}
              >
                <div className={cn('rounded-t-lg border-t-4 p-3 bg-card border', STATUS_COLORS[status])}>
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm">{status.replace(/_/g, ' ')}</h3>
                    <span className="text-xs font-bold bg-background/50 px-2 py-0.5 rounded">{cards.length}</span>
                  </div>
                </div>
                <div className="bg-muted/30 p-2 space-y-2 min-h-[500px] rounded-b-lg border border-t-0">
                  {cards.map((card) => (
                    <Card
                      key={card.id}
                      draggable
                      onDragStart={(e) => onDragStart(e, card.id)}
                      className="p-3 cursor-move hover:shadow-md transition-shadow"
                    >
                      <div className="text-xs font-mono text-muted-foreground mb-1">{card.code}</div>
                      <div className="font-medium text-sm leading-snug mb-2">{card.name}</div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{card.num_influencers} influencers</span>
                        {card.budget_total && <span className="font-semibold">${card.budget_total.toLocaleString()}</span>}
                      </div>
                    </Card>
                  ))}
                  {cards.length === 0 && (
                    <div className="text-center text-xs text-muted-foreground py-8 border-2 border-dashed rounded">
                      Arrastra aqui
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}