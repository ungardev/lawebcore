import { Hash, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
    <div className="rounded-md border border-primary/25 bg-primary/10 p-4 text-card-foreground">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-eyebrow text-primary">Brief detectado</span>
        <Badge variant="outline" className="border-primary/25 bg-primary/10 text-primary">Revisión requerida</Badge>
      </div>
      <p className="mt-2 text-xs leading-5 text-muted-foreground">Confirma los parámetros que Lens utilizará para iniciar la búsqueda.</p>

      <div className="mt-4 grid grid-cols-1 gap-2 border-t border-primary/15 pt-3 text-xs sm:grid-cols-2">
        {brief.product_name && <SummaryField label="Producto" value={brief.product_name} />}
        {brief.industry && <SummaryField label="Industria" value={brief.industry} />}
        {brief.niches.length > 0 && <SummaryField label="Nichos" value={brief.niches.join(', ')} />}
        <SummaryField label="Audiencia" value={`${brief.audience_gender === 'all' ? 'Todos' : brief.audience_gender === 'female' ? 'Mujeres' : 'Hombres'}, ${brief.audience_age_min}-${brief.audience_age_max} años`} />
        {brief.audience_countries.length > 0 && <SummaryField label="Países" value={brief.audience_countries.join(', ')} />}
        {brief.platforms.length > 0 && <SummaryField label="Plataformas" value={brief.platforms.join(', ')} />}
        {brief.tone.length > 0 && <SummaryField label="Tono" value={brief.tone.join(', ')} />}
      </div>

      {brief.hashtags.length > 0 && (
        <div className="mt-3 border-t border-primary/15 pt-3">
          <span className="text-xs text-muted-foreground">Hashtags</span>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {brief.hashtags.slice(0, 15).map((hashtag) => <Badge key={hashtag} variant="outline" className="border-primary/20 bg-background/30 text-primary"><Hash className="h-2.5 w-2.5" aria-hidden="true" />{hashtag}</Badge>)}
            {brief.hashtags.length > 15 && <span className="px-1 text-xs text-muted-foreground">+{brief.hashtags.length - 15} más</span>}
          </div>
        </div>
      )}

      {brief.additional_context && <p className="mt-3 border-t border-primary/15 pt-3 text-xs italic leading-5 text-muted-foreground">“{brief.additional_context}”</p>}

      <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row">
        {onEdit && <Button type="button" variant="outline" onClick={onEdit} disabled={isLoading} className="sm:w-auto">Editar brief</Button>}
        {onConfirm && <Button type="button" onClick={onConfirm} disabled={isLoading} className="flex-1 gap-2">{isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}{isLoading ? 'Buscando…' : 'Buscar con este brief'}</Button>}
      </div>
    </div>
  );
}

function SummaryField({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><span className="text-muted-foreground">{label}:</span> <span className="font-medium text-foreground">{value}</span></div>;
}
