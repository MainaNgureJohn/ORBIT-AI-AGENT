"use client";

import { FormEvent, useMemo, useState } from "react";

const assets = {
  BTC: { name: "Bitcoin", price: "$68,420.00", change: "+2.84%", trend: "Bullish", risk: "Medium", score: 56.5, market: 72.7, technical: 66, riskScore: 58, volume: "$28.4B", support: "$66,800", resistance: "$70,200", icon: "₿", tone: "amber" },
  ETH: { name: "Ethereum", price: "$3,528.40", change: "+1.26%", trend: "Constructive", risk: "Medium", score: 52, market: 60, technical: 58, riskScore: 51, volume: "$14.1B", support: "$3,420", resistance: "$3,680", icon: "◆", tone: "violet" },
  BNB: { name: "BNB", price: "$612.75", change: "−0.42%", trend: "Neutral", risk: "Low", score: 48, market: 47, technical: 56, riskScore: 65, volume: "$1.9B", support: "$590", resistance: "$640", icon: "◇", tone: "cyan" },
};

type Asset = keyof typeof assets;
type Message = { id: string; role: "agent" | "user"; title?: string; body: string };

const quickPrompts = [
  { label: "Analyze BTC", prompt: "Analyze BTC for me" },
  { label: "Compare assets", prompt: "Compare BTC, ETH and BNB" },
  { label: "Improve portfolio", prompt: "Suggest portfolio improvements" },
  { label: "Portfolio risk", prompt: "Show my portfolio risk" },
];

const initialMessages: Message[] = [{ id: "welcome", role: "agent", title: "ORBIT online", body: "I can analyze read-only account and market data, compare setups, explain portfolio risk, and suggest possible improvements. ORBIT has no order capability." }];

