import { useState, useEffect } from "react";
import { Search, Filter, RefreshCw, TrendingUp } from "lucide-react";
import { type StockFilters } from "@/hooks/use-stocks";

interface StockFiltersProps {
  onFilterChange: (filters: StockFilters) => void;
}

export function StockFilterSidebar({ onFilterChange }: StockFiltersProps) {
  const [filters, setFilters] = useState<StockFilters>({
    search: "",
    sector: "",
    minPrice: undefined,
    maxPrice: undefined,
    minRsi: undefined,
    maxRsi: undefined,
    aboveSma200: undefined,
  });

  // Debounce the filter changes to avoid too many API calls
  useEffect(() => {
    const handler = setTimeout(() => {
      onFilterChange(filters);
    }, 300);

    return () => clearTimeout(handler);
  }, [filters, onFilterChange]);

  const handleInputChange = (key: keyof StockFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value === "" ? undefined : value }));
  };

  return (
    <div className="w-full lg:w-80 border-r border-border bg-card/30 p-6 flex flex-col gap-8 h-full overflow-y-auto">
      <div className="space-y-2">
        <h2 className="text-xl font-display font-bold flex items-center gap-2 text-primary">
          <TrendingUp className="h-6 w-6" />
          Market Screener
        </h2>
        <p className="text-sm text-muted-foreground">
          Filter stocks based on technical indicators.
        </p>
      </div>

      <div className="space-y-6">
        {/* Search */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Symbol</label>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search AAPL, MSFT..."
              className="w-full bg-secondary/50 border border-border rounded-lg pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-muted-foreground/50 font-mono uppercase"
              value={filters.search || ""}
              onChange={(e) => handleInputChange("search", e.target.value)}
            />
          </div>
        </div>

        {/* Sector */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sector</label>
          <select
            className="w-full bg-secondary/50 border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all text-foreground appearance-none cursor-pointer"
            value={filters.sector || ""}
            onChange={(e) => handleInputChange("sector", e.target.value)}
          >
            <option value="">All Sectors</option>
            <option value="Technology">Technology</option>
            <option value="Healthcare">Healthcare</option>
            <option value="Finance">Finance</option>
            <option value="Energy">Energy</option>
            <option value="Consumer">Consumer Goods</option>
          </select>
        </div>

        {/* Price Range */}
        <div className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex justify-between">
            <span>Price Range</span>
            <span className="text-primary font-mono text-[10px] bg-primary/10 px-1.5 py-0.5 rounded">USD</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Min"
              className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
              onChange={(e) => handleInputChange("minPrice", Number(e.target.value))}
            />
            <input
              type="number"
              placeholder="Max"
              className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
              onChange={(e) => handleInputChange("maxPrice", Number(e.target.value))}
            />
          </div>
        </div>

        {/* RSI Range */}
        <div className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex justify-between">
            <span>RSI (14)</span>
            <span className="text-muted-foreground/50 text-[10px]">0-100</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="0"
              min="0"
              max="100"
              className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
              onChange={(e) => handleInputChange("minRsi", Number(e.target.value))}
            />
            <input
              type="number"
              placeholder="100"
              min="0"
              max="100"
              className="bg-secondary/50 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono"
              onChange={(e) => handleInputChange("maxRsi", Number(e.target.value))}
            />
          </div>
        </div>

        {/* Technicals */}
        <div className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Technicals</label>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors cursor-pointer" onClick={() => handleInputChange("aboveSma200", filters.aboveSma200 === 'true' ? undefined : 'true')}>
            <div className={`w-4 h-4 rounded-sm border ${filters.aboveSma200 === 'true' ? 'bg-primary border-primary' : 'border-muted-foreground'}`}>
              {filters.aboveSma200 === 'true' && <div className="text-primary-foreground flex items-center justify-center text-xs">✓</div>}
            </div>
            <span className="text-sm">Above 200 SMA</span>
          </div>
        </div>

        <button 
          onClick={() => {
            setFilters({});
            onFilterChange({});
          }}
          className="w-full flex items-center justify-center gap-2 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors border border-dashed border-border hover:border-muted-foreground rounded-lg"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Reset Filters
        </button>
      </div>
    </div>
  );
}
