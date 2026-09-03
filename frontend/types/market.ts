export type MarketSource = "simulation" | "binance";
export type MarketFreshness = "fixture" | "fresh" | "stale";

export type MarketSnapshot = {
  symbol: string;
  price: number;
  change_24h: number;
  volume_24h: number;
  timestamp: string;
  retrieved_at?: string | null;
  source: MarketSource;
  freshness: MarketFreshness;
};
