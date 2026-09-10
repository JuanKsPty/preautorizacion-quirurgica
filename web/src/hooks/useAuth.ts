import { createContext, useContext } from 'react';
import type { Credentials, RegisterPayload } from '@/services/authService';
import type { User } from '@/types/api';

export interface AuthContextValue {
  user: User | null;
  /** true mientras se valida el token guardado al cargar la app. */
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: Credentials) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth se debe usar dentro de <AuthProvider>');
  }
  return context;
}
