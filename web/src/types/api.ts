// ---------------------------------------------------------------------------
// DTOs: lo que devuelve la API tal cual (snake_case, fechas como string).
// Modelos de dominio: lo que consume la UI (camelCase, Date).
// La conversion se hace en services/, nunca en los componentes.
// ---------------------------------------------------------------------------

export interface UserDto {
  id: number;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface User {
  id: number;
  email: string;
  fullName: string | null;
  createdAt: Date;
}

export interface TokenDto {
  access_token: string;
  token_type: string;
}

export interface ItemDto {
  id: number;
  title: string;
  description: string | null;
  done: boolean;
  created_at: string;
  owner_id: number;
}

export interface Item {
  id: number;
  title: string;
  description: string | null;
  done: boolean;
  createdAt: Date;
  ownerId: number;
}

export interface HealthDto {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: string;
  ai_enabled: boolean;
}

export interface Health {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: string;
  aiEnabled: boolean;
}

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}
