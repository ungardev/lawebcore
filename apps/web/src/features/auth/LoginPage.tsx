import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { Button } from '@/components/ui/button';
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

  return (
    <main className="min-h-screen flex items-center justify-center relative overflow-hidden bg-background">
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,hsl(var(--brand-pink)/0.08),transparent_60%)]"
      />

      <Card className="relative w-full max-w-md mx-4 overflow-hidden shadow-elevated">
        <div aria-hidden="true" className="h-1 w-full bg-brand-gradient" />

        <div className="px-8 pt-10 pb-8">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-1 mb-3">
              <img
                src="/logo-laweb.png"
                alt="La Web Figital Agency"
                className="h-16 w-auto object-contain"
              />
            </div>
            <p className="text-eyebrow text-muted-foreground">
              P.I.A.R - LENS
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            {error && (
              <div
                role="alert"
                className="flex items-center gap-2.5 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive-foreground"
              >
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-semibold">
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
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-semibold">
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

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="w-4 h-4 rounded accent-primary"
                />
                <span className="font-medium">Recordarme</span>
              </label>
              <a
                href="#"
                onClick={(e) => e.preventDefault()}
                className="text-muted-foreground hover:text-foreground transition-colors font-medium"
              >
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            <Button
              type="submit"
              variant="gradient"
              size="lg"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Ingresando…
                </>
              ) : (
                'Ingresar'
              )}
            </Button>
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
