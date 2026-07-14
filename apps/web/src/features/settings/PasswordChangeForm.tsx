import { useState } from 'react';
import { Eye, EyeOff, Lock, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/features/auth/AuthProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function PasswordInput({
  id,
  label,
  value,
  onChange,
  error,
  placeholder = '',
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  placeholder?: string;
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium">
        {label}
      </Label>
      <div className="relative">
        <Input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="pr-10"
          aria-invalid={!!error}
        />
        <button
          type="button"
          onClick={() => setVisible(!visible)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          tabIndex={-1}
          aria-label={visible ? 'Ocultar contrasena' : 'Mostrar contrasena'}
        >
          {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      {error && (
        <p className="text-xs text-destructive flex items-center gap-1">
          <AlertCircle className="w-3 h-3" />
          {error}
        </p>
      )}
    </div>
  );
}

export function PasswordChangeForm() {
  const { updatePassword } = useAuth();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const [errors, setErrors] = useState<{
    current?: string;
    new?: string;
    confirm?: string;
  }>({});

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!currentPassword) {
      newErrors.current = 'Ingresa tu contrasena actual';
    }

    if (!newPassword) {
      newErrors.new = 'Ingresa una nueva contrasena';
    } else {
      if (newPassword.length < 8) {
        newErrors.new = 'Minimo 8 caracteres';
      }
      if (!/[a-zA-Z]/.test(newPassword)) {
        newErrors.new = newErrors.new
          ? 'Debe contener al menos una letra'
          : 'Debe contener al menos una letra y un numero';
      }
      if (!/[0-9]/.test(newPassword)) {
        const base = newErrors.new ? 'Debe contener al menos un numero' : undefined;
        if (base) newErrors.new = 'Debe contener al menos una letra y un numero';
      }
    }

    if (!confirmPassword) {
      newErrors.confirm = 'Confirma tu nueva contrasena';
    } else if (confirmPassword !== newPassword) {
      newErrors.confirm = 'Las contrasenas no coinciden';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    try {
      await updatePassword(currentPassword, newPassword);
      toast.success('Contrasena actualizada correctamente', {
        icon: <CheckCircle className="w-4 h-4" />,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setErrors({});
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al cambiar la contrasena';
      toast.error(message, {
        icon: <AlertCircle className="w-4 h-4" />,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Actualiza tu contrasena para mayor seguridad. La nueva contrasena debe tener al menos 8 caracteres.
      </p>

      <PasswordInput
        id="current-password"
        label="Contrasena actual"
        value={currentPassword}
        onChange={setCurrentPassword}
        error={errors.current}
        placeholder="Tu contrasena actual"
      />

      <PasswordInput
        id="new-password"
        label="Nueva contrasena"
        value={newPassword}
        onChange={setNewPassword}
        error={errors.new}
        placeholder="Nueva contrasena (min 8 caracteres)"
      />

      <PasswordInput
        id="confirm-password"
        label="Confirmar nueva contrasena"
        value={confirmPassword}
        onChange={setConfirmPassword}
        error={errors.confirm}
        placeholder="Repite la nueva contrasena"
      />

      <Button
        type="submit"
        disabled={loading}
        className="w-full"
      >
        {loading ? 'Cambiando...' : 'Cambiar contrasena'}
      </Button>
    </form>
  );
}
