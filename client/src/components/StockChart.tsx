import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { useStockHistory, type HistoricalDataResponse } from "@/hooks/use-stocks";
import { Loader2 } from "lucide-react";

interface StockChartProps {
  symbol: string;
  changePercent: number;
}

export function StockChart({ symbol, changePercent }: StockChartProps) {
  const { data: history, isLoading } = useStockHistory(symbol);

  if (isLoading) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center bg-card/30 rounded-xl border border-border/50">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className="h-[300px] w-full flex items-center justify-center bg-card/30 rounded-xl border border-border/50">
        <p className="text-muted-foreground">No historical data available</p>
      </div>
    );
  }

  // Determine color based on overall change (positive = green, negative = red)
  const isPositive = changePercent >= 0;
  const strokeColor = isPositive ? "hsl(142 71% 45%)" : "hsl(0 84% 60%)";
  const fillColor = isPositive ? "hsl(142 71% 45%)" : "hsl(0 84% 60%)";

  // Format data for Recharts
  const chartData = history.map(item => ({
    date: new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    price: Number(item.close),
  }));

  return (
    <div className="h-[350px] w-full bg-card/50 rounded-xl border border-border/50 p-4 shadow-inner">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{
            top: 10,
            right: 0,
            left: 0,
            bottom: 0,
          }}
        >
          <defs>
            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={fillColor} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={fillColor} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" opacity={0.4} />
          <XAxis 
            dataKey="date" 
            tickLine={false} 
            axisLine={false} 
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
            minTickGap={30}
          />
          <YAxis 
            orientation="right"
            tickLine={false} 
            axisLine={false} 
            tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
            domain={['auto', 'auto']}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'hsl(var(--card))', 
              borderColor: 'hsl(var(--border))',
              borderRadius: '8px',
              color: 'hsl(var(--foreground))',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}
            itemStyle={{ color: 'hsl(var(--foreground))' }}
            formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
          />
          <Area 
            type="monotone" 
            dataKey="price" 
            stroke={strokeColor} 
            strokeWidth={2}
            fillOpacity={1} 
            fill="url(#colorPrice)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
