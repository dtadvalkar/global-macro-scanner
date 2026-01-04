import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // Initialize mock data
  await storage.seedData();

  app.get(api.stocks.list.path, async (req, res) => {
    try {
      const filters = api.stocks.list.input.parse(req.query);
      
      // Convert 'true'/'false' string to boolean if present
      const processedFilters = {
        ...filters,
        aboveSma200: filters?.aboveSma200 === 'true'
      };

      const stocks = await storage.getStocks(processedFilters);
      res.json(stocks);
    } catch (err) {
      if (err instanceof z.ZodError) {
        res.status(400).json({ message: "Invalid filter parameters" });
        return;
      }
      throw err;
    }
  });

  app.get(api.stocks.get.path, async (req, res) => {
    const symbol = req.params.symbol;
    // Attempt update from Yahoo before returning
    await storage.updateStockFromYahoo(symbol);
    const stock = await storage.getStockBySymbol(symbol);
    if (!stock) {
      res.status(404).json({ message: "Stock not found" });
      return;
    }
    res.json(stock);
  });

  app.get(api.stocks.history.path, async (req, res) => {
    const symbol = req.params.symbol;
    const history = await storage.getHistoricalPrices(symbol);
    if (history.length === 0) {
      res.status(404).json({ message: "History not found" });
      return;
    }
    res.json(history);
  });

  return httpServer;
}
