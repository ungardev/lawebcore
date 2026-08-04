import { useState } from 'react'
import {
  Camera,
  Check,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Dumbbell,
  Film,
  Flame,
  GraduationCap,
  Heart,
  Home,
  Loader2,
  MapPin,
  Music2,
  PawPrint,
  Plane,
  PlayCircle,
  Shirt,
  Sparkles,
  TrendingUp,
  Trophy,
  UtensilsCrossed,
  Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Slider } from '@/components/ui/slider'
import { Textarea } from '@/components/ui/textarea'
import { HashtagChips } from './HashtagChips'
import { CityChips } from './CityChips'
import { FileUploadZone } from './FileUploadZone'
import type { BriefStructured, AudienceGender, Platform } from '../types/discovery'

const INDUSTRIES = [
  { value: 'mascotas', label: 'Mascotas', icon: <PawPrint className="h-4 w-4" /> },
  { value: 'belleza', label: 'Belleza', icon: <Sparkles className="h-4 w-4" /> },
  { value: 'food', label: 'Food & Restaurants', icon: <UtensilsCrossed className="h-4 w-4" /> },
  { value: 'moda', label: 'Moda', icon: <Shirt className="h-4 w-4" /> },
  { value: 'fitness', label: 'Fitness & Health', icon: <Dumbbell className="h-4 w-4" /> },
  { value: 'tecnologia', label: 'Tecnología', icon: <Cpu className="h-4 w-4" /> },
  { value: 'turismo', label: 'Turismo', icon: <Plane className="h-4 w-4" /> },
  { value: 'entretenimiento', label: 'Entretenimiento', icon: <Film className="h-4 w-4" /> },
  { value: 'educacion', label: 'Educación', icon: <GraduationCap className="h-4 w-4" /> },
  { value: 'finanzas', label: 'Finanzas', icon: <TrendingUp className="h-4 w-4" /> },
  { value: 'hogar', label: 'Hogar', icon: <Home className="h-4 w-4" /> },
  { value: 'deportes', label: 'Deportes', icon: <Trophy className="h-4 w-4" /> },
]

const NICHE_PRESETS: Record<string, string[]> = {
  mascotas: ['mascotas', 'perros', 'gatos', 'pet care', 'adopcion', 'rescate animal'],
  belleza: ['makeup', 'skincare', 'haircare', 'nails', 'beauty blogger'],
  food: ['foodie', 'recetas', 'cocina', 'restaurantes', 'comida saludable'],
  moda: ['fashion', 'streetwear', 'outfits', 'estilo'],
  fitness: ['gym', 'workout', 'healthy', 'running'],
  tecnologia: ['tech', 'gadgets', 'apps', 'coding'],
  turismo: ['travel', 'viajes', 'hoteles', 'experiencias'],
}

const COUNTRIES = [
  { value: 'VE', label: 'Venezuela' },
  { value: 'CO', label: 'Colombia' },
  { value: 'MX', label: 'México' },
  { value: 'AR', label: 'Argentina' },
  { value: 'CL', label: 'Chile' },
  { value: 'EC', label: 'Ecuador' },
  { value: 'PE', label: 'Perú' },
  { value: 'PA', label: 'Panamá' },
  { value: 'DO', label: 'Rep. Dominicana' },
  { value: 'US', label: 'EE.UU. (Hispanos)' },
]

const VENEZUELA_STATES = [
  { value: 'Distrito Capital', label: 'Distrito Capital' },
  { value: 'Miranda', label: 'Miranda' },
  { value: 'Carabobo', label: 'Carabobo' },
  { value: 'Aragua', label: 'Aragua' },
  { value: 'Lara', label: 'Lara' },
  { value: 'Tachira', label: 'Táchira' },
  { value: 'Zulia', label: 'Zulia' },
  { value: 'Anzoategui', label: 'Anzoátegui' },
  { value: 'Bolivar', label: 'Bolívar' },
  { value: 'Monagas', label: 'Monagas' },
  { value: 'Sucre', label: 'Sucre' },
  { value: 'Merida', label: 'Mérida' },
  { value: 'Barinas', label: 'Barinas' },
  { value: 'Portuguesa', label: 'Portuguesa' },
  { value: 'Guárico', label: 'Guárico' },
  { value: 'Cojedes', label: 'Cojedes' },
  { value: 'Trujillo', label: 'Trujillo' },
  { value: 'Yaracuy', label: 'Yaracuy' },
  { value: 'Falcón', label: 'Falcón' },
  { value: 'Vargas', label: 'Vargas' },
  { value: 'Amazonas', label: 'Amazonas' },
  { value: 'Apure', label: 'Apure' },
  { value: 'Delta Amacuro', label: 'Delta Amacuro' },
]

