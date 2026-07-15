import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';

export function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  if (user) {
    const fromDashboard = window.location.search.includes('from=dashboard') ||
                         sessionStorage.getItem('auth_error') === 'true';
    if (!fromDashboard) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await signIn(email, password);
      navigate('/dashboard');
      toast.success('Bienvenido');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Error de autenticacion');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-subtle dark:bg-background p-4">
      <Card className="w-full max-w-md p-6 sm:p-8 shadow-elevated">
        <div className="text-center mb-8">
          <img
            src="/logo-laweb.png"
            alt="La Web Figital Agency"
            className="h-20 w-auto mx-auto mb-4 object-contain"
          />
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nombre.apellido@hacemosloquenosgusta.com"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Contrasena</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="********"
            />
          </div>

          <Button type="submit" variant="gradient" className="w-full" disabled={loading}>
            {loading ? 'Ingresando...' : 'Ingresar'}
          </Button>
        </form>

        <p className="text-xs text-center text-muted-foreground mt-6">
          v0.1.0 - La Web Figital Agency - Venezuela
        </p>
      </Card>
    </div>
  );
}
