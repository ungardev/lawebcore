import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useAuth } from '@/features/auth/AuthProvider';
import { PasswordChangeForm } from './PasswordChangeForm';

export function SettingsPage() {
  const { user } = useAuth();
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold">Configuracion</h1>
        <p className="text-muted-foreground">Tu cuenta y preferencias</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Perfil</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-muted-foreground">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-muted-foreground">ID</p>
              <p className="font-mono text-xs">{user?.id}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Creado</p>
              <p className="font-medium">{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Contraseña</CardTitle></CardHeader>
        <CardContent>
          <PasswordChangeForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Acerca de La Web Core</CardTitle></CardHeader>
        <CardContent className="text-sm space-y-2 text-muted-foreground">
          <p>Version: 0.1.0 (MVP)</p>
          <p>Stack: FastAPI + Railway Postgres + React + Vite + shadcn/ui</p>
          <p>La Web Figital Agency - Venezuela</p>
          <p className="pt-2 border-t mt-3">
            Producto interno para gestion integral de campañas de marketing, KPIs, operaciones e IA.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}