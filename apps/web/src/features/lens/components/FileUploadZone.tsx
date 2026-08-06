import { useCallback, useId, useState, type ChangeEvent, type DragEvent } from 'react';
import { AlertCircle, CheckCircle2, FileText, Loader2, Upload, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { lensApi } from '../api/lensApi';
import type { BriefStructured } from '../types/discovery';

type BriefExtractedCallback = (_: BriefStructured, _2: string) => void;
interface FileUploadZoneProps {
  onBriefExtracted: BriefExtractedCallback;
  onClear: () => void;
  isLoading: boolean;
  onLoadingChange?: (loading: boolean) => void;
  extractedBrief: BriefStructured | null;
  extractedFileName: string | null;
}

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export function FileUploadZone({ onBriefExtracted, onClear, isLoading, onLoadingChange, extractedBrief, extractedFileName }: FileUploadZoneProps) {
  const inputId = useId();
  const [dragOver, setDragOver] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    const allowedTypes = ['application/pdf', 'text/plain', 'text/csv', 'text/markdown', 'application/json'];
    const extension = file.name.toLowerCase().split('.').pop();
    const allowedExtensions = ['pdf', 'txt', 'csv', 'md', 'json'];

    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(extension || '')) {
      setErrorMessage('Formato no soportado. Usa PDF, TXT, CSV, MD o JSON.');
      setUploadState('error');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setErrorMessage('Archivo muy grande. El límite es 5MB.');
      setUploadState('error');
      return;
    }

    setUploadState('uploading');
    setErrorMessage(null);
    onLoadingChange?.(true);
    try {
      const result = await lensApi.uploadBrief(file);
      onBriefExtracted(result.brief, result.file_name);
      setUploadState('success');
    } catch (error) {
      const responseDetail = typeof error === 'object' && error !== null && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setErrorMessage(responseDetail || (error instanceof Error ? error.message : 'Error al procesar archivo'));
      setUploadState('error');
    } finally {
      onLoadingChange?.(false);
    }
  }, [onBriefExtracted, onLoadingChange]);

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);
    const file = event.dataTransfer.files[0];
    if (file) void handleFile(file);
  }, [handleFile]);

  const handleInputChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) void handleFile(file);
    event.target.value = '';
  }, [handleFile]);

  const handleClear = useCallback(() => {
    setUploadState('idle');
    setErrorMessage(null);
    onLoadingChange?.(false);
    onClear();
  }, [onClear, onLoadingChange]);

  if (extractedBrief && extractedFileName) {
    return (
      <div className="rounded-md border border-success/30 bg-success/10 p-4">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-success/15 text-success"><CheckCircle2 className="h-4 w-4" aria-hidden="true" /></span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate text-sm font-medium text-foreground">Brief analizado</p>
              <Badge variant="outline" className="border-success/30 bg-success/10 text-success">{extractedFileName}</Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Los datos detectados se incorporaron al resumen. Revisa y ajusta antes de ejecutar.</p>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={handleClear} className="-mr-2 -mt-2 h-8 w-8 text-muted-foreground hover:text-foreground" aria-label="Quitar brief cargado"><X className="h-4 w-4" aria-hidden="true" /></Button>
        </div>
        <div className="mt-4 grid gap-2 border-t border-success/20 pt-3 text-xs sm:grid-cols-2">
          {extractedBrief.product_name && <SummaryField label="Producto" value={extractedBrief.product_name} />}
          {extractedBrief.brand_name && <SummaryField label="Marca" value={extractedBrief.brand_name} />}
          {extractedBrief.industry && <SummaryField label="Industria" value={extractedBrief.industry} />}
          {extractedBrief.campaign_objective && <SummaryField label="Objetivo" value={extractedBrief.campaign_objective} />}
          {extractedBrief.budget_usd != null && <SummaryField label="Budget" value={`$${extractedBrief.budget_usd.toLocaleString()} ${extractedBrief.budget_currency ?? 'USD'}`} />}
          {extractedBrief.audience_countries?.length > 0 && <SummaryField label="Países" value={extractedBrief.audience_countries.join(', ')} />}
          {extractedBrief.niches?.length > 0 && <SummaryField label="Nichos" value={extractedBrief.niches.slice(0, 3).join(', ')} />}
          {extractedBrief.kpis?.length > 0 && <SummaryField label="KPIs" value={extractedBrief.kpis.join(', ')} />}
        </div>
      </div>
    );
  }

  if (uploadState === 'uploading' || isLoading) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-md border border-primary/30 bg-primary/10 p-6 text-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">Analizando brief con IA…</p>
        <p className="text-xs text-muted-foreground">Extrayendo producto, audiencia, objetivos y señales de campaña.</p>
      </div>
    );
  }

  if (uploadState === 'error') {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
          <div className="min-w-0 flex-1"><p className="text-sm font-medium text-foreground">No se pudo analizar el archivo</p><p className="mt-1 text-xs leading-5 text-destructive">{errorMessage}</p></div>
          <Button type="button" variant="ghost" size="icon" onClick={handleClear} className="-mr-2 -mt-2 h-8 w-8 text-destructive/70 hover:text-destructive" aria-label="Cerrar error de carga"><X className="h-4 w-4" aria-hidden="true" /></Button>
        </div>
      </div>
    );
  }

  return (
    <div onDragOver={(event) => { event.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop} className={cn('rounded-md border border-dashed p-4 transition-colors', dragOver ? 'border-primary bg-primary/10' : 'border-divider hover:border-primary/50 hover:bg-surface-raised')}>
      <div className="flex flex-col items-center gap-3 text-center" aria-live="polite">
        <span className={cn('flex h-10 w-10 items-center justify-center rounded-md transition-colors', dragOver ? 'bg-primary/15 text-primary' : 'bg-surface-raised text-muted-foreground')}><Upload className="h-5 w-5" aria-hidden="true" /></span>
        <div><p className="text-sm font-medium text-foreground">Arrastra tu brief aquí</p><p className="mt-1 text-xs text-muted-foreground">PDF · TXT · CSV · MD · JSON · máximo 5MB</p></div>
        <Button asChild type="button" variant="outline" size="sm" className="gap-2"><label htmlFor={inputId} className="cursor-pointer"><FileText className="h-3.5 w-3.5" aria-hidden="true" />Seleccionar archivo<input id={inputId} type="file" accept=".pdf,.txt,.csv,.md,.json" onChange={handleInputChange} className="sr-only" /></label></Button>
        <p className="text-[10px] text-muted-foreground">La extracción solo lee el documento para preparar el brief.</p>
      </div>
    </div>
  );
}

function SummaryField({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><span className="text-muted-foreground">{label}:</span> <span className="font-medium text-foreground">{value}</span></div>;
}
