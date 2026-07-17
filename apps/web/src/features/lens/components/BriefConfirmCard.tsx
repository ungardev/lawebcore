import type { BriefStructured } from '../types/discovery';

interface BriefConfirmCardProps {
  brief: BriefStructured | null;
  onConfirm?: () => void;
  onEdit?: () => void;
  isLoading?: boolean;
}

export function BriefConfirmCard({ brief, onConfirm, onEdit, isLoading }: BriefConfirmCardProps) {
  if (!brief) return null;

  return (
    <div className="rounded-xl border bg-card p-4 text-card-foreground">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-primary">Brief Detectado</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-xs">
        {brief.product_name && (
          <div><span className="text-muted-foreground">Producto:</span> <span className="font-medium">{brief.product_name}</span></div>
        )}
        {brief.industry && (
          <div><span className="text-muted-foreground">Industria:</span> <span className="font-medium">{brief.industry}</span></div>
        )}
        {brief.niches.length > 0 && (
          <div><span className="text-muted-foreground">Nichos:</span> <span className="font-medium">{brief.niches.join(', ')}</span></div>
        )}
        <div>
          <span className="text-muted-foreground">Audiencia:</span>{' '}
          <span className="font-medium">
            {brief.audience_gender === 'all' ? 'Todos' : brief.audience_gender === 'female' ? 'Mujeres' : 'Hombres'},
            {brief.audience_age_min}-{brief.audience_age_max} años
          </span>
        </div>
        {brief.audience_countries.length > 0 && (
          <div><span className="text-muted-foreground">Países:</span> <span className="font-medium">{brief.audience_countries.join(', ')}</span></div>
        )}
        {brief.budget_usd != null && (
          <div><span className="text-muted-foreground">Presupuesto:</span> <span className="font-medium">${brief.budget_usd.toLocaleString()} USD</span></div>
        )}
        {brief.platforms.length > 0 && (
          <div><span className="text-muted-foreground">Plataformas:</span> <span className="font-medium">{brief.platforms.join(', ')}</span></div>
        )}
        {brief.tone.length > 0 && (
          <div><span className="text-muted-foreground">Tono:</span> <span className="font-medium">{brief.tone.join(', ')}</span></div>
        )}
      </div>

      {brief.additional_context && (
        <p className="text-xs text-muted-foreground mt-2 italic">"{brief.additional_context}"</p>
      )}

      <div className="flex gap-2 mt-4">
        {onConfirm && (
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 text-sm py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {isLoading ? 'Buscando...' : 'Buscar con este brief'}
          </button>
        )}
        {onEdit && (
          <button
            onClick={onEdit}
            className="text-sm py-2 px-3 rounded-lg border border-border hover:bg-muted transition-colors"
          >
            Editar
          </button>
        )}
      </div>
    </div>
  );
}
