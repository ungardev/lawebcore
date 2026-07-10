import { useState } from 'react';
import { Plus, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { toast } from 'sonner';

interface ManualPublicationFormProps {
  campaignId: string;
  campaignName?: string;
  onSuccess?: () => void;
}

export function ManualPublicationForm({ campaignId, campaignName, onSuccess }: ManualPublicationFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState({
    username: '',
    post_date: '',
    post_url: '',
    views: '',
    likes: '',
    comments: '',
    saves: '',
    shares: '',
    alcance: '',
    followers: '',
    retention_seconds: '',
    plataforma: 'instagram',
    formato: 'reel',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!form.username.trim()) newErrors.username = 'Handle requerido';
    if (!form.post_date.trim()) newErrors.post_date = 'Fecha requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => { const e = { ...prev }; delete e[field]; return e; });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setSuccess(false);

    const payload = {
      username: form.username.trim(),
      followers: form.followers ? parseInt(form.followers) : null,
      campaign_id: campaignId,
      campaign_name: campaignName || null,
      post_date: form.post_date,
      post_url: form.post_url || null,
      views: form.views ? parseInt(form.views) : null,
      likes: form.likes ? parseInt(form.likes) : null,
      comments: form.comments ? parseInt(form.comments) : null,
      saves: form.saves ? parseInt(form.saves) : null,
      shares: form.shares ? parseInt(form.shares) : null,
      engagement_total:
        form.likes || form.comments || form.saves || form.shares
          ? (parseInt(form.likes) || 0) + (parseInt(form.comments) || 0) + (parseInt(form.saves) || 0) + (parseInt(form.shares) || 0)
          : null,
      retention_avg: form.retention_seconds && form.views
        ? parseFloat(form.retention_seconds) / parseInt(form.views)
        : null,
      data_quality_flags: [],
      raw_data: { ...form, source: 'MANUAL' },
    };

    try {
      const { importsApi } = await import('@/lib/api');
      const result = await importsApi.uploadJson([payload]);
      if (result.errors && result.errors.length > 0) {
        toast.error(`Error: ${result.errors[0].reason}`);
      } else {
        setSuccess(true);
        toast.success('Publicación registrada correctamente');
        setForm({
          username: '',
          post_date: '',
          post_url: '',
          views: '',
          likes: '',
          comments: '',
          saves: '',
          shares: '',
          alcance: '',
          followers: '',
          retention_seconds: '',
          plataforma: 'instagram',
          formato: 'reel',
        });
        onSuccess?.();
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass = (field: string) =>
    `w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary ${
      errors[field] ? 'border-destructive' : ''
    }`;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Carga manual de publicación
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Usa este formulario cuando el creador no quiere dar acceso a su API. Los datos se guardan con <code className="text-xs bg-muted px-1 rounded">source=MANUAL</code>.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Handle del influencer *
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">@</span>
                <input
                  type="text"
                  value={form.username}
                  onChange={(e) => handleChange('username', e.target.value)}
                  placeholder="usuario"
                  className={`${inputClass('username')} pl-7`}
                />
              </div>
              {errors.username && <p className="text-xs text-destructive mt-1">{errors.username}</p>}
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Fecha de publicación *
              </label>
              <input
                type="date"
                value={form.post_date}
                onChange={(e) => handleChange('post_date', e.target.value)}
                className={inputClass('post_date')}
              />
              {errors.post_date && <p className="text-xs text-destructive mt-1">{errors.post_date}</p>}
            </div>

            <div className="sm:col-span-2">
              <label className="text-xs font-medium text-muted-foreground block mb-1">URL de la publicación</label>
              <input
                type="url"
                value={form.post_url}
                onChange={(e) => handleChange('post_url', e.target.value)}
                placeholder="https://instagram.com/p/..."
                className={inputClass('post_url')}
              />
            </div>
          </div>

          <div className="border-t pt-4">
            <p className="text-xs font-medium text-muted-foreground mb-3">MÉTRICAS (al menos una requerida)</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Vistas</label>
                <input
                  type="number"
                  min="0"
                  value={form.views}
                  onChange={(e) => handleChange('views', e.target.value)}
                  placeholder="0"
                  className={inputClass('views')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Alcance</label>
                <input
                  type="number"
                  min="0"
                  value={form.alcance}
                  onChange={(e) => handleChange('alcance', e.target.value)}
                  placeholder="0"
                  className={inputClass('alcance')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Likes</label>
                <input
                  type="number"
                  min="0"
                  value={form.likes}
                  onChange={(e) => handleChange('likes', e.target.value)}
                  placeholder="0"
                  className={inputClass('likes')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Comentarios</label>
                <input
                  type="number"
                  min="0"
                  value={form.comments}
                  onChange={(e) => handleChange('comments', e.target.value)}
                  placeholder="0"
                  className={inputClass('comments')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Guardados</label>
                <input
                  type="number"
                  min="0"
                  value={form.saves}
                  onChange={(e) => handleChange('saves', e.target.value)}
                  placeholder="0"
                  className={inputClass('saves')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Compartidos</label>
                <input
                  type="number"
                  min="0"
                  value={form.shares}
                  onChange={(e) => handleChange('shares', e.target.value)}
                  placeholder="0"
                  className={inputClass('shares')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Seguidores</label>
                <input
                  type="number"
                  min="0"
                  value={form.followers}
                  onChange={(e) => handleChange('followers', e.target.value)}
                  placeholder="0"
                  className={inputClass('followers')}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">
                  Segundos totales de reproducción
                </label>
                <input
                  type="number"
                  min="0"
                  value={form.retention_seconds}
                  onChange={(e) => handleChange('retention_seconds', e.target.value)}
                  placeholder="0"
                  className={inputClass('retention_seconds')}
                />
                <p className="text-xs text-muted-foreground mt-0.5">El sistema divide ÷ vistas automáticamente</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">Plataforma</label>
              <select
                value={form.plataforma}
                onChange={(e) => handleChange('plataforma', e.target.value)}
                className={inputClass('plataforma')}
              >
                <option value="instagram">Instagram</option>
                <option value="tiktok">TikTok</option>
                <option value="youtube">YouTube</option>
                <option value="x">X / Twitter</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">Formato</label>
              <select
                value={form.formato}
                onChange={(e) => handleChange('formato', e.target.value)}
                className={inputClass('formato')}
              >
                <option value="reel">Reel</option>
                <option value="video">Video</option>
                <option value="story">Story</option>
                <option value="post">Post</option>
                <option value="carousel">Carousel</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={submitting} size="sm">
              {submitting ? (
                <>
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  Guardando...
                </>
              ) : (
                <>
                  <Plus className="w-3 h-3 mr-1" />
                  Agregar publicación
                </>
              )}
            </Button>
            {success && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle2 className="w-3 h-3" />
                Guardado
              </span>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
