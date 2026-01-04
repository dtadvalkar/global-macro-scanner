import { db } from "./db";
import {
  stocks,
  historicalPrices,
  type Stock,
  type InsertStock,
  type HistoricalPrice,
  type ScreeningFilters
} from "@shared/schema";
import { eq, and, gte, lte, like, sql } from "drizzle-orm";

export interface IStorage {
  getStocks(filters?: ScreeningFilters): Promise<Stock[]>;
  getStockBySymbol(symbol: string): Promise<Stock | undefined>;
  getHistoricalPrices(symbol: string): Promise<HistoricalPrice[]>;
  seedData(): Promise<void>;
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
      conditions.push(sql`${stocks.price} > ${stocks.sma200}`);
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

  async seedData(): Promise<void> {
    const existing = await db.select().from(stocks).limit(1);
    if (existing.length > 0) return;

    const sectors = ["Technology", "Healthcare", "Finance", "Consumer", "Energy"];
    const mockStocks: InsertStock[] = [
      {
        symbol: "AAPL",
        name: "Apple Inc.",
        sector: "Technology",
        price: "185.50",
        changePercent: "1.2",
        volume: 50000000,
        marketCap: "2800000000000",
        peRatio: "28.5",
        rsi: "65.4",
        sma50: "175.20",
        sma200: "160.50"
      },
      {
        symbol: "MSFT",
        name: "Microsoft Corp.",
        sector: "Technology",
        price: "402.10",
        changePercent: "-0.5",
        volume: 25000000,
        marketCap: "3000000000000",
        peRatio: "35.2",
        rsi: "72.1",
        sma50: "390.00",
        sma200: "350.00"
      },
      {
        symbol: "TSLA",
        name: "Tesla Inc.",
        sector: "Consumer",
        price: "215.30",
        changePercent: "-2.4",
        volume: 110000000,
        marketCap: "680000000000",
        peRatio: "45.0",
        rsi: "35.5",
        sma50: "230.00",
        sma200: "245.00"
      },
      {
        symbol: "NVDA",
        name: "NVIDIA Corp.",
        sector: "Technology",
        price: "650.00",
        changePercent: "3.5",
        volume: 45000000,
        marketCap: "1600000000000",
        peRatio: "85.4",
        rsi: "82.0",
        sma50: "580.00",
        sma200: "480.00"
      },
      {
        symbol: "JPM",
        name: "JPMorgan Chase",
        sector: "Finance",
        price: "175.20",
        changePercent: "0.8",
        volume: 12000000,
        marketCap: "500000000000",
        peRatio: "11.2",
        rsi: "58.4",
        sma50: "168.00",
        sma200: "155.00"
      }
    ];

    await db.insert(stocks).values(mockStocks);

    // Generate mock history for each stock
    for (const stock of mockStocks) {
      const history = [];
      let price = parseFloat(stock.price as string);
      const today = new Date();
      
      for (let i = 30; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        
        const volatility = price * 0.02;
        const change = (Math.random() - 0.5) * volatility;
        const open = price - change / 2;
        const close = price + change / 2;
        const high = Math.max(open, close) + Math.random() * volatility * 0.5;
        const low = Math.min(open, close) - Math.random() * volatility * 0.5;
        
        history.push({
          symbol: stock.symbol,
          date,
          open: open.toFixed(2),
          high: high.toFixed(2),
          low: low.toFixed(2),
          close: close.toFixed(2),
          volume: Math.floor(stock.volume * (0.8 + Math.random() * 0.4))
        });
        
        price = open; // simplistic backward generation
      }
      
      await db.insert(historicalPrices).values(history);
    }
  }
}

export const storage = new DatabaseStorage();
