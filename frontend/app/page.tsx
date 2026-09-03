"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchAccount, fetchAdvice, fetchAnalysis, fetchMarkets, fetchPortfolio } from "../lib/api";
import type { AnalysisReport } from "../types/analysis";
import type { AccountSnapshot, PortfolioHolding, PortfolioSnapshot } from "../types/account";
import type { MarketSnapshot } from "../types/market";

const assets = {
  BTC: { name: "Bitcoin", icon: "₿", tone: "amber" },
  ETH: { name: "Ethereum", icon: "◆", tone: "violet" },
  BNB: { name: "BNB", icon: "◇", tone: "cyan" },
};
type Asset = keyof typeof assets;
type Message = { id: string; role: "agent" | "user"; title?: string; body: string };
type View = "command" | "markets" | "portfolio" | "activity";

const assetKeys = Object.keys(assets) as Asset[];
const quickPrompts = [
  { label: "Analyze BTC", prompt: "Analyze BTC for me" },
  { label: "Compare assets", prompt: "Compare BTC, ETH and BNB" },
  { label: "Portfolio status", prompt: "Show my portfolio status" },
  { label: "Market risk", prompt: "Explain BTC market risk" },
];
const initialMessages: Message[] = [{ id: "welcome", role: "agent", title: "ORBIT online", body: "I use live public Binance market data for BTC, ETH, and BNB. Account features remain unavailable until a verified read-only account is connected. ORBIT has no order capability." }];

