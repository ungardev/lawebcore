import { Search, BarChart2, TrendingUp, Users, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const ACTIONS = [
  { label: 'Buscar creadores', icon: Search, prompt: 'Busca influencers relevantes para mi campaña actual.' },
  { label: 'Analisis de campaña', icon: BarChart2, prompt: 'Dame un analisis detallado de la campaña activa, con métricas y recomendaciones.' },
  { label: 'Proyeccion 3 escenarios', icon: TrendingUp, prompt: 'Genera una proyección de 3 escenarios (conservador, moderado, optimista) para el alcance y engagement.' },
  { label: 'Mis creadores guardados', icon: Users, prompt: 'Muestrame todos los creadores que tengo guardados en mi cartera.' },
  { label: 'Cargar un brief', icon: FileText, prompt: 'Ayudame a estructurar un brief para una nueva campaña de influencer marketing.' },
];

interface ActionChipsProps {
  onSend: (prompt: string) => void;
  disabled?: boolean;
  className?: string;
}

export function ActionChips({ onSend, disabled, className }: ActionChipsProps) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {ACTIONS.map((action) => (
        <Button
          key={action.label}
          variant="outline"
          size="sm"
          onClick={() => onSend(action.prompt)}
          disabled={disabled}
          className={cn(
            'min-h-8 text-xs gap-1.5 px-2.5 bg-surface-raised hover:bg-surface-3 border-divider',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <action.icon className="w-3 h-3 text-primary" />
          {action.label}
        </Button>
      ))}
    </div>
  );
}
