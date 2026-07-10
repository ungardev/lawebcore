import { useState } from 'react';
import { FileJson, Send, AlertCircle, CheckCircle2 } from 'lucide-react';
import { importsApi, type ImportReport } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface JSONImportPanelProps {
  onSuccess?: (report: ImportReport) => void;
}

const TEMPLATE_JSON = `[
  {
    "username": "usuario_ejemplo",
    "followers": 12300,
    "campaign_id": "UUID-DE-LA-CAMPAÑA",
    "campaign_name": "#NombreCampaña",
    "post_date": "DD-MM-AAAA",
    "post_url": "https://instagram.com/p/xxxx",
    "views": 5600,
    "likes": 410,
    "comments": 22,
    "saves": 9,
    "shares": 5,
    "data_quality_flags": [],
    "raw_data": {}
  }
]`;

export function JSONImportPanel({ onSuccess }: JSONImportPanelProps) {
  const [json, setJson] = useState(TEMPLATE_JSON);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  const validateJson = (text: string): boolean => {
    try {
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed)) {
        setParseError('El JSON debe ser un array de objetos');
        return false;
      }
      setParseError(null);
      return true;
    } catch {
      setParseError('JSON inválido — revisa la sintaxis');
      return false;
    }
  };

  const handleSubmit = async () => {
    if (!validateJson(json)) return;

    setUploading(true);
    setReport(null);

    try {
      const parsed = JSON.parse(json);
      const result = await importsApi.uploadJson(parsed);
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

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <FileJson className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-medium">JSON Data Contract</span>
      </div>

      <textarea
        value={json}
        onChange={(e) => { setJson(e.target.value); setParseError(null); }}
        className="w-full h-48 font-mono text-xs border rounded-lg p-3 bg-muted/30 resize-y
                   focus:outline-none focus:ring-2 focus:ring-primary"
        placeholder="Pega aquí tu JSON array siguiendo el data contract..."
        spellCheck={false}
      />

      {parseError && (
        <div className="flex items-center gap-1 text-xs text-destructive">
          <AlertCircle className="w-3 h-3" />
          {parseError}
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={uploading || Boolean(parseError)}
        className="w-full"
        size="sm"
      >
        <Send className="w-3 h-3 mr-1" />
        {uploading ? 'Importando...' : 'Importar JSON'}
      </Button>

      {report && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <FileJson className="w-4 h-4 text-muted-foreground" />
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
            <div className="max-h-40 overflow-y-auto space-y-1">
              {report.errors.slice(0, 5).map((err, i) => (
                <div key={i} className="text-xs bg-destructive/5 rounded p-2 border border-destructive/20">
                  <span className="font-medium">Fila {err.row}:</span>{' '}
                  <span className="text-muted-foreground">{err.reason}</span>
                </div>
              ))}
              {report.errors.length > 5 && (
                <p className="text-xs text-muted-foreground">
                  +{report.errors.length - 5} errores más
                </p>
              )}
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
