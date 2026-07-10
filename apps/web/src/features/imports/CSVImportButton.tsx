import { useState, useRef } from 'react';
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2, Download } from 'lucide-react';
import { importsApi, type ImportReport } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface CSVImportButtonProps {
  campaignId: string;
  campaignName?: string;
  onSuccess?: (report: ImportReport) => void;
}

export function CSVImportButton({ campaignId, campaignName, onSuccess }: CSVImportButtonProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const downloadTemplate = async () => {
    try {
      const blob = await importsApi.getTemplate();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'piar_import_template.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Error descargando plantilla');
    }
  };

  const handleFile = async (file: File) => {
    if (!file.name.match(/\.(csv|xlsx?)$/i)) {
      toast.error('Formato no soportado. Usa .csv o .xlsx');
      return;
    }

    setUploading(true);
    setReport(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('campaign_id', campaignId);
    if (campaignName) formData.append('source', 'SHEETS');

    try {
      const result = await importsApi.uploadCsv(formData);
      setReport(result);

      if (result.inserted > 0 || result.updated > 0) {
        toast.success(`${result.inserted} insertadas, ${result.updated} actualizadas`);
      } else if (result.skipped > 0) {
        toast.warning(`${result.skipped} filas omitidas`);
      }

      if (result.errors.length > 0) {
        toast.error(`${result.errors.length} errores — revisa el reporte`);
      } else {
        toast.success('Importación completada sin errores');
      }

      onSuccess?.(result);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Error en la importación');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div className="space-y-3">
      <div
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer
          ${dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
          ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        <Upload className={`w-8 h-8 mx-auto mb-2 ${dragOver ? 'text-primary' : 'text-muted-foreground'}`} />
        <p className="text-sm font-medium">
          {uploading ? 'Importando...' : 'Arrastra tu CSV aquí o haz clic para seleccionar'}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Acepta .csv y .xlsx · Mapeo automático (español e inglés)
        </p>
        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          onClick={(e) => { e.stopPropagation(); downloadTemplate(); }}
        >
          <Download className="w-3 h-3 mr-1" />
          Descargar plantilla
        </Button>
      </div>

      {report && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Reporte de importación</span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-green-500/10 p-2">
              <p className="text-lg font-bold text-green-600">{report.inserted}</p>
              <p className="text-xs text-muted-foreground">Insertadas</p>
            </div>
            <div className="rounded-lg bg-blue-500/10 p-2">
              <p className="text-lg font-bold text-blue-600">{report.updated}</p>
              <p className="text-xs text-muted-foreground">Actualizadas</p>
            </div>
            <div className="rounded-lg bg-amber-500/10 p-2">
              <p className="text-lg font-bold text-amber-600">{report.skipped}</p>
              <p className="text-xs text-muted-foreground">Omitidas</p>
            </div>
          </div>

          {report.errors.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs font-medium text-destructive">
                <AlertCircle className="w-3 h-3" />
                {report.errors.length} error(es)
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {report.errors.slice(0, 10).map((err, i) => (
                  <div key={i} className="text-xs bg-destructive/5 rounded p-2 border border-destructive/20">
                    <span className="font-medium">Fila {err.row}:</span>{' '}
                    <span className="text-muted-foreground">{err.reason}</span>
                  </div>
                ))}
                {report.errors.length > 10 && (
                  <p className="text-xs text-muted-foreground">
                    +{report.errors.length - 10} errores más
                  </p>
                )}
              </div>
            </div>
          )}

          {report.errors.length === 0 && report.inserted > 0 && (
            <div className="flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="w-3 h-3" />
              Importación exitosa — 0 errores
            </div>
          )}
        </div>
      )}
    </div>
  );
}
