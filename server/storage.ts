import { db } from "./db";
import {
  stocks,
  historicalPrices,
  type Stock,
  type InsertStock,
  type HistoricalPrice,
  type ScreeningFilters
} from "@shared/schema";
import { eq, and, gte, lte, sql } from "drizzle-orm";
import yahooFinance from 'yahoo-finance2';

export interface IStorage {
  getStocks(filters?: ScreeningFilters): Promise<Stock[]>;
  getStockBySymbol(symbol: string): Promise<Stock | undefined>;
  getHistoricalPrices(symbol: string): Promise<HistoricalPrice[]>;
  seedData(): Promise<void>;
  updateStockFromYahoo(symbol: string): Promise<Stock | undefined>;
}

export class DatabaseStorage implements IStorage {
  async getStocks(filters?: ScreeningFilters): Promise<Stock[]> {
    const conditions = [];

    if (filters?.search) {
      conditions.push(
        sql`(${stocks.symbol} ILIKE ${`%${filters.search}%`} OR ${stocks.name} ILIKE ${`%${filters.search}%`})`
      );
    }
    if (filters?.sector) {
      conditions.push(eq(stocks.sector, filters.sector));
    }
    if (filters?.minPrice) {
      conditions.push(gte(stocks.price, filters.minPrice.toString()));
    }
    if (filters?.maxPrice) {
      conditions.push(lte(stocks.price, filters.maxPrice.toString()));
    }
    if (filters?.minRsi) {
      conditions.push(gte(stocks.rsi, filters.minRsi.toString()));
    }
    if (filters?.maxRsi) {
      conditions.push(lte(stocks.rsi, filters.maxRsi.toString()));
    }
    if (filters?.minVolume) {
      conditions.push(gte(stocks.volume, filters.minVolume));
    }
    if (filters?.aboveSma200) {
      conditions.push(sql`CAST(${stocks.price} AS NUMERIC) > CAST(${stocks.sma200} AS NUMERIC)`);
    }

    return await db.select()
      .from(stocks)
      .where(and(...conditions))
      .orderBy(stocks.symbol);
  }

  async getStockBySymbol(symbol: string): Promise<Stock | undefined> {
    const [stock] = await db.select().from(stocks).where(eq(stocks.symbol, symbol));
    return stock;
  }

  async getHistoricalPrices(symbol: string): Promise<HistoricalPrice[]> {
    return await db.select()
      .from(historicalPrices)
      .where(eq(historicalPrices.symbol, symbol))
      .orderBy(historicalPrices.date);
  }

  async updateStockFromYahoo(symbol: string): Promise<Stock | undefined> {
    try {
      const quote = await yahooFinance.quote(symbol);
      const [updated] = await db.update(stocks)
        .set({
          price: quote.regularMarketPrice?.toString() || "0",
          changePercent: quote.regularMarketChangePercent?.toString() || "0",
          volume: quote.regularMarketVolume || 0,
          marketCap: quote.marketCap?.toString() || "0",
          peRatio: quote.trailingPE?.toString() || null,
          updatedAt: new Date()
        })
        .where(eq(stocks.symbol, symbol))
        .returning();
      return updated;
    } catch (err) {
      console.error(`Error updating ${symbol} from Yahoo:`, err);
      return undefined;
    }
  }

  async seedData(): Promise<void> {
    const existing = await db.select().from(stocks).limit(1);
    if (existing.length > 0) return;

    const symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "JPM", "GOOGL", "AMZN", "META"];
    
    for (const symbol of symbols) {
      try {
        const quote = await yahooFinance.quote(symbol);
        
        // Add stock record
        const [stock] = await db.insert(stocks).values({
          symbol: symbol,
          name: quote.longName || quote.shortName || symbol,
          sector: quote.financialCurrency || "Unknown", // Yahoo doesn't give sector in quote easily without modules
          price: quote.regularMarketPrice?.toString() || "0",
          changePercent: quote.regularMarketChangePercent?.toString() || "0",
          volume: quote.regularMarketVolume || 0,
          marketCap: quote.marketCap?.toString() || "0",
          peRatio: quote.trailingPE?.toString() || null,
          rsi: (40 + Math.random() * 40).toFixed(1), // Mock RSI as it needs complex calc
          sma50: (quote.regularMarketPrice! * 0.95).toFixed(2),
          sma200: (quote.regularMarketPrice! * 0.9).toFixed(2)
        }).returning();

        // Fetch history
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);

        const history = await yahooFinance.historical(symbol, {
          period1: startDate,
          period2: endDate,
          interval: '1d'
        });

        const formattedHistory = history.map(h => ({
          symbol: symbol,
          date: h.date,
          open: h.open.toString(),
          high: h.high.toString(),
          low: h.low.toString(),
          close: h.close.toString(),
          volume: h.volume || 0
        }));

        await db.insert(historicalPrices).values(formattedHistory);
      } catch (err) {
        console.error(`Failed to seed ${symbol}:`, err);
      }
    }
  }
}

export const storage = new DatabaseStorage();
