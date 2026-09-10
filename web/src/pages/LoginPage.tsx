import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2Icon } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useLocation, useNavigate } from 'react-router';
import { toast } from 'sonner';
import { z } from 'zod';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';

const esquema = z.object({
  email: z.email('Escribe un correo valido'),
  password: z.string().min(8, 'La contrasena debe tener al menos 8 caracteres'),
  fullName: z.string().max(120, 'Maximo 120 caracteres').optional(),
});

type ValoresFormulario = z.infer<typeof esquema>;

export function LoginPage() {
  const [modo, setModo] = useState<'login' | 'register'>('login');
  const { login, register: registrar } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = (location.state as { from?: string } | null)?.from ?? '/items';

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ValoresFormulario>({
    resolver: zodResolver(esquema),
    defaultValues: { email: '', password: '', fullName: '' },
  });

  const [errorApi, setErrorApi] = useState<string | null>(null);

  const enviar = handleSubmit(async (valores) => {
    setErrorApi(null);
    try {
      if (modo === 'login') {
        await login({ email: valores.email, password: valores.password });
        toast.success('Sesion iniciada');
      } else {
        await registrar({
          email: valores.email,
          password: valores.password,
          fullName: valores.fullName?.trim() || undefined,
        });
        toast.success('Cuenta creada');
      }
      navigate(destino, { replace: true });
    } catch (error) {
      setErrorApi(error instanceof Error ? error.message : 'No se pudo completar la operacion');
    }
  });

  const usarUsuarioDemo = () => {
    setValue('email', 'demo@demo.com');
    setValue('password', 'demo1234');
    setModo('login');
  };

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>{modo === 'login' ? 'Iniciar sesion' : 'Crear cuenta'}</CardTitle>
          <CardDescription>
            {modo === 'login'
              ? 'Entra para ver las secciones protegidas.'
              : 'La contrasena se guarda con hash Argon2, nunca en texto plano.'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="space-y-4" onSubmit={(evento) => void enviar(evento)} noValidate>
            {modo === 'register' && (
              <div className="space-y-2">
                <Label htmlFor="fullName">Nombre completo (opcional)</Label>
                <Input id="fullName" autoComplete="name" {...register('fullName')} />
                {errors.fullName && (
                  <p className="text-sm text-destructive">{errors.fullName.message}</p>
                )}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Correo</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                aria-invalid={Boolean(errors.email)}
                {...register('email')}
              />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Contrasena</Label>
              <Input
                id="password"
                type="password"
                autoComplete={modo === 'login' ? 'current-password' : 'new-password'}
                aria-invalid={Boolean(errors.password)}
                {...register('password')}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            {errorApi && (
              <Alert variant="destructive">
                <AlertDescription>{errorApi}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting && <Loader2Icon className="animate-spin" />}
              {modo === 'login' ? 'Entrar' : 'Registrarme'}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="flex-col items-start gap-2 text-sm">
          <button
            type="button"
            className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            onClick={() => {
              setErrorApi(null);
              setModo(modo === 'login' ? 'register' : 'login');
            }}
          >
            {modo === 'login' ? 'No tengo cuenta, quiero registrarme' : 'Ya tengo cuenta'}
          </button>
          <button
            type="button"
            className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            onClick={usarUsuarioDemo}
          >
            Usar el usuario de demo (requiere haber corrido pnpm run seed)
          </button>
        </CardFooter>
      </Card>
    </div>
  );
}
