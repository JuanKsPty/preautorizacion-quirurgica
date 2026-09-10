import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { InboxIcon, Loader2Icon, PlusIcon, Trash2Icon } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { z } from 'zod';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { createItem, deleteItem, listItems, updateItem } from '@/services/itemsService';

const esquema = z.object({
  title: z.string().min(3, 'Minimo 3 caracteres').max(120, 'Maximo 120 caracteres'),
  description: z.string().max(500, 'Maximo 500 caracteres').optional(),
});

type ValoresFormulario = z.infer<typeof esquema>;

const claveItems = ['items'] as const;

/**
 * CRUD de ejemplo, cableado punta a punta: SQLModel -> FastAPI -> service ->
 * TanStack Query -> formulario. Copia este archivo como plantilla para la
 * entidad real del proyecto y borra este cuando ya no lo necesites.
 */
export function ItemsPage() {
  const queryClient = useQueryClient();
  const [dialogoAbierto, setDialogoAbierto] = useState(false);

  const { data: items, isPending, isError, error } = useQuery({
    queryKey: claveItems,
    queryFn: listItems,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ValoresFormulario>({
    resolver: zodResolver(esquema),
    defaultValues: { title: '', description: '' },
  });

  const invalidar = () => queryClient.invalidateQueries({ queryKey: claveItems });

  const crear = useMutation({
    mutationFn: createItem,
    onSuccess: async () => {
      await invalidar();
      reset();
      setDialogoAbierto(false);
      toast.success('Item creado');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const alternar = useMutation({
    mutationFn: ({ id, done }: { id: number; done: boolean }) => updateItem(id, { done }),
    onSuccess: invalidar,
    onError: (e: Error) => toast.error(e.message),
  });

  const eliminar = useMutation({
    mutationFn: deleteItem,
    onSuccess: async () => {
      await invalidar();
      toast.success('Item eliminado');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const enviar = handleSubmit((valores) =>
    crear.mutateAsync({
      title: valores.title,
      description: valores.description?.trim() || null,
    })
  );

  const pendientes = items?.filter((item) => !item.done).length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Items</h1>
          <p className="text-sm text-muted-foreground">
            {isPending
              ? 'Cargando...'
              : `${items?.length ?? 0} en total, ${pendientes} sin completar`}
          </p>
        </div>

        <Dialog open={dialogoAbierto} onOpenChange={setDialogoAbierto}>
          <DialogTrigger asChild>
            <Button>
              <PlusIcon /> Nuevo item
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={(evento) => void enviar(evento)} noValidate>
              <DialogHeader>
                <DialogTitle>Nuevo item</DialogTitle>
                <DialogDescription>
                  Se guarda en la base de datos a traves de POST /api/items.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Titulo</Label>
                  <Input id="title" aria-invalid={Boolean(errors.title)} {...register('title')} />
                  {errors.title && (
                    <p className="text-sm text-destructive">{errors.title.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Descripcion (opcional)</Label>
                  <Textarea id="description" rows={3} {...register('description')} />
                  {errors.description && (
                    <p className="text-sm text-destructive">{errors.description.message}</p>
                  )}
                </div>
              </div>

              <DialogFooter>
                <Button type="submit" disabled={crear.isPending}>
                  {crear.isPending && <Loader2Icon className="animate-spin" />}
                  Guardar
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertTitle>No se pudieron cargar los items</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'Error desconocido'}
          </AlertDescription>
        </Alert>
      )}

      {isPending && (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}

      {items?.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-muted">
              <InboxIcon className="size-5 text-muted-foreground" />
            </span>
            <div>
              <p className="font-medium">Todavia no hay items</p>
              <p className="text-sm text-muted-foreground">
                Crea el primero o corre <code className="rounded bg-muted px-1">pnpm run seed</code>{' '}
                para tener datos de demo.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <ul className="space-y-3">
        {items?.map((item) => (
          <li key={item.id}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-start gap-3 text-base">
                  <input
                    type="checkbox"
                    className="mt-1 size-4 accent-primary"
                    checked={item.done}
                    aria-label={item.done ? 'Marcar como pendiente' : 'Marcar como completado'}
                    onChange={() => alternar.mutate({ id: item.id, done: !item.done })}
                  />
                  <span className={item.done ? 'text-muted-foreground line-through' : undefined}>
                    {item.title}
                  </span>
                  <Badge variant={item.done ? 'secondary' : 'outline'} className="ml-auto">
                    {item.done ? 'listo' : 'pendiente'}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between gap-4">
                <div className="space-y-1">
                  {item.description && <p className="text-sm">{item.description}</p>}
                  <p className="text-xs text-muted-foreground">
                    Creado el {item.createdAt.toLocaleString('es-PA')}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Eliminar ${item.title}`}
                  disabled={eliminar.isPending}
                  onClick={() => eliminar.mutate(item.id)}
                >
                  <Trash2Icon className="text-destructive" />
                </Button>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
