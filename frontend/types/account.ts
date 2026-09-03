export type AccountBalance = {
  asset: string;
  free: number;
  locked: number;
  total: number;
};

export type AccountSnapshot = {
  balances: AccountBalance[];
  source: "binance";
  permission_scope: "read_only";
  permissions_verified: boolean;
  freshness: "fresh" | "stale";
  fetched_at: string;
};

export type PortfolioPosition = {
  symbol: string;
  quantity: number;
  market_value: number;
  allocation_percent: number;
};

export type PortfolioHolding = {
  symbol: string;
  quantity: number;
  market_value: number | null;
  allocation_percent: number | null;
  unit_price: number | null;
  price_status: "available" | "unpriced";
  source: "binance";
  freshness: "fresh" | "stale";
};

export type PortfolioSnapshot = {
  total_value: number;
  stablecoin_percent: number;
  concentration_risk: "Low" | "Medium" | "High";
  positions: PortfolioPosition[];
  holdings: PortfolioHolding[];
  source: "binance";
  permission_scope: "read_only";
  fetched_at: string;
  freshness: "fresh" | "stale";
  unpriced_assets: string[];
};
