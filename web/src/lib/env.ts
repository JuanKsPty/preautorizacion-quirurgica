import { z } from 'zod';

/**
 * Variables de entorno del frontend. Viven en el .env de la RAIZ del proyecto
 * (vite.config.ts apunta envDir alli) y deben llevar el prefijo VITE_.
 */
const envSchema = z.object({
  VITE_API_URL: z.string().min(1).default('/api'),
});

const parsed = envSchema.safeParse(import.meta.env);

if (!parsed.success) {
  const detalle = parsed.error.issues
    .map((issue) => `${issue.path.join('.')}: ${issue.message}`)
    .join(' | ');
  throw new Error(`Variables de entorno invalidas -> ${detalle}. Revisa el .env de la raiz.`);
}

export const env = {
  /** Base de todas las llamadas HTTP. En dev es /api y Vite lo proxea a FastAPI. */
  apiUrl: parsed.data.VITE_API_URL.replace(/\/+$/, ''),
};
