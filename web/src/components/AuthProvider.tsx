import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { AuthContext } from '@/hooks/useAuth';
import type { AuthContextValue } from '@/hooks/useAuth';
import * as authService from '@/services/authService';
import type { Credentials, RegisterPayload } from '@/services/authService';
import { setUnauthorizedHandler, tokenStore } from '@/services/http';
import type { User } from '@/types/api';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Solo hay algo que validar si quedo un token de una sesion anterior.
  const [isLoading, setIsLoading] = useState(() => tokenStore.get() !== null);

  // Cualquier 401 de la API cierra la sesion en el cliente.
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  // Al arrancar, si hay token guardado lo validamos contra /auth/me.
  useEffect(() => {
    if (!tokenStore.get()) return;

    let activo = true;
    authService
      .me()
      .then((usuario) => {
        if (activo) setUser(usuario);
      })
      .catch(() => {
        authService.logout();
      })
      .finally(() => {
        if (activo) setIsLoading(false);
      });

    return () => {
      activo = false;
    };
  }, []);

  const login = useCallback(async (credentials: Credentials) => {
    await authService.login(credentials);
    setUser(await authService.me());
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await authService.register(payload);
    setUser(await authService.me());
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, isAuthenticated: user !== null, login, register, logout }),
    [user, isLoading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
