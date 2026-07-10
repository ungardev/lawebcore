import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { KanbanCard, KanbanCardData } from './KanbanCard';

interface SortableKanbanCardProps {
  card: KanbanCardData;
}

export function SortableKanbanCard({ card }: SortableKanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
    >
      <KanbanCard card={card} isDragging={isDragging} />
    </div>
  );
}
