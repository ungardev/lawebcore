import { Sparkles, Search, TrendingUp, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

type EmptyStateVariant = 'no_conversations' | 'no_results' | 'no_candidates';

interface LensEmptyStateProps {
  variant?: EmptyStateVariant;
  className?: string;
}

const variants: Record<EmptyStateVariant, { icon: React.ReactNode; title: string; description: string }> = {
  no_conversations: {
    icon: <MessageSquare className="w-10 h-10" />,
    title: 'Sin conversaciones aún',
    description: 'Comienza una nueva conversación para descubrir influencers ideales para tu campaña.',
  },
  no_results: {
    icon: <Search className="w-10 h-10" />,
    title: 'Sin resultados',
    description: 'Intenta ajustar tu búsqueda con palabras clave diferentes o menos filtros.',
  },
  no_candidates: {
    icon: <TrendingUp className="w-10 h-10" />,
    title: 'Sin candidatos',
    description: 'Aún no se han encontrado influencers. Ejecuta una búsqueda para comenzar.',
  },
};

export function LensEmptyState({ variant = 'no_conversations', className }: LensEmptyStateProps) {
  const v = variants[variant];

  return (
    <div className={cn('flex flex-col items-center justify-center py-16 text-center', className)}>
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-pink-500/10 to-blue-500/10 flex items-center justify-center text-primary mb-4">
        {v.icon}
      </div>
      <h3 className="font-semibold text-foreground mb-1">{v.title}</h3>
      <p className="text-sm text-muted-foreground max-w-xs">{v.description}</p>
    </div>
  );
}
