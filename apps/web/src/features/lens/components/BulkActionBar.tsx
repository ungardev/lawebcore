import { Search, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BulkActionBarProps {
  count: number;
  onAnalyze: () => void;
  onClear: () => void;
  isLoading?: boolean;
  isDisabled?: boolean;
}

export function BulkActionBar({ count, onAnalyze, onClear, isLoading, isDisabled }: BulkActionBarProps) {
  if (count === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full border border-divider bg-panel px-5 py-3 shadow-soft">
      <span className="text-sm font-medium text-foreground">
        {count} seleccionado{count !== 1 ? 's' : ''}
      </span>
      <Button
        size="sm"
        variant="gradient"
        onClick={onAnalyze}
        disabled={isLoading || isDisabled}
        className="gap-1.5"
      >
        <Search className="h-3.5 w-3.5" aria-hidden="true" />
        {isLoading ? 'Analizando…' : `Analizar ${count} perfil${count !== 1 ? 'es' : ''}`}
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={onClear}
        className="gap-1 text-muted-foreground"
        aria-label="Limpiar selección"
      >
        <X className="h-3.5 w-3.5" aria-hidden="true" />
      </Button>
    </div>
  );
}
