import { useCallback, useState } from 'react';
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefStructured } from '../types/discovery';

type BriefExtractedCallback = (_: BriefStructured, _2: string) => void;
interface FileUploadZoneProps {
  onBriefExtracted: BriefExtractedCallback;
  onClear: () => void;
  isLoading: boolean;
  extractedBrief: BriefStructured | null;
  extractedFileName: string | null;
}

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

export function FileUploadZone({
  onBriefExtracted,
  onClear,
  isLoading,
  extractedBrief,
  extractedFileName,
}: FileUploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    const allowed = ['application/pdf', 'text/plain', 'text/csv'];
    const ext = file.name.toLowerCase().split('.').pop();
    const allowedExt = ['pdf', 'txt', 'csv'];

    if (!allowed.includes(file.type) && !allowedExt.includes(ext || '')) {
      setErrorMessage('Formato no soportado. Usa PDF, TXT o CSV.');
      setUploadState('error');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setErrorMessage('Archivo muy grande. Máximo 5MB.');
      setUploadState('error');
      return;
    }

    setUploadState('uploading');
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/v1/lens/discovery/upload-brief', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      onBriefExtracted(result.brief as BriefStructured, result.file_name as string);
      setUploadState('success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al procesar archivo';
      setErrorMessage(msg);
      setUploadState('error');
    }
  }, [onBriefExtracted]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleClear = useCallback(() => {
    setUploadState('idle');
    setErrorMessage(null);
    onClear();
  }, [onClear]);

  if (extractedBrief && extractedFileName) {
    return (
      <div className="border-2 border-green-200 bg-green-50 rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
            <span className="text-sm font-medium text-green-800">
              {extractedFileName}
            </span>
          </div>
          <button
            type="button"
            onClick={handleClear}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs text-green-700">
          {extractedBrief.product_name && (
            <div><span className="opacity-70">Producto:</span> {extractedBrief.product_name}</div>
          )}
          {extractedBrief.brand_name && (
            <div><span className="opacity-70">Marca:</span> {extractedBrief.brand_name}</div>
          )}
          {extractedBrief.industry && (
            <div><span className="opacity-70">Industria:</span> {extractedBrief.industry}</div>
          )}
          {extractedBrief.campaign_objective && (
            <div><span className="opacity-70">Objetivo:</span> {extractedBrief.campaign_objective}</div>
          )}
          {extractedBrief.budget_usd && (
            <div><span className="opacity-70">Budget:</span> ${extractedBrief.budget_usd.toLocaleString()} {extractedBrief.budget_currency}</div>
          )}
          {extractedBrief.audience_countries && extractedBrief.audience_countries.length > 0 && (
            <div><span className="opacity-70">Países:</span> {extractedBrief.audience_countries.join(', ')}</div>
          )}
          {extractedBrief.niches && extractedBrief.niches.length > 0 && (
            <div><span className="opacity-70">Nichos:</span> {extractedBrief.niches.slice(0, 3).join(', ')}</div>
          )}
          {extractedBrief.kpis && extractedBrief.kpis.length > 0 && (
            <div><span className="opacity-70">KPIs:</span> {extractedBrief.kpis.join(', ')}</div>
          )}
          {extractedBrief.competitor_brands && extractedBrief.competitor_brands.length > 0 && (
            <div><span className="opacity-70">Competencia:</span> {extractedBrief.competitor_brands.slice(0, 2).join(', ')}</div>
          )}
          {extractedBrief.influencer_preferences && (
            <div>
              <span className="opacity-70">Tiers:</span>{' '}
              {(extractedBrief.influencer_preferences as Record<string, unknown>).tiers instanceof Array
                ? ((extractedBrief.influencer_preferences as Record<string, unknown>).tiers as string[]).join(', ')
                : null}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (uploadState === 'uploading' || isLoading) {
    return (
      <div className="border-2 border-dashed border-brand-purple/40 bg-brand-purple/5 rounded-lg p-6 flex flex-col items-center gap-2">
        <Loader2 className="w-6 h-6 text-brand-purple animate-spin" />
        <p className="text-sm text-brand-purple font-medium">Analizando brief con IA...</p>
        <p className="text-xs text-muted-foreground">Extrayendo datos del documento</p>
      </div>
    );
  }

  if (uploadState === 'error') {
    return (
      <div className="border-2 border-red-200 bg-red-50 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-red-700 font-medium">Error al procesar archivo</p>
            <p className="text-xs text-red-600 mt-0.5">{errorMessage}</p>
          </div>
          <button type="button" onClick={handleClear} className="text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={cn(
        'border-2 border-dashed rounded-lg p-4 transition-colors',
        dragOver
          ? 'border-brand-purple bg-brand-purple/5'
          : 'border-muted-foreground/30 hover:border-brand-purple/50 hover:bg-muted/50'
      )}
    >
      <label className="flex flex-col items-center gap-2 cursor-pointer">
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-10 h-10 rounded-full flex items-center justify-center',
            dragOver ? 'bg-brand-purple/20' : 'bg-muted'
          )}>
            <Upload className={cn('w-5 h-5', dragOver ? 'text-brand-purple' : 'text-muted-foreground')} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">
              Arrastra tu brief aquí
            </p>
            <p className="text-xs text-muted-foreground">
              PDF · TXT · CSV — máximo 5MB
            </p>
          </div>
        </div>
        <input
          type="file"
          accept=".pdf,.txt,.csv"
          onChange={handleInputChange}
          className="hidden"
        />
        <div className="flex items-center gap-1.5 mt-1">
          <FileText className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">o haz click para seleccionar</span>
        </div>
      </label>
    </div>
  );
}