const PLATFORMS: { value: Platform; label: string; icon: React.ReactNode }[] = [
  { value: 'instagram', label: 'Instagram', icon: <Camera className="h-6 w-6" /> },
  { value: 'tiktok', label: 'TikTok', icon: <Music2 className="h-6 w-6" /> },
  { value: 'youtube', label: 'YouTube', icon: <PlayCircle className="h-6 w-6" /> },
]

const TONES = [
  { value: 'emocional', label: 'Emocional' },
  { value: 'informativo', label: 'Informativo' },
  { value: 'aspiracional', label: 'Aspiracional' },
  { value: 'humor', label: 'Humor' },
  { value: 'educativo', label: 'Educativo' },
  { value: 'familiar', label: 'Familiar' },
  { value: 'auténtico', label: 'Auténtico' },
]

const STEPS = [
  { id: 1, label: 'Producto' },
  { id: 2, label: 'Nicho' },
  { id: 3, label: 'Audiencia' },
  { id: 4, label: 'Hashtags' },
  { id: 5, label: 'Plataformas' },
  { id: 6, label: 'Revisar' },
]

type SubmitCallback = (_: Partial<BriefStructured>) => void
interface BriefWizardProps {
  onSubmit: SubmitCallback
  onCancel: () => void
  initialBrief?: Partial<BriefStructured>
  isSubmitting?: boolean
}

function createEmptyBrief(): Partial<BriefStructured> {
  return {
    product_name: null,
    industry: null,
    niches: [],
    hashtags: [],
    audience_gender: 'all',
    audience_age_min: 25,
    audience_age_max: 45,
    audience_countries: [],
    audience_cities: [],
    audience_states: [],
    platforms: ['instagram'],
    tone: [],
    additional_context: '',
  }
}

