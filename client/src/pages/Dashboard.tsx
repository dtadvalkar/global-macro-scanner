import { useState } from "react";
import { useStocks, type StockFilters, type StockResponse } from "@/hooks/use-stocks";
import { StockFilterSidebar } from "@/components/StockFilters";
import { StockChart } from "@/components/StockChart";
import { Loader2, ArrowUpRight, ArrowDownRight, Activity, BarChart2, DollarSign, PieChart, X } from "lucide-react";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import clsx from "clsx";

export default function Dashboard() {
  const [filters, setFilters] = useState<StockFilters>({});
  const [selectedStock, setSelectedStock] = useState<StockResponse | null>(null);
  
  const { data: stocks, isLoading, isError } = useStocks(filters);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Sidebar Filter Panel */}
      <StockFilterSidebar onFilterChange={setFilters} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Header */}
        <header className="border-b border-border bg-card/20 backdrop-blur-md p-6 sticky top-0 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-display font-bold text-foreground">Market Overview</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Real-time screening and analysis of market movers.
              </p>
            </div>
            <div className="hidden md:flex gap-4">
               {/* Quick Stats */}
               <div className="flex items-center gap-3 px-4 py-2 bg-secondary/30 rounded-lg border border-border/50">
                 <div className="p-2 bg-primary/10 rounded-md">
                   <Activity className="w-4 h-4 text-primary" />
                 </div>
                 <div>
                   <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Active</p>
                   <p className="text-sm font-mono font-medium">{stocks?.length || 0}</p>
                 </div>
               </div>
            </div>
          </div>
        </header>

        {/* Stock List Table */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="h-full flex flex-col items-center justify-center gap-4">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-muted-foreground animate-pulse">Scanning market data...</p>
            </div>
          ) : isError ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-2">
                <p className="text-destructive font-medium">Failed to load market data</p>
                <button onClick={() => window.location.reload()} className="text-sm text-primary hover:underline">Retry Connection</button>
              </div>
            </div>
          ) : stocks && stocks.length === 0 ? (
             <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-4">
               <div className="p-4 rounded-full bg-muted/50 border border-border">
                  <SearchXIcon className="w-8 h-8" />
               </div>
               <p>No stocks match your criteria.</p>
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 pb-20">
              {stocks?.map((stock) => (
                <StockCard 
                  key={stock.symbol} 
                  stock={stock} 
                  onClick={() => setSelectedStock(stock)} 
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Stock Details Modal */}
      <Dialog open={!!selectedStock} onOpenChange={(open) => !open && setSelectedStock(null)}>
        <DialogContent className="max-w-4xl p-0 bg-background border-border overflow-hidden gap-0">
          {selectedStock && (
            <div className="flex flex-col h-[80vh] md:h-auto">
              {/* Modal Header */}
              <div className="p-6 border-b border-border bg-card/20 flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <h2 className="text-3xl font-display font-bold text-foreground">{selectedStock.symbol}</h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-secondary-foreground border border-border">
                      {selectedStock.sector}
                    </span>
                  </div>
                  <p className="text-muted-foreground">{selectedStock.name}</p>
                </div>
                
                <div className="text-right">
                  <div className="text-3xl font-mono font-medium tracking-tight">
                    ${Number(selectedStock.price).toFixed(2)}
                  </div>
                  <div className={clsx(
                    "flex items-center justify-end gap-1 font-medium mt-1",
                    Number(selectedStock.changePercent) >= 0 ? "text-success" : "text-destructive"
                  )}>
                    {Number(selectedStock.changePercent) >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                    {Math.abs(Number(selectedStock.changePercent)).toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Modal Body */}
              <div className="p-6 overflow-y-auto space-y-8">
                {/* Chart Section */}
                <section>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Price Performance</h3>
                  <StockChart symbol={selectedStock.symbol} changePercent={Number(selectedStock.changePercent)} />
                </section>

                {/* Key Stats Grid */}
                <section>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Key Statistics</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatBox 
                      label="Volume" 
                      value={new Intl.NumberFormat('en-US', { notation: "compact", compactDisplay: "short" }).format(selectedStock.volume)} 
                      icon={<BarChart2 className="w-4 h-4 text-blue-400" />}
                    />
                    <StatBox 
                      label="Market Cap" 
                      value={new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: "compact" }).format(Number(selectedStock.marketCap))} 
                      icon={<DollarSign className="w-4 h-4 text-green-400" />}
                    />
                    <StatBox 
                      label="P/E Ratio" 
                      value={selectedStock.peRatio ? Number(selectedStock.peRatio).toFixed(2) : '-'} 
                      icon={<PieChart className="w-4 h-4 text-purple-400" />}
                    />
                    <StatBox 
                      label="RSI (14)" 
                      value={Number(selectedStock.rsi).toFixed(0)} 
                      icon={<Activity className="w-4 h-4 text-orange-400" />}
                      highlight={Number(selectedStock.rsi) > 70 ? 'High' : Number(selectedStock.rsi) < 30 ? 'Low' : 'Neutral'}
                    />
                  </div>
                </section>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                   <div className="bg-secondary/20 p-4 rounded-xl border border-border/50">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-muted-foreground">50-Day SMA</span>
                        <span className="font-mono font-medium">${Number(selectedStock.sma50).toFixed(2)}</span>
                      </div>
                      <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                        <div 
                          className="bg-blue-500 h-full rounded-full" 
                          style={{ width: `${Math.min((Number(selectedStock.price) / Number(selectedStock.sma50)) * 50, 100)}%` }} 
                        />
                      </div>
                   </div>
                   <div className="bg-secondary/20 p-4 rounded-xl border border-border/50">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-muted-foreground">200-Day SMA</span>
                        <span className="font-mono font-medium">${Number(selectedStock.sma200).toFixed(2)}</span>
                      </div>
                       <div className="w-full bg-secondary h-1.5 rounded-full overflow-hidden">
                        <div 
                          className="bg-purple-500 h-full rounded-full" 
                          style={{ width: `${Math.min((Number(selectedStock.price) / Number(selectedStock.sma200)) * 50, 100)}%` }} 
                        />
                      </div>
                   </div>
                </div>
              </div>
            </div>
          )}
          <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
            <X className="h-6 w-6 text-muted-foreground hover:text-foreground" />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StockCard({ stock, onClick }: { stock: StockResponse, onClick: () => void }) {
  const isPositive = Number(stock.changePercent) >= 0;
  
  return (
    <div 
      onClick={onClick}
      className="group bg-card rounded-xl border border-border/50 p-5 hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 cursor-pointer relative overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      
      <div className="relative flex justify-between items-start mb-4">
        <div>
          <h3 className="font-bold font-display text-lg tracking-tight group-hover:text-primary transition-colors">{stock.symbol}</h3>
          <p className="text-xs text-muted-foreground truncate max-w-[120px]">{stock.name}</p>
        </div>
        <div className="text-right">
          <div className="font-mono font-medium">${Number(stock.price).toFixed(2)}</div>
          <div className={clsx(
            "text-xs font-bold flex items-center justify-end gap-0.5",
            isPositive ? "text-success" : "text-destructive"
          )}>
            {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(Number(stock.changePercent)).toFixed(2)}%
          </div>
        </div>
      </div>
      
      <div className="relative pt-4 border-t border-border/50 flex justify-between items-center text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-primary/70" />
          <span>RSI: <span className={Number(stock.rsi) > 70 || Number(stock.rsi) < 30 ? "text-foreground font-medium" : ""}>{Number(stock.rsi).toFixed(0)}</span></span>
        </div>
        <div className="uppercase tracking-wider opacity-70">{stock.sector}</div>
      </div>
    </div>
  );
}

function StatBox({ label, value, icon, highlight }: { label: string, value: string, icon: React.ReactNode, highlight?: string }) {
  return (
    <div className="p-4 rounded-xl bg-secondary/30 border border-border/50 flex flex-col gap-2">
      <div className="flex items-center justify-between text-muted-foreground">
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
        {icon}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-mono font-medium text-foreground">{value}</span>
        {highlight && (
          <span className={clsx(
            "text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase",
            highlight === 'High' ? "border-destructive/30 text-destructive bg-destructive/10" :
            highlight === 'Low' ? "border-success/30 text-success bg-success/10" :
            "border-border text-muted-foreground"
          )}>
            {highlight}
          </span>
        )}
      </div>
    </div>
  );
}

function SearchXIcon({ className }: { className?: string }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width="24" 
      height="24" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="m13.5 8.5-5 5" />
      <path d="m8.5 8.5 5 5" />
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}
