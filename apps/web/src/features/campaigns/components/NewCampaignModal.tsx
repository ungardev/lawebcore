import { useState, useEffect } from 'react';
import { X, Plus, Loader2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { campaignsApi, brandsApi, clientsApi } from '@/lib/api';
import { ProjectionPanel } from '@/features/projections/ProjectionPanel';
import { Brand } from '@/types';
import { Client } from '@/types';
import { toast } from 'sonner';

interface NewCampaignModalProps {
  open: boolean;
  onClose: () => void;
}

const OBJECTIVES = [
  { value: 'AWARENESS', label: 'Awareness' },
  { value: 'CONSIDERACION', label: 'Consideración' },
  { value: 'CONVERSION', label: 'Conversión' },
  { value: 'BRANDING', label: 'Branding' },
  { value: 'LANZAMIENTO', label: 'Lanzamiento' },
  { value: 'RETENCION', label: 'Retención' },
  { value: 'GESTION_DE_CRISIS', label: 'Gestión de Crisis' },
];

const TIERS = ['NANO', 'MICRO', 'MID', 'MACRO', 'MEGA'] as const;

export function NewCampaignModal({ open, onClose }: NewCampaignModalProps) {
  const qc = useQueryClient();
  const [step, setStep] = useState<'form' | 'projection'>('form');
  const [selectedBrand, setSelectedBrand] = useState<Brand | null>(null);

  const [name, setName] = useState('');
  const [objective, setObjective] = useState('AWARENESS');
  const [selectedTiers, setSelectedTiers] = useState<string[]>(['NANO']);
  const [budget, setBudget] = useState('');
  const [numInfluencers, setNumInfluencers] = useState('0');

  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.list(),
    enabled: open,
  });

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => clientsApi.list(),
    enabled: open,
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => campaignsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Campaña creada');
      onClose();
      resetForm();
    },
    onError: () => toast.error('Error creando campaña'),
  });

  const resetForm = () => {
    setName('');
    setObjective('AWARENESS');
    setSelectedTiers(['NANO']);
    setBudget('');
    setNumInfluencers('0');
    setSelectedBrand(null);
    setStep('form');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const clientMap = new Map((clients || []).map((c: Client) => [c.id, c]));

  const handleSubmit = () => {
    if (!name.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    if (!selectedBrand) {
      toast.error('Selecciona una marca');
      return;
    }
    if (selectedTiers.length === 0) {
      toast.error('Selecciona al menos un tier');
      return;
    }
    setStep('projection');
  };

  const handleCreate = () => {
    const client = clientMap.get(selectedBrand!.client_id);
    createMutation.mutate({
      brand_id: selectedBrand!.id,
      client_id: selectedBrand!.client_id,
      name: name.trim(),
      objective,
      influencer_tiers: selectedTiers,
      num_influencers: parseInt(numInfluencers) || 0,
      budget_total: budget ? parseFloat(budget) : undefined,
    });
  };

  useEffect(() => {
    if (!open) resetForm();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      <div className="relative bg-background rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
        <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-background z-10">
          <div>
            <h2 className="text-lg font-bold">
              {step === 'form' ? 'Nueva Campaña' : 'Proyección P.I.A.R'}
            </h2>
            <p className="text-xs text-muted-foreground">
              {step === 'form' ? 'Paso 1 de 2: Datos de la campaña' : 'Paso 2 de 2: Proyecta antes de crear'}
            </p>
          </div>
          <button onClick={handleClose} className="p-2 hover:bg-accent rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {step === 'form' && (
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Marca *</Label>
                <select
                  value={selectedBrand?.id || ''}
                  onChange={(e) => {
                    const b = brands?.find((br: Brand) => br.id === e.target.value);
                    setSelectedBrand(b || null);
                  }}
                  className="w-full h-9 px-3 rounded-md border border-input bg-transparent text-sm"
                >
                  <option value="">Seleccionar marca...</option>
                  {brands?.map((b: Brand) => {
                    const client = clientMap.get(b.client_id);
                    return (
                      <option key={b.id} value={b.id}>
                        {b.name} ({client?.name || '—'})
                      </option>
                    );
                  })}
                </select>
              </div>

              <div className="space-y-2">
                <Label>Nombre de campaña *</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="#MiCampaña2026"
                />
              </div>

              <div className="space-y-2">
                <Label>Objetivo *</Label>
                <select
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  className="w-full h-9 px-3 rounded-md border border-input bg-transparent text-sm"
                >
                  {OBJECTIVES.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label>Budget (USD)</Label>
                <Input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="5000"
                  min={0}
                />
              </div>

              <div className="space-y-2">
                <Label># Influencers</Label>
                <Input
                  type="number"
                  value={numInfluencers}
                  onChange={(e) => setNumInfluencers(e.target.value)}
                  min={0}
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label>Tiers de influencers *</Label>
                <div className="flex flex-wrap gap-2">
                  {TIERS.map((tier) => (
                    <button
                      key={tier}
                      type="button"
                      onClick={() => {
                        if (selectedTiers.includes(tier)) {
                          if (selectedTiers.length > 1) {
                            setSelectedTiers(selectedTiers.filter((t) => t !== tier));
                          }
                        } else {
                          setSelectedTiers([...selectedTiers, tier]);
                        }
                      }}
                      className={`px-3 py-1.5 rounded-md text-sm border transition-all ${
                        selectedTiers.includes(tier)
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-card hover:bg-accent border-border'
                      }`}
                    >
                      {tier}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => setSelectedTiers([...TIERS])}
                    className="px-3 py-1.5 rounded-md text-sm border border-dashed border-muted-foreground/50 hover:bg-accent"
                  >
                    MIX
                  </button>
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={handleClose} className="flex-1">
                Cancelar
              </Button>
              <Button onClick={handleSubmit} className="flex-1">
                Siguiente: Proyección
              </Button>
            </div>
          </div>
        )}

        {step === 'projection' && selectedBrand && (
          <div className="p-4 space-y-4">
            <Card className="bg-muted/30">
              <CardContent className="p-3 text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Marca:</span>
                  <span className="font-medium">{selectedBrand.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Nombre:</span>
                  <span className="font-medium">{name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tiers:</span>
                  <div className="flex gap-1">
                    {selectedTiers.map((t) => (
                      <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <ProjectionPanel
              brandId={selectedBrand.id}
              brandName={selectedBrand.name}
            />

            <div className="flex gap-3 pt-2">
              <Button variant="outline" onClick={() => setStep('form')} className="flex-1">
                Volver
              </Button>
              <Button
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="flex-1"
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creando...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Crear campaña
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