export function BriefWizard({
  onSubmit,
  onCancel,
  initialBrief,
  isSubmitting = false,
}: BriefWizardProps) {
  const [step, setStep] = useState(1)
  const [brief, setBrief] = useState<Partial<BriefStructured>>(initialBrief ?? createEmptyBrief())
  const [customNiche, setCustomNiche] = useState('')
  const [extractedBrief, setExtractedBrief] = useState<BriefStructured | null>(null)
  const [extractedFileName, setExtractedFileName] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const update = (patch: Partial<BriefStructured>) => setBrief((prev) => ({ ...prev, ...patch }))

  const handleBriefExtracted = (extracted: BriefStructured, fileName: string) => {
    setExtractedBrief(extracted)
    setExtractedFileName(fileName)
    setIsUploading(false)
    const mapped: Partial<BriefStructured> = {
      product_name: extracted.product_name,
      brand_name: extracted.brand_name,
      industry: extracted.industry,
      niches: extracted.niches ?? [],
      hashtags: extracted.hashtags ?? [],
      audience_gender: extracted.audience_gender ?? 'all',
      audience_age_min: extracted.audience_age_min ?? 25,
      audience_age_max: extracted.audience_age_max ?? 45,
      audience_countries: extracted.audience_countries ?? ['VE'],
      audience_cities: extracted.audience_cities ?? [],
      audience_states: (extracted as any).audience_states ?? [],
      platforms: extracted.platforms ?? ['instagram'],
      tone: extracted.tone ?? [],
      additional_context: extracted.additional_context ?? '',
    }
    setBrief((prev) => ({ ...prev, ...mapped }))
  }

  const handleClearUpload = () => {
    setExtractedBrief(null)
    setExtractedFileName(null)
    setIsUploading(false)
  }

  const canNext = () => {
    switch (step) {
      case 1:
        return !!brief.product_name || !!brief.industry
      case 2:
        return true
      case 3:
        return true
      case 4:
        return true
      case 5:
        return brief.platforms && brief.platforms.length > 0
      case 6:
        return !isSubmitting
      default:
        return true
    }
  }

  const handleSubmit = () => {
    onSubmit({
      ...brief,
      ...(extractedBrief
        ? {
            campaign_objective: extractedBrief.campaign_objective,
            budget_usd: extractedBrief.budget_usd,
            budget_currency: extractedBrief.budget_currency,
            kpis: extractedBrief.kpis,
            campaign_dates: extractedBrief.campaign_dates,
            key_themes: extractedBrief.key_themes,
            competitor_brands: extractedBrief.competitor_brands,
            influencer_preferences: extractedBrief.influencer_preferences,
            brief_source: extractedBrief.brief_source,
            source_document: extractedBrief.source_document,
          }
        : {}),
      platforms: (brief.platforms?.length ?? 0) > 0 ? brief.platforms : ['instagram'],
    })
  }

  const addNiche = (niche: string) => {
    if (niche && !brief.niches?.includes(niche)) {
      update({ niches: [...(brief.niches ?? []), niche] })
    }
    setCustomNiche('')
  }

  const removeNiche = (niche: string) => {
    update({ niches: (brief.niches ?? []).filter((n) => n !== niche) })
  }

  const toggleCountry = (country: string) => {
    const current = brief.audience_countries ?? []
    if (current.includes(country)) {
      update({ audience_countries: current.filter((c) => c !== country) })
    } else {
      update({ audience_countries: [...current, country] })
    }
  }

  const togglePlatform = (platform: Platform) => {
    const current = brief.platforms ?? []
    if (current.includes(platform)) {
      update({ platforms: current.filter((p) => p !== platform) })
    } else {
      update({ platforms: [...current, platform] })
    }
  }

  const toggleTone = (tone: string) => {
    const current = brief.tone ?? []
    if (current.includes(tone)) {
      update({ tone: current.filter((t) => t !== tone) })
    } else {
      update({ tone: [...current, tone] })
    }
  }

  return (
    <div className="space-y-4">
      <div className="border-b border-divider px-5 pb-4 pt-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-eyebrow text-muted-foreground">Nueva búsqueda / configuración</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground">
              Construye el brief de discovery
            </h2>
          </div>
          <span className="font-mono text-xs text-muted-foreground">0{step} / 06</span>
        </div>
        <div className="mt-4 grid grid-cols-6 gap-1" aria-label="Progreso del brief">
          {STEPS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setStep(s.id)}
              disabled={isSubmitting || s.id > step + 1}
              aria-current={step === s.id ? 'step' : undefined}
              aria-label={`Paso ${s.id}: ${s.label}`}
              className={cn(
                'h-1.5 rounded-full transition-colors focus-ring disabled:cursor-not-allowed',
                step === s.id ? 'bg-primary' : s.id < step ? 'bg-success' : 'bg-surface-raised',
              )}
            />
          ))}
        </div>
        <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
          <span>{STEPS[step - 1]?.label}</span>
          <span>
            {step === STEPS.length
              ? 'Listo para ejecutar'
              : 'Puedes volver a cualquier paso anterior'}
          </span>
        </div>
      </div>

      <Card className="mx-5 my-4 border-divider bg-surface-sunken p-5 shadow-none">
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <Label className="mb-1.5 block">Sube tu brief (PDF/TXT/CSV)</Label>
              <FileUploadZone
                onBriefExtracted={handleBriefExtracted}
                onClear={handleClearUpload}
                isLoading={isUploading}
                onLoadingChange={setIsUploading}
                extractedBrief={extractedBrief}
                extractedFileName={extractedFileName}
              />
            </div>
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">o completa manualmente</span>
              </div>
            </div>
            <div>
              <Label className="mb-1.5 block">Producto o marca *</Label>
              <Input
                placeholder="Ej: Shampoo Dove, Restaurant Plaza, App fintech"
                value={brief.product_name ?? ''}
                onChange={(e) => update({ product_name: e.target.value || null })}
              />
            </div>
            <div>
              <Label className="mb-1.5 block">Industria *</Label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {INDUSTRIES.map((ind) => (
                  <button
                    key={ind.value}
                    type="button"
                    onClick={() =>
                      update({ industry: ind.value, niches: NICHE_PRESETS[ind.value] ?? [] })
                    }
                    className={cn(
                      'min-h-11 rounded-md border px-3 py-2 text-left text-xs transition-colors focus-ring flex items-center gap-2',
                      brief.industry === ind.value
                        ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                        : 'border-divider hover:border-primary/40 hover:bg-surface-raised',
                    )}
                  >
                    {ind.icon}
                    <span>{ind.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <Label className="mb-1.5 block"> nichos detectados automáticamente</Label>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {(brief.niches ?? []).map((n) => (
                  <span
                    key={n}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-brand-purple/10 text-brand-purple text-xs font-medium border border-brand-purple/20"
                  >
                    {n}
                    <button
                      type="button"
                      onClick={() => removeNiche(n)}
                      className="hover:bg-brand-purple/20 rounded-full p-0.5"
                    >
                      <Check className="w-2.5 h-2.5" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Agregar nicho..."
                  value={customNiche}
                  onChange={(e) => setCustomNiche(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      addNiche(customNiche)
                    }
                  }}
                  className="flex-1"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => addNiche(customNiche)}
                >
                  Agregar
                </Button>
              </div>
            </div>
            {brief.industry && NICHE_PRESETS[brief.industry] && (
              <div>
                <Label className="mb-1.5 block text-muted-foreground">
                  Sugeridos para {brief.industry}
                </Label>
                <div className="flex flex-wrap gap-1.5">
                  {NICHE_PRESETS[brief.industry]!.filter((n) => !brief.niches?.includes(n)).map(
                    (n) => (
                      <button
                        key={n}
                        type="button"
                        onClick={() => addNiche(n)}
                        className="px-2.5 py-1 rounded-full bg-muted hover:bg-brand-purple/10 text-xs border border-border hover:border-brand-purple/30 transition-colors"
                      >
                        + {n}
                      </button>
                    ),
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <div>
              <Label className="mb-2 block">Género objetivo</Label>
              <div className="flex gap-2">
                {(
                  [
                    { value: 'female', label: 'Female' },
                    { value: 'male', label: 'Male' },
                    { value: 'all', label: 'Todos' },
                  ] as { value: AudienceGender; label: string }[]
                ).map((g) => (
                  <button
                    key={g.value}
                    type="button"
                    onClick={() => update({ audience_gender: g.value })}
                    className={cn(
                      'min-h-11 flex-1 rounded-md border text-xs font-medium transition-colors focus-ring',
                      brief.audience_gender === g.value
                        ? 'border-primary/50 bg-primary/10 text-primary'
                        : 'border-divider hover:bg-surface-raised',
                    )}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label className="mb-2 block">
                Rango de edad: {brief.audience_age_min} – {brief.audience_age_max} años
              </Label>
              <div className="flex gap-4">
                <Slider
                  min={13}
                  max={65}
                  value={brief.audience_age_min ?? 25}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10)
                    update({ audience_age_min: Math.min(val, (brief.audience_age_max ?? 65) - 1) })
                  }}
                  aria-label="Edad mínima"
                />
                <Slider
                  min={13}
                  max={65}
                  value={brief.audience_age_max ?? 45}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10)
                    update({ audience_age_max: Math.max(val, (brief.audience_age_min ?? 13) + 1) })
                  }}
                  aria-label="Edad máxima"
                />
              </div>
            </div>

            <div>
              <Label className="mb-2 block">Países</Label>
              <div className="flex flex-wrap gap-2">
                {COUNTRIES.map((c) => (
                  <button
                    key={c.value}
                    type="button"
                    onClick={() => toggleCountry(c.value)}
                    className={cn(
                      'px-3 py-1.5 rounded-full border text-xs transition-colors',
                      brief.audience_countries?.includes(c.value)
                        ? 'border-brand-purple bg-brand-purple/5 text-brand-purple font-medium'
                        : 'border-border hover:bg-muted text-muted-foreground',
                    )}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label className="mb-1.5 block">Ciudades (opcional)</Label>
              <CityChips
                cities={brief.audience_cities ?? []}
                onChange={(cities) => update({ audience_cities: cities })}
                placeholder="Ej: Caracas, Bogotá, CDMX..."
              />
            </div>

            {brief.audience_countries?.includes('VE') && (
              <div>
                <Label className="mb-1.5 block">Estados (opcional){' '}
                  <span className="text-xs font-normal text-muted-foreground">
                    Filtra candidatos por estado específico de Venezuela
                  </span>
                </Label>
                <div className="flex flex-wrap gap-2">
                  {VENEZUELA_STATES.map((s) => {
                    const isSelected = brief.audience_states?.includes(s.value)
                    return (
                      <button
                        key={s.value}
                        type="button"
                        onClick={() => {
                          const current = brief.audience_states ?? []
                          if (isSelected) {
                            update({ audience_states: current.filter((x) => x !== s.value) })
                          } else {
                            update({ audience_states: [...current, s.value] })
                          }
                        }}
                        className={cn(
                          'px-3 py-1.5 rounded-full border text-xs transition-colors',
                          isSelected
                            ? 'border-brand-pink bg-brand-pink/5 text-brand-pink font-medium'
                            : 'border-border hover:bg-muted text-muted-foreground',
                        )}
                      >
                        {s.label}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <div>
              <Label className="mb-1.5 block">
                Hashtags personalizados{brief.industry ? ` · Vertical: ${brief.industry}` : ''}
              </Label>
              <HashtagChips
                hashtags={brief.hashtags ?? []}
                onChange={(hashtags) => update({ hashtags })}
                industry={brief.industry}
              />
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4">
            <div>
              <Label className="mb-2 block">Plataformas</Label>
              <div className="flex gap-3">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => togglePlatform(p.value)}
                    className={cn(
                      'flex-1 flex flex-col items-center gap-2 py-4 rounded-xl border text-sm font-medium transition-colors',
                      brief.platforms?.includes(p.value)
                        ? 'border-brand-purple bg-brand-purple/5 text-brand-purple'
                        : 'border-border hover:bg-muted',
                    )}
                  >
                    {p.icon}
                    <span className="text-xs mt-1">{p.label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label className="mb-2 block">Tono de comunicación</Label>
              <div className="flex flex-wrap gap-2">
                {TONES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => toggleTone(t.value)}
                    className={cn(
                      'px-3 py-1.5 rounded-full border text-xs transition-colors',
                      brief.tone?.includes(t.value)
                        ? 'border-brand-purple bg-brand-purple/5 text-brand-purple font-medium'
                        : 'border-border hover:bg-muted text-muted-foreground',
                    )}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label className="mb-1.5 block">Contexto adicional (opcional)</Label>
              <Textarea
                rows={3}
                placeholder="Ej: Solo creadoras de contenido individuales, NO tiendas..."
                value={brief.additional_context ?? ''}
                onChange={(e) => update({ additional_context: e.target.value })}
              />
            </div>
          </div>
        )}

        {step === 6 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-brand-purple" />
              <span className="text-sm font-semibold text-foreground">Resumen del Brief</span>
              {extractedBrief && (
                <span className="ml-auto max-w-[12rem] truncate rounded border border-success/30 bg-success/10 px-2 py-1 text-xs text-success">
                  Fuente: {extractedFileName}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
              {brief.product_name && (
                <div>
                  <span className="text-muted-foreground">Producto:</span>{' '}
                  <span className="font-medium">{brief.product_name}</span>
                </div>
              )}
              {brief.industry && (
                <div>
                  <span className="text-muted-foreground">Industria:</span>{' '}
                  <span className="font-medium">{brief.industry}</span>
                </div>
              )}
              {brief.niches && brief.niches.length > 0 && (
                <div>
                  <span className="text-muted-foreground">Nichos:</span>{' '}
                  <span className="font-medium">{brief.niches.join(', ')}</span>
                </div>
              )}
              <div>
                <span className="text-muted-foreground">Audiencia:</span>{' '}
                <span className="font-medium">
                  {brief.audience_gender === 'female'
                    ? 'Mujeres'
                    : brief.audience_gender === 'male'
                      ? 'Hombres'
                      : 'Todos'}
                  {` ${brief.audience_age_min}-${brief.audience_age_max} años`}
                </span>
              </div>
              {brief.audience_countries && brief.audience_countries.length > 0 && (
                <div>
                  <span className="text-muted-foreground">Países:</span>{' '}
                  <span className="font-medium">{brief.audience_countries.join(', ')}</span>
                </div>
              )}
              {brief.hashtags && brief.hashtags.length > 0 && (
                <div>
                  <span className="text-muted-foreground">Hashtags:</span>{' '}
                  <span className="font-medium">{brief.hashtags.length} agregados</span>
                </div>
              )}
              {brief.platforms && brief.platforms.length > 0 && (
                <div>
                  <span className="text-muted-foreground">Plataformas:</span>{' '}
                  <span className="font-medium">{brief.platforms.join(', ')}</span>
                </div>
              )}
              {extractedBrief && extractedBrief.campaign_objective && (
                <div>
                  <span className="text-muted-foreground">Objetivo:</span>{' '}
                  <span className="font-medium">{extractedBrief.campaign_objective}</span>
                </div>
              )}
              {extractedBrief && extractedBrief.budget_usd && (
                <div>
                  <span className="text-muted-foreground">Budget:</span>{' '}
                  <span className="font-medium">
                    ${extractedBrief.budget_usd.toLocaleString()}{' '}
                    {extractedBrief.budget_currency ?? 'USD'}
                  </span>
                </div>
              )}
              {extractedBrief && extractedBrief.kpis && extractedBrief.kpis.length > 0 && (
                <div>
                  <span className="text-muted-foreground">KPIs:</span>{' '}
                  <span className="font-medium">{extractedBrief.kpis.join(', ')}</span>
                </div>
              )}
              {extractedBrief &&
                extractedBrief.key_themes &&
                extractedBrief.key_themes.length > 0 && (
                  <div>
                    <span className="text-muted-foreground">Temas clave:</span>{' '}
                    <span className="font-medium">
                      {extractedBrief.key_themes.slice(0, 3).join(', ')}
                    </span>
                  </div>
                )}
              {extractedBrief &&
                extractedBrief.competitor_brands &&
                extractedBrief.competitor_brands.length > 0 && (
                  <div>
                    <span className="text-muted-foreground">Competencia:</span>{' '}
                    <span className="font-medium">
                      {extractedBrief.competitor_brands.slice(0, 2).join(', ')}
                    </span>
                  </div>
                )}
              {extractedBrief &&
                extractedBrief.influencer_preferences &&
                (() => {
                  const pref = extractedBrief.influencer_preferences as Record<string, unknown>
                  const tiers = pref?.tiers
                  return (
                    <div>
                      <span className="text-muted-foreground">Tiers:</span>{' '}
                      <span className="font-medium">
                        {Array.isArray(tiers) ? tiers.join(', ') : null}
                      </span>
                    </div>
                  )
                })()}
            </div>
            {brief.additional_context && (
              <p className="text-xs text-muted-foreground italic border-t pt-2 mt-2">
                "{brief.additional_context}"
              </p>
            )}
          </div>
        )}

        <div className="flex justify-between border-t border-divider px-5 pb-5 pt-4">
          {step > 1 ? (
            <Button type="button" variant="outline" size="sm" onClick={() => setStep(step - 1)}>
              <ChevronLeft className="w-4 h-4 mr-1" />
              Atrás
            </Button>
          ) : (
            <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
              Cancelar
            </Button>
          )}

          {step < 6 ? (
            <Button
              type="button"
              size="sm"
              onClick={() => setStep(step + 1)}
              disabled={!canNext()}
              className="gap-1"
            >
              Siguiente
              <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={handleSubmit}
              className="min-w-40 gap-2"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Sparkles className="h-4 w-4" aria-hidden="true" />
              )}
              {isSubmitting ? 'Iniciando…' : 'Buscar candidatos'}
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
