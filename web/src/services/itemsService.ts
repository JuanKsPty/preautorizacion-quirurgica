import { apiFetch } from './http';
import type { Item, ItemDto } from '@/types/api';

const toItem = (dto: ItemDto): Item => ({
  id: dto.id,
  title: dto.title,
  description: dto.description,
  done: dto.done,
  createdAt: new Date(dto.created_at),
  ownerId: dto.owner_id,
});

export interface ItemInput {
  title: string;
  description?: string | null;
  done?: boolean;
}

export async function listItems(): Promise<Item[]> {
  const dtos = await apiFetch<ItemDto[]>('/items');
  return dtos.map(toItem);
}

export async function createItem(input: ItemInput): Promise<Item> {
  const dto = await apiFetch<ItemDto>('/items', {
    method: 'POST',
    body: {
      title: input.title,
      description: input.description ?? null,
      done: input.done ?? false,
    },
  });
  return toItem(dto);
}

export async function updateItem(id: number, input: Partial<ItemInput>): Promise<Item> {
  const dto = await apiFetch<ItemDto>(`/items/${id}`, { method: 'PATCH', body: input });
  return toItem(dto);
}

export async function deleteItem(id: number): Promise<void> {
  await apiFetch<void>(`/items/${id}`, { method: 'DELETE' });
}
