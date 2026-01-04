import { useQuery } from "@tanstack/react-query";
import { api, buildUrl } from "@shared/routes";
import { z } from "zod";

// Type definitions derived from Zod schemas
export type StocksListResponse = z.infer<typeof api.stocks.list.responses[200]>;
export type StockResponse = z.infer<typeof api.stocks.get.responses[200]>;
export type HistoricalDataResponse = z.infer<typeof api.stocks.history.responses[200]>;

// Input type for filtering
export type StockFilters = z.infer<NonNullable<typeof api.stocks.list.input>>;

export function useStocks(filters?: StockFilters) {
  // Construct query key that includes all filters so it refetches when they change
  const queryKey = [api.stocks.list.path, filters];
  
  return useQuery({
    queryKey,
    queryFn: async () => {
      // Build URL with query parameters
      const params: Record<string, string | number> = {};
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined && value !== "") {
            params[key] = value;
          }
        });
      }
      
      const queryString = new URLSearchParams(params as any).toString();
      const url = `${api.stocks.list.path}?${queryString}`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch stocks");
      
      // Parse with Zod schema
      return api.stocks.list.responses[200].parse(await res.json());
    },
  });
}

export function useStock(symbol: string | null) {
  return useQuery({
    queryKey: [api.stocks.get.path, symbol],
    queryFn: async () => {
      if (!symbol) throw new Error("Symbol is required");
      
      const url = buildUrl(api.stocks.get.path, { symbol });
      const res = await fetch(url);
      
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch stock details");
      
      return api.stocks.get.responses[200].parse(await res.json());
    },
    enabled: !!symbol,
  });
}

export function useStockHistory(symbol: string | null) {
  return useQuery({
    queryKey: [api.stocks.history.path, symbol],
    queryFn: async () => {
      if (!symbol) throw new Error("Symbol is required");
      
      const url = buildUrl(api.stocks.history.path, { symbol });
      const res = await fetch(url);
      
      if (res.status === 404) return [];
      if (!res.ok) throw new Error("Failed to fetch stock history");
      
      return api.stocks.history.responses[200].parse(await res.json());
    },
    enabled: !!symbol,
  });
}
