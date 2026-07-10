import { memo } from 'react';
import { Card } from '@/components/ui/card';
import { Calendar, Users } from 'lucide-react';

export interface KanbanCardData {
  id: string;
  code: string;
  name: string;
  objective?: string;
  num_influencers?: number;
  budget_total?: number | null;
  end_date?: string | null;
  brand_id?: string;
  client_id?: string;
}

interface KanbanCardProps {
  card: KanbanCardData;
  isDragging?: boolean;
  onDragStart: (e: React.DragEvent, id: string) => void;
}

export const KanbanCard = memo(function KanbanCard({ card, isDragging, onDragStart }: KanbanCardProps) {
  return (
    <Card
      draggable
      onDragStart={(e) => onDragStart(e, card.id)}
      className={`p-3 cursor-move hover:shadow-md transition-all ${
        isDragging ? 'opacity-50 rotate-2' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <div className="text-xs font-mono text-muted-foreground">{card.code}</div>
        {card.budget_total && (
          <span className="text-xs font-semibold text-green-600">
            ${card.budget_total.toLocaleString()}
          </span>
        )}
      </div>
      <div className="font-medium text-sm leading-snug mb-2 line-clamp-2">
        {card.name}
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          <span>{card.num_influencers ?? 0}</span>
        </div>
        {card.end_date && (
          <div className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            <span>{new Date(card.end_date).toLocaleDateString('es-VE', { day: '2-digit', month: 'short' })}</span>
          </div>
        )}
      </div>
    </Card>
  );
});
