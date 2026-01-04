import { pgTable, text, serial, numeric, integer, timestamp, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Stock Data Snapshot for Screening
export const stocks = pgTable("stocks", {
  id: serial("id").primaryKey(),
  symbol: text("symbol").notNull().unique(),
  name: text("name").notNull(),
  sector: text("sector").notNull(),
  price: numeric("price").notNull(),
  changePercent: numeric("change_percent").notNull(),
  volume: integer("volume").notNull(),
  marketCap: numeric("market_cap").notNull(),
  peRatio: numeric("pe_ratio"),
  rsi: numeric("rsi"), // Relative Strength Index (14)
  sma50: numeric("sma_50"), // 50-day Simple Moving Average
  sma200: numeric("sma_200"), // 200-day Simple Moving Average
  updatedAt: timestamp("updated_at").defaultNow(),
});

// Historical Data for Charts
export const historicalPrices = pgTable("historical_prices", {
  id: serial("id").primaryKey(),
  symbol: text("symbol").notNull(),
  date: timestamp("date").notNull(),
  open: numeric("open").notNull(),
  high: numeric("high").notNull(),
  low: numeric("low").notNull(),
  close: numeric("close").notNull(),
  volume: integer("volume").notNull(),
});

// Schemas
export const insertStockSchema = createInsertSchema(stocks).omit({ id: true, updatedAt: true });
export const insertHistoricalPriceSchema = createInsertSchema(historicalPrices).omit({ id: true });

// Types
export type Stock = typeof stocks.$inferSelect;
export type InsertStock = z.infer<typeof insertStockSchema>;
export type HistoricalPrice = typeof historicalPrices.$inferSelect;

// API Contract Types
export type StockResponse = Stock;
export type HistoricalPriceResponse = HistoricalPrice;

export interface StockListResponse {
  items: Stock[];
  total: number;
}

export interface ScreeningFilters {
  search?: string;
  sector?: string;
  minPrice?: number;
  maxPrice?: number;
  minRsi?: number;
  maxRsi?: number;
  minVolume?: number;
  aboveSma200?: boolean;
}