export default function Home() {
  const [asset, setAsset] = useState<Asset>("BTC");
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [activities, setActivities] = useState(["Connecting to public Binance", "Risk engine initialized", "Waiting for request"]);
  const [marketSnapshots, setMarketSnapshots] = useState<Partial<Record<Asset, MarketSnapshot>>>({});
  const [analyses, setAnalyses] = useState<Partial<Record<Asset, AnalysisReport>>>({});
  const [accountSnapshot, setAccountSnapshot] = useState<AccountSnapshot | null>(null);
  const [portfolioSnapshot, setPortfolioSnapshot] = useState<PortfolioSnapshot | null>(null);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<View>("command");
  const [isRunning, setIsRunning] = useState(false);
  const currentMarket = marketSnapshots[asset];
  const currentAnalysis = analyses[asset];
  const marketReady = Object.values(marketSnapshots).some((snapshot) => snapshot?.source === "binance");
  const accountConnected = accountSnapshot?.permissions_verified === true;
  const holdings: PortfolioHolding[] = portfolioSnapshot?.holdings ?? accountSnapshot?.balances.map((balance) => ({ symbol: balance.asset, quantity: balance.total, market_value: null, allocation_percent: null, unit_price: null, price_status: "unpriced" as const, source: "binance" as const, freshness: accountSnapshot.freshness })) ?? [];

  function navigate(view: View) {
    setActiveView(view);
    document.getElementById(view)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  useEffect(() => {
    let active = true;
    fetchMarkets()
      .then(async (snapshots) => {
        if (!active) return;
        setMarketSnapshots(Object.fromEntries(snapshots.map((snapshot) => [snapshot.symbol as Asset, snapshot])) as Partial<Record<Asset, MarketSnapshot>>);
        setMarketError(null);
        setActivities((items) => ["Live Binance snapshots retrieved", ...items].slice(0, 6));
        const reports = await Promise.all(assetKeys.map(async (key) => [key, await fetchAnalysis(key)] as const));
        if (active) setAnalyses(Object.fromEntries(reports) as Partial<Record<Asset, AnalysisReport>>);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setMarketError(error instanceof Error ? error.message : "Market service unavailable");
        setActivities((items) => ["Live market connection failed", ...items].slice(0, 6));
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([fetchAccount(), fetchPortfolio()])
      .then(([account, portfolio]) => {
        if (!active) return;
        setAccountSnapshot(account);
        setPortfolioSnapshot(portfolio);
        setAccountError(null);
        setActivities((items) => ["Read-only Binance account verified", ...items].slice(0, 6));
      })
      .catch((error: unknown) => {
        if (!active) return;
        setAccountError(error instanceof Error ? error.message : "Account service unavailable");
      });
    return () => { active = false; };
  }, []);

  function addActivity(text: string) { setActivities((items) => [text, ...items].slice(0, 6)); }

  async function runAgent(value?: string) {
    if (isRunning) return;
    setIsRunning(true);
    const request = (value ?? prompt).trim() || "Analyze BTC for me";
    const normalized = request.toLowerCase();
    const requestId = crypto.randomUUID();
    const mentioned = assetKeys.find((key) => normalized.includes(key.toLowerCase()));
    const selectedAsset = mentioned ?? asset;
    const selectedMarket = marketSnapshots[selectedAsset];
    const selectedAnalysis = analyses[selectedAsset];
    let response: Message;

    if (normalized.includes("portfolio") || normalized.includes("rebalance") || normalized.includes("suggest") || normalized.includes("buy") || normalized.includes("sell") || normalized.includes("trade")) {
      if (accountConnected && portfolioSnapshot) {
        const coverage = `${portfolioSnapshot.positions.length} valued · ${portfolioSnapshot.unpriced_assets.length} unpriced`;
        try {
          const advice = await fetchAdvice(request);
          response = { id: `${requestId}-agent`, role: "agent", title: advice.provider === "openai" ? "Live ORBIT portfolio guidance" : "Deterministic portfolio guidance", body: `${advice.answer} ${portfolioSnapshot.positions.length ? `Covered value: ${formatPrice(portfolioSnapshot.total_value)} · ${coverage}.` : `${accountSnapshot.balances.length} non-zero balances were read; ${coverage}.`} ORBIT cannot place orders.` };
        } catch {
          response = { id: `${requestId}-agent`, role: "agent", title: "Verified read-only portfolio", body: portfolioSnapshot.positions.length ? `${formatPrice(portfolioSnapshot.total_value)} covered value · ${coverage} · ${portfolioSnapshot.concentration_risk} concentration risk. Unsupported assets are excluded rather than assigned fictional prices. ORBIT cannot place orders.` : `${accountSnapshot.balances.length} non-zero balances were read successfully; ${coverage}. Price coverage must be expanded before a total is shown. ORBIT cannot place orders.` };
        }
        addActivity("Live read-only portfolio reviewed");
      } else {
        response = { id: `${requestId}-agent`, role: "agent", title: "Read-only account required", body: "No simulated portfolio is shown in live mode. Connect a dedicated Binance key with every write-capable permission disabled to enable portfolio analysis. ORBIT cannot place orders." };
        addActivity("Account-dependent request safely declined");
      }
    } else if (normalized.includes("compare") || normalized.includes("strongest")) {
      const ranked = assetKeys.map((key) => analyses[key]).filter((item): item is AnalysisReport => Boolean(item)).sort((a, b) => b.score.final - a.score.final);
      response = ranked.length === assetKeys.length
        ? { id: `${requestId}-agent`, role: "agent", title: "Live comparison", body: `${ranked.map((item) => `${item.asset} ${item.score.final}/100`).join(" · ")}. Scores are deterministic informational signals from current public snapshots; on-chain data is unavailable.` }
        : { id: `${requestId}-agent`, role: "agent", title: "Comparison unavailable", body: "Live analysis data is still loading or unavailable. No fixture ranking has been substituted." };
      addActivity("Live assets compared");
    } else if (selectedMarket && selectedAnalysis) {
      if (mentioned) setAsset(mentioned);
      const explanation = (selectedAnalysis.explanation ?? "Deterministic analysis is available.").replace(/\.+$/, "");
      response = { id: `${requestId}-agent`, role: "agent", title: `${selectedAsset} live market analysis`, body: `${formatPrice(selectedMarket.price)} · ${formatChange(selectedMarket.change_24h)} over 24 hours. ${explanation}. Source: Binance public market data, ${selectedMarket.freshness}.` };
      addActivity(`${selectedAsset} live analysis generated`);
    } else {
      response = { id: `${requestId}-agent`, role: "agent", title: "Live data unavailable", body: "ORBIT could not retrieve a live market snapshot. It did not substitute simulated values." };
      addActivity("Live analysis unavailable");
    }
    setMessages((items) => [...items, { id: `${requestId}-user`, role: "user", body: request }, response]);
    setPrompt("");
    setIsRunning(false);
  }

  function submit(event: FormEvent) { event.preventDefault(); runAgent(); }

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="site-header">
        <div className="brand-lockup"><span className="orbit-logo"><i /><b>O</b></span><div><strong>ORBIT</strong><span>AI market intelligence</span></div></div>
        <nav className="desktop-nav" aria-label="Primary navigation">{([ ["command", "Command"], ["markets", "Markets"], ["portfolio", "Portfolio"], ["activity", "Activity"] ] as const).map(([view, label]) => <button key={view} className={activeView === view ? "active" : ""} aria-current={activeView === view ? "page" : undefined} aria-controls={view} onClick={() => navigate(view)}>{label}</button>)}</nav>
        <div className="header-actions"><span className="connection"><i /> {accountConnected ? "Read-only account connected" : marketReady ? "Live market connected" : "Connecting"}</span><button className="reset-button" onClick={() => window.location.reload()}>Refresh</button><span className="avatar">MN</span></div>
      </header>

      <section className="simulation-strip"><div><span className="live-pulse" /><strong>{accountConnected ? "BINANCE LIVE ACCOUNT + MARKET DATA" : "PUBLIC BINANCE MARKET DATA"}</strong><span>Read-only · no order capability</span></div><p>{marketError ? `Unavailable · ${marketError}` : accountConnected ? `Permissions verified · account ${accountSnapshot.freshness} · market live` : marketReady ? "Fresh public snapshots · UTC · deterministic analysis" : "Connecting to public endpoint…"}</p></section>

      <section className="intro">
        <div><p className="kicker">ORBIT COMMAND CENTER</p><h1>Market clarity, <em>on command.</em></h1><p>Ask naturally. ORBIT exposes live source data, deterministic calculations, risks, and limitations.</p></div>
        <div className="session-id"><span>SESSION</span><strong>{accountConnected ? "LIVE-ACCOUNT" : "LIVE-PUBLIC"}</strong><small>{accountConnected ? "Verified read-only access" : "Public data · no credentials"}</small></div>
      </section>

      <section id="command" className="workspace-grid">
        <article className="panel agent-panel">
          <div className="panel-header agent-header"><div><span className="eyebrow">AGENT WORKSPACE</span><h2>Ask ORBIT</h2></div><span className="agent-state"><i /> {marketReady ? "Ready" : "Connecting"}</span></div>
          <div className="quick-prompts">{quickPrompts.map((item) => <button key={item.label} onClick={() => runAgent(item.prompt)}>{item.label}<span>↗</span></button>)}</div>
          <div className="conversation" aria-live="polite">{messages.map((message) => { const body = message.id === "welcome" && accountConnected ? "I use live public Binance market data and your verified read-only account snapshot. Portfolio values include only assets with supported public price routes. ORBIT has no order capability." : message.body; return <div key={message.id} className={`message ${message.role}`}><span className="message-avatar">{message.role === "agent" ? "O" : "MN"}</span><div className="message-bubble">{message.title && <strong>{message.title}</strong>}<p>{body}</p>{message.role === "agent" && <small>LIVE MARKET · SAFE SUMMARY</small>}</div></div>; })}</div>
          <form className="command-box" onSubmit={submit}><span className="command-glyph">⌁</span><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder={accountConnected ? "Ask ORBIT about live markets or your read-only portfolio…" : "Ask ORBIT to analyze or compare live public markets…"} aria-label="Ask ORBIT" /><span className="keyboard-hint">↵</span><button type="submit" disabled={isRunning}>{isRunning ? "Thinking…" : "Run agent"} <span>→</span></button></form>
          <p className="input-note">{accountConnected ? "Market prices are public; portfolio data comes from your verified read-only account. No order capability." : "Market responses use public Binance data. Portfolio features require a verified read-only account."}</p>
        </article>

        <aside id="markets" className="right-rail">
          <section className="panel market-panel"><div className="panel-header compact"><div><span className="eyebrow">WATCHLIST</span><h2>Market snapshot</h2></div><span className="fixture-tag">{marketReady ? "BINANCE" : "WAITING"}</span></div><p className="section-explainer">Live public Binance prices for the three tracked markets. Select one to update the pulse below.</p><div className="asset-list">{assetKeys.map((key) => { const item = assets[key]; const market = marketSnapshots[key]; const change = market ? formatChange(market.change_24h) : "—"; return <button key={key} className={asset === key ? "asset-row selected" : "asset-row"} onClick={() => setAsset(key)}><span className={`asset-icon ${item.tone}`}>{item.icon}</span><span className="asset-name"><strong>{key}</strong><small>{item.name} · {market ? `${market.source} · ${market.freshness}` : "awaiting live data"}</small></span><span className="asset-price"><strong>{market ? formatPrice(market.price) : "—"}</strong><small className={market && market.change_24h >= 0 ? "up" : "down"}>{change}</small></span></button>; })}</div></section>
          <section className="panel score-panel"><div className="panel-header compact"><div><span className="eyebrow">LIVE RANKING</span><h2>Opportunity scores</h2></div><span className="info-dot">i</span></div>{assetKeys.map((key) => { const score = analyses[key]?.score.final; return <div className="rank-row" key={key}><div><span>{key}</span><strong>{score ?? "—"}{score !== undefined && <small>/100</small>}</strong></div><div className="score-track"><i style={{ width: `${score ?? 0}%` }} /></div></div>; })}<p className="score-note">Public snapshot · Market 30% · Technical 35% · On-chain unavailable · Risk 20%</p></section>
          <section id="activity" className="panel activity-panel"><div className="panel-header compact"><div><span className="eyebrow">AUDIT TRAIL</span><h2>Agent activity</h2></div><span className="activity-count">{activities.length}</span></div><p className="section-explainer">Read-only events recorded by this local session.</p><div className="activity-list">{activities.map((item, index) => <div key={`${item}-${index}`}><span className={index === 0 ? "active" : ""} /><p>{item}<small>{index === 0 ? "just now" : `${index + 1}m ago`}</small></p></div>)}</div></section>
        </aside>
      </section>

      <section id="portfolio" className="portfolio-section panel">
        <div className="panel-header"><div><span className="eyebrow">PORTFOLIO</span><h2>All account holdings</h2></div><span className="fixture-tag">{accountConnected ? `${holdings.length} HOLDINGS` : "NOT CONNECTED"}</span></div>
        <p className="section-explainer">Every non-zero balance returned by Binance is listed below. A holding can exist even when its public market price is unavailable; those assets stay visible and are excluded only from the total.</p>
        {!accountConnected ? <div className="empty-state">Connect a verified read-only Binance account to display holdings.</div> : holdings.length === 0 ? <div className="empty-state">No non-zero holdings were returned by Binance.</div> : <div className="holdings-table" role="table" aria-label="Complete account holdings"><div className="holding-row holding-head" role="row"><span>Asset</span><span>Quantity</span><span>Price</span><span>Value</span><span>Status</span></div>{holdings.map((holding) => <div className="holding-row" role="row" key={holding.symbol}><strong>{holding.symbol}</strong><span>{formatQuantity(holding.quantity)}</span><span>{holding.unit_price === null ? "—" : formatPrice(holding.unit_price)}</span><span>{holding.market_value === null ? "Excluded" : formatPrice(holding.market_value)}</span><span className={holding.price_status === "available" ? "price-available" : "price-unpriced"}>{holding.price_status === "available" ? "Price available" : "Unpriced"}</span></div>)}</div>}
        {accountConnected && portfolioSnapshot && <div className="portfolio-summary"><span>{formatPrice(portfolioSnapshot.total_value)} covered value</span><span>{portfolioSnapshot.positions.length} priced</span><span>{portfolioSnapshot.unpriced_assets.length} awaiting price coverage</span><span>Source: Binance · {portfolioSnapshot.freshness}</span></div>}
      </section>

      <section className="insight-grid">
        <article className="panel pulse-card"><div className="panel-header"><div><span className="eyebrow">SELECTED LIVE MARKET</span><h2>{asset}/USDT pulse</h2></div><span className={`risk-pill ${(currentAnalysis?.risk_level ?? "medium").toLowerCase()}`}>{currentAnalysis ? `${currentAnalysis.risk_level} risk` : "Awaiting data"}</span></div><div className="pulse-body"><div className="pulse-value"><strong>{currentMarket ? formatPrice(currentMarket.price) : "—"}</strong><span className={currentMarket && currentMarket.change_24h >= 0 ? "up" : "down"}>{currentMarket ? formatChange(currentMarket.change_24h) : "—"}</span><small>{currentMarket ? `Binance · ${currentMarket.freshness} · retrieved ${formatTime(currentMarket.retrieved_at)}` : "No simulated fallback"}</small></div><div className="mini-chart"><p className="suggestion-copy">Historical chart unavailable from the current 24-hour ticker endpoint. ORBIT will not draw a fictional price path.</p></div></div><div className="market-facts"><span><small>Trend</small><strong>{currentAnalysis?.metrics.trend ?? "—"}</strong></span><span><small>Quote volume</small><strong>{currentMarket ? formatVolume(currentMarket.volume_24h) : "—"}</strong></span><span><small>Momentum</small><strong>{currentAnalysis ? `${currentAnalysis.metrics.momentum}/100` : "—"}</strong></span><span><small>Data source</small><strong>{currentMarket?.source ?? "—"}</strong></span></div></article>
        <article className="panel suggestion-card"><div className="panel-header"><div><span className="eyebrow">ACCOUNT STATUS</span><h2>{accountConnected ? "Read-only account connected" : "Portfolio not connected"}</h2></div><span className="shield">◆</span></div><p className="suggestion-copy">{accountConnected ? `Binance verified reading access. ${accountSnapshot.balances.length} non-zero balances were retrieved ${accountSnapshot.freshness === "fresh" ? "freshly" : "from bounded stale cache"}.` : "Live portfolio holdings stay hidden until a dedicated Binance key passes ORBIT’s read-only permission checks."}</p><div className="suggestion-list"><div className="suggestion-item"><span className="suggestion-symbol">API</span><div><strong>{accountConnected ? "Permissions verified" : "Read-only account required"}</strong><small>{accountConnected && portfolioSnapshot ? `${portfolioSnapshot.positions.length} valued positions · ${portfolioSnapshot.unpriced_assets.length} assets await price coverage` : accountError ?? "All trading, withdrawal, and transfer permissions must be disabled"}</small></div></div></div><button className="suggestion-button" onClick={() => runAgent("Explain portfolio status")}>{accountConnected ? "Review portfolio status" : "Explain requirements"} <span>→</span></button><small className="guard-note">No simulated balances · no order capability</small></article>
      </section>

      <footer className="site-footer"><span>ORBIT · {accountConnected ? "Live read-only account mode" : "Live public market mode"}</span><span>Informational signal only — not financial advice</span></footer>
    </main>
  );
}

function formatPrice(value: number): string { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value); }
function formatQuantity(value: number): string { return new Intl.NumberFormat("en-US", { maximumFractionDigits: 8 }).format(value); }
function formatChange(value: number): string { return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`; }
function formatVolume(value: number): string {
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${value.toLocaleString("en-US")}`;
}
function formatTime(value?: string | null): string { return value ? new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", timeZoneName: "short" }) : "unknown time"; }