export default function Home() {
  const [asset, setAsset] = useState<Asset>("BTC");
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [activities, setActivities] = useState(["Simulation fixtures loaded", "Risk engine initialized", "Waiting for request"]);
  const current = useMemo(() => assets[asset], [asset]);

  function addActivity(text: string) { setActivities((items) => [text, ...items].slice(0, 6)); }

  function runAgent(value?: string) {
    const request = (value ?? prompt).trim() || "Analyze BTC for me";
    const normalized = request.toLowerCase();
    const requestId = crypto.randomUUID();
    let response: Message;

    if (normalized.includes("suggest") || normalized.includes("improve") || normalized.includes("rebalance") || normalized.includes("trade") || normalized.includes("buy") || normalized.includes("sell")) {
      response = { id: `${requestId}-agent`, role: "agent", title: "Portfolio improvement ideas", body: "Based on the simulated allocation (42% BTC, 30% ETH, 28% USDT), consider reducing BTC toward 35–40%, exploring a small 5–8% BNB allocation, and retaining a 20–30% stablecoin reserve. These are informational suggestions only; ORBIT cannot place orders." };
      addActivity("Read-only suggestions generated");
    } else if (normalized.includes("compare") || normalized.includes("strongest")) {
      response = { id: `${requestId}-agent`, role: "agent", title: "Comparison complete", body: "BTC currently leads the deterministic fixture set at 56.5/100, followed by ETH at 52/100 and BNB at 48/100. BTC has stronger momentum, but its volatility keeps risk at Medium." };
      addActivity("Three assets ranked");
    } else if (normalized.includes("portfolio") || normalized.includes("risk")) {
      response = { id: `${requestId}-agent`, role: "agent", title: "Portfolio risk readout", body: "Simulated concentration is Medium and volatility exposure is Medium–High. A 28% stablecoin buffer reduces drawdown sensitivity. This is informational fixture output, not financial advice." };
      addActivity("Portfolio risk calculated");
    } else {
      const mentioned = (Object.keys(assets) as Asset[]).find((key) => normalized.includes(key.toLowerCase()));
      if (mentioned) setAsset(mentioned);
      const selected = mentioned ? assets[mentioned] : current;
      response = { id: `${requestId}-agent`, role: "agent", title: `${mentioned ?? asset} market analysis`, body: `${selected.price} · ${selected.change} over 24 hours. The fixture trend is ${selected.trend.toLowerCase()}, volume is ${selected.volume}, and opportunity score is ${selected.score}/100. Support sits near ${selected.support}; resistance is near ${selected.resistance}.` };
      addActivity(`${mentioned ?? asset} analysis generated`);
    }

    setMessages((items) => [...items, { id: `${requestId}-user`, role: "user", body: request }, response]);
    setPrompt("");
  }

  function submit(event: FormEvent) { event.preventDefault(); runAgent(); }
  function resetSimulation() { setMessages(initialMessages); setActivities(["Simulation reset", "Fixtures reloaded", "Waiting for request"]); setAsset("BTC"); }

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="site-header">
        <div className="brand-lockup"><span className="orbit-logo"><i /><b>O</b></span><div><strong>ORBIT</strong><span>AI market intelligence</span></div></div>
        <nav className="desktop-nav" aria-label="Primary navigation"><button className="active">Command</button><button>Markets</button><button>Portfolio</button><button>Activity</button></nav>
        <div className="header-actions"><span className="connection"><i /> Systems nominal</span><button className="reset-button" onClick={resetSimulation}>Reset</button><span className="avatar">MN</span></div>
      </header>

      <section className="simulation-strip"><div><span className="live-pulse" /><strong>SIMULATION MODE</strong><span>Read-only · no order capability</span></div><p>Deterministic fixture data · UTC · LLM disabled</p></section>

      <section className="intro">
        <div><p className="kicker">ORBIT COMMAND CENTER</p><h1>Market clarity, <em>on command.</em></h1><p>Ask naturally. ORBIT will expose the data, calculations, risks, and actions behind every answer.</p></div>
        <div className="session-id"><span>SESSION</span><strong>SIM-0902-A7</strong><small>Local · private · temporary</small></div>
      </section>

      <section className="workspace-grid">
        <article className="panel agent-panel">
          <div className="panel-header agent-header"><div><span className="eyebrow">AGENT WORKSPACE</span><h2>Ask ORBIT</h2></div><span className="agent-state"><i /> Ready</span></div>
          <div className="quick-prompts">{quickPrompts.map((item) => <button key={item.label} onClick={() => runAgent(item.prompt)}>{item.label}<span>↗</span></button>)}</div>
          <div className="conversation" aria-live="polite">
            {messages.map((message) => <div key={message.id} className={`message ${message.role}`}><span className="message-avatar">{message.role === "agent" ? "O" : "MN"}</span><div className="message-bubble">{message.title && <strong>{message.title}</strong>}<p>{message.body}</p>{message.role === "agent" && <small>SIMULATION · SAFE SUMMARY</small>}</div></div>)}
          </div>
          <form className="command-box" onSubmit={submit}><span className="command-glyph">⌁</span><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask ORBIT to analyze, compare, explain risk, or suggest improvements…" aria-label="Ask ORBIT" /><span className="keyboard-hint">↵</span><button type="submit">Run agent <span>→</span></button></form>
          <p className="input-note">Responses use fictional fixture data and deterministic calculations.</p>
        </article>

        <aside className="right-rail">
          <section className="panel market-panel"><div className="panel-header compact"><div><span className="eyebrow">WATCHLIST</span><h2>Market snapshot</h2></div><span className="fixture-tag">FIXTURE</span></div><div className="asset-list">{(Object.keys(assets) as Asset[]).map((key) => { const item = assets[key]; return <button key={key} className={asset === key ? "asset-row selected" : "asset-row"} onClick={() => setAsset(key)}><span className={`asset-icon ${item.tone}`}>{item.icon}</span><span className="asset-name"><strong>{key}</strong><small>{item.name}</small></span><span className="asset-price"><strong>{item.price}</strong><small className={item.change.startsWith("+") ? "up" : "down"}>{item.change}</small></span></button>; })}</div></section>
          <section className="panel score-panel"><div className="panel-header compact"><div><span className="eyebrow">RANKING</span><h2>Opportunity scores</h2></div><span className="info-dot">i</span></div>{(Object.keys(assets) as Asset[]).map((key) => <div className="rank-row" key={key}><div><span>{key}</span><strong>{assets[key].score}<small>/100</small></strong></div><div className="score-track"><i style={{ width: `${assets[key].score}%` }} /></div></div>)}<p className="score-note">Market 30% · Technical 35% · On-chain 15% · Risk 20%</p></section>
          <section className="panel activity-panel"><div className="panel-header compact"><div><span className="eyebrow">AUDIT TRAIL</span><h2>Agent activity</h2></div><span className="activity-count">{activities.length}</span></div><div className="activity-list">{activities.map((item, index) => <div key={`${item}-${index}`}><span className={index === 0 ? "active" : ""} /><p>{item}<small>{index === 0 ? "just now" : `${index + 1}m ago`}</small></p></div>)}</div></section>
        </aside>
      </section>

      <section className="insight-grid">
        <article className="panel pulse-card"><div className="panel-header"><div><span className="eyebrow">SELECTED MARKET</span><h2>{asset}/USDT pulse</h2></div><span className={`risk-pill ${current.risk.toLowerCase()}`}>{current.risk} risk</span></div><div className="pulse-body"><div className="pulse-value"><strong>{current.price}</strong><span className={current.change.startsWith("+") ? "up" : "down"}>{current.change}</span><small>24-hour fixture movement</small></div><div className="mini-chart"><svg viewBox="0 0 460 120" preserveAspectRatio="none" aria-label="Simulated price trend"><defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#f7c548" stopOpacity=".32"/><stop offset="1" stopColor="#f7c548" stopOpacity="0"/></linearGradient></defs><path d="M0 95 C25 83 44 92 66 72 S109 82 130 62 S172 72 195 48 S236 64 260 42 S302 51 326 29 S365 45 389 24 S430 35 460 10 L460 120 L0 120Z" fill="url(#chartFill)"/><path d="M0 95 C25 83 44 92 66 72 S109 82 130 62 S172 72 195 48 S236 64 260 42 S302 51 326 29 S365 45 389 24 S430 35 460 10" fill="none" stroke="#f7c548" strokeWidth="3"/></svg></div></div><div className="market-facts"><span><small>Trend</small><strong>{current.trend}</strong></span><span><small>Volume</small><strong>{current.volume}</strong></span><span><small>Support</small><strong>{current.support}</strong></span><span><small>Resistance</small><strong>{current.resistance}</strong></span></div></article>
        <article className="panel suggestion-card"><div className="panel-header"><div><span className="eyebrow">READ-ONLY GUIDANCE</span><h2>Portfolio improvement ideas</h2></div><span className="shield">◆</span></div><p className="suggestion-copy">ORBIT analyzes account data with read-only permission. It cannot prepare, submit, confirm, or cancel an order.</p><div className="suggestion-list"><div className="suggestion-item"><span className="suggestion-symbol">BTC</span><div><strong>Consider reducing</strong><small>42% now · target 35–40%</small></div></div><div className="suggestion-item"><span className="suggestion-symbol">BNB</span><div><strong>Consider adding</strong><small>0% now · target 5–8%</small></div></div><div className="suggestion-item"><span className="suggestion-symbol">USDT</span><div><strong>Hold reserve</strong><small>28% now · target 20–30%</small></div></div></div><button className="suggestion-button" onClick={() => runAgent("Suggest portfolio improvements")}>Explain suggestions <span>→</span></button><small className="guard-note">Analysis only · You remain in control</small></article>
      </section>

      <footer className="site-footer"><span>ORBIT v0.1 · Simulation foundation</span><span>Informational signal only — not financial advice</span></footer>

    </main>
  );
}
