import { memo } from 'react';
import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SortableKanbanCard } from './SortableKanbanCard';
import { KanbanCardData } from './KanbanCard';
import { STATUS_COLORS, cn } from '@/lib/utils';

interface KanbanColumnProps {
  status: string;
  cards: KanbanCardData[];
  totalBudget: number;
}

export const KanbanColumn = memo(function KanbanColumn({
  status,
  cards,
  totalBudget,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'w-72 flex-shrink-0 transition-all rounded-lg',
        isOver && 'ring-2 ring-primary ring-offset-2 bg-accent/20'
      )}
    >
      <div className={cn('rounded-t-lg border-t-4 p-3 bg-card border', STATUS_COLORS[status])}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm">{status.replace(/_/g, ' ')}</h3>
          <span className="text-xs font-bold bg-background/50 px-2 py-0.5 rounded">
            {cards.length}
          </span>
        </div>
        {totalBudget > 0 && (
          <div className="text-xs text-muted-foreground mt-1">
            ${totalBudget.toLocaleString()} total
          </div>
        )}
      </div>
      <div className="bg-muted/30 p-2 space-y-2 min-h-[500px] rounded-b-lg border border-t-0">
        <SortableContext items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <SortableKanbanCard key={card.id} card={card} />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="text-center text-xs text-muted-foreground py-8 border-2 border-dashed rounded">
            Arrastra aqui
          </div>
        )}
      </div>
    </div>
  );
});
