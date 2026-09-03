import type { AnalysisReport } from "../types/analysis";
import type { AccountSnapshot, PortfolioSnapshot } from "../types/account";
import type { MarketSnapshot } from "../types/market";

const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

export async function fetchMarket(symbol: string): Promise<MarketSnapshot> {
  const response = await fetch(`${backendUrl}/api/v1/market/${encodeURIComponent(symbol)}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Market request failed (${response.status})`);
  return response.json() as Promise<MarketSnapshot>;
}

export async function fetchMarkets(): Promise<MarketSnapshot[]> {
  const response = await fetch(`${backendUrl}/api/v1/market`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Market request failed (${response.status})`);
  return response.json() as Promise<MarketSnapshot[]>;
}

export async function fetchAnalysis(symbol: string): Promise<AnalysisReport> {
  const response = await fetch(`${backendUrl}/api/v1/analyze/${encodeURIComponent(symbol)}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Analysis request failed (${response.status})`);
  return response.json() as Promise<AnalysisReport>;
}

export async function fetchAccount(): Promise<AccountSnapshot> {
  const response = await fetch(`${backendUrl}/api/v1/account`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Account request failed (${response.status})`);
  return response.json() as Promise<AccountSnapshot>;
}

export async function fetchPortfolio(): Promise<PortfolioSnapshot> {
  const response = await fetch(`${backendUrl}/api/v1/portfolio`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Portfolio request failed (${response.status})`);
  return response.json() as Promise<PortfolioSnapshot>;
}

export async function fetchAdvice(question: string): Promise<{ answer: string; provider: "groq" | "openai" | "deterministic"; source: "binance" | "none"; limitations: string[] }> {
  const response = await fetch(`${backendUrl}/api/v1/advice`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }), cache: "no-store" });
  if (!response.ok) throw new Error(`Advice request failed (${response.status})`);
  return response.json();
}
