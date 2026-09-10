import { apiFetch, tokenStore } from './http';
import type { TokenDto, User, UserDto } from '@/types/api';

const toUser = (dto: UserDto): User => ({
  id: dto.id,
  email: dto.email,
  fullName: dto.full_name,
  createdAt: new Date(dto.created_at),
});

export interface Credentials {
  email: string;
  password: string;
}

export interface RegisterPayload extends Credentials {
  fullName?: string;
}

export async function login(credentials: Credentials): Promise<string> {
  const dto = await apiFetch<TokenDto>('/auth/login', {
    method: 'POST',
    body: credentials,
    auth: false,
  });
  tokenStore.set(dto.access_token);
  return dto.access_token;
}

export async function register(payload: RegisterPayload): Promise<string> {
  const dto = await apiFetch<TokenDto>('/auth/register', {
    method: 'POST',
    body: {
      email: payload.email,
      password: payload.password,
      full_name: payload.fullName ?? null,
    },
    auth: false,
  });
  tokenStore.set(dto.access_token);
  return dto.access_token;
}

export async function me(): Promise<User> {
  return toUser(await apiFetch<UserDto>('/auth/me'));
}

export function logout(): void {
  tokenStore.clear();
}
