import { memo } from 'react';
import { KanbanCard, KanbanCardData } from './KanbanCard';
import { STATUS_COLORS, cn } from '@/lib/utils';

interface KanbanColumnProps {
  status: string;
  cards: KanbanCardData[];
  totalBudget: number;
  onDragStart: (e: React.DragEvent, id: string) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent, status: string) => void;
  isDragOver?: boolean;
}

export const KanbanColumn = memo(function KanbanColumn({
  status,
  cards,
  totalBudget,
  onDragStart,
  onDragOver,
  onDrop,
  isDragOver,
}: KanbanColumnProps) {
  return (
    <div
      className={cn(
        'w-72 flex-shrink-0 transition-all',
        isDragOver && 'ring-2 ring-primary ring-offset-2 rounded-lg'
      )}
      onDragOver={onDragOver}
      onDrop={(e) => onDrop(e, status)}
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
        {cards.map((card) => (
          <KanbanCard key={card.id} card={card} onDragStart={onDragStart} />
        ))}
        {cards.length === 0 && (
          <div className="text-center text-xs text-muted-foreground py-8 border-2 border-dashed rounded">
            Arrastra aqui
          </div>
        )}
      </div>
    </div>
  );
});
