import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { Eye, EyeOff, AlertCircle, Loader2 } from 'lucide-react';

export interface LoginPageProps {
  onSubmit?: (values: { email: string; password: string; remember: boolean }) => Promise<void> | void;
  isLoading?: boolean;
  error?: string | null;
  version?: string;
}

export function LoginPage({
  onSubmit: onSubmitProp,
  isLoading: isLoadingProp,
  error: errorProp,
  version = 'v0.1.0',
}: LoginPageProps) {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const isLoading = isLoadingProp ?? localLoading;
  const error = errorProp ?? localError;

  if (user) {
    const fromDashboard =
      window.location.search.includes('from=dashboard') ||
      sessionStorage.getItem('auth_error') === 'true';
    if (!fromDashboard) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (onSubmitProp) {
      await onSubmitProp({ email, password, remember });
      return;
    }

    setLocalLoading(true);
    try {
      await signIn(email, password);
      navigate('/dashboard');
      toast.success('Bienvenido');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error de autenticacion';
      setLocalError(msg);
      toast.error(msg);
    } finally {
      setLocalLoading(false);
    }
  };

  const BRAND_PINK = '#ec4899';
  const BRAND_PURPLE = '#a855f7';
  const BRAND_BLUE = '#3b82f6';
  const GRADIENT = `linear-gradient(135deg, ${BRAND_PINK} 0%, ${BRAND_PURPLE} 50%, ${BRAND_BLUE} 100%)`;

  return (
    <main
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{ fontFamily: 'Montserrat, ui-sans-serif, system-ui, sans-serif' }}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 80% 60% at 20% 20%, ${BRAND_PINK}22 0%, transparent 60%),
            radial-gradient(ellipse 70% 50% at 80% 80%, ${BRAND_BLUE}22 0%, transparent 60%)
          `,
          filter: 'blur(120px)',
        }}
      />

      <Card
        className="relative w-full max-w-md mx-4 rounded-2xl overflow-hidden"
        style={{
          border: '1px solid hsl(var(--border))',
          boxShadow: '0 20px 60px -20px rgba(15, 23, 42, 0.18)',
        }}
      >
        <div
          aria-hidden="true"
          className="w-full h-1"
          style={{ background: GRADIENT }}
        />

        <div className="px-8 pt-10 pb-8">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-1 mb-3">
              <img
                src="/logo-laweb.png"
                alt="La Web Figital Agency"
                className="h-16 w-auto object-contain"
              />
            </div>
            <p
              className="text-sm text-muted-foreground uppercase"
              style={{ letterSpacing: '0.28em', fontWeight: 600 }}
            >
              Influencer Strategist & Manager
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            noValidate
            className="space-y-5"
          >
            {error && (
              <div
                role="alert"
                className="flex items-center gap-2.5 rounded-lg px-4 py-3 text-sm"
                style={{
                  background: 'hsl(var(--destructive) / 0.12)',
                  border: '1px solid hsl(var(--destructive) / 0.4)',
                  color: 'hsl(var(--destructive-foreground))',
                }}
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                Email
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={!!error}
                style={{ borderRadius: '8px' }}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                Contraseña
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={!!error}
                  className="pr-10"
                  style={{ borderRadius: '8px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between" style={{ fontSize: '0.875rem' }}>
              <label className="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="w-4 h-4 rounded"
                  style={{ accentColor: BRAND_PINK }}
                />
                <span style={{ fontWeight: 500 }}>Recordarme</span>
              </label>
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="text-muted-foreground hover:text-foreground transition-colors"
                style={{ fontWeight: 500 }}
              >
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-11 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              style={{
                background: GRADIENT,
                boxShadow: '0 10px 30px -10px rgba(236, 72, 153, 0.5)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 14px 36px -10px rgba(59, 130, 246, 0.55)';
                e.currentTarget.style.filter = 'brightness(1.08)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = '0 10px 30px -10px rgba(236, 72, 153, 0.5)';
                e.currentTarget.style.filter = 'none';
              }}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Ingresando…</span>
                </>
              ) : (
                <span>Ingresar</span>
              )}
            </button>
          </form>
        </div>

        <div className="px-8 pb-6 text-center">
          <p className="text-xs text-muted-foreground">
            {version} · La Web Figital Agency · Venezuela
          </p>
        </div>
      </Card>
    </main>
  );
}
