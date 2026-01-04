import { z } from 'zod';
import { stocks, historicalPrices } from './schema';

export const errorSchemas = {
  notFound: z.object({
    message: z.string(),
  }),
  validation: z.object({
    message: z.string(),
  }),
};

export const api = {
  stocks: {
    list: {
      method: 'GET' as const,
      path: '/api/stocks',
      input: z.object({
        search: z.string().optional(),
        sector: z.string().optional(),
        minPrice: z.coerce.number().optional(),
        maxPrice: z.coerce.number().optional(),
        minRsi: z.coerce.number().optional(),
        maxRsi: z.coerce.number().optional(),
        minVolume: z.coerce.number().optional(),
        aboveSma200: z.enum(['true', 'false']).optional(),
      }).optional(),
      responses: {
        200: z.array(z.custom<typeof stocks.$inferSelect>()),
      },
    },
    get: {
      method: 'GET' as const,
      path: '/api/stocks/:symbol',
      responses: {
        200: z.custom<typeof stocks.$inferSelect>(),
        404: errorSchemas.notFound,
      },
    },
    history: {
      method: 'GET' as const,
      path: '/api/stocks/:symbol/history',
      responses: {
        200: z.array(z.custom<typeof historicalPrices.$inferSelect>()),
        404: errorSchemas.notFound,
      },
    },
  },
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}
