export type ScoreInputs = {
  market: number;
  technical: number;
  onChain?: number | null;
  risk: number;
};

export function calculateOpportunityScore({
  market,
  technical,
  onChain,
  risk,
}: ScoreInputs): number {
  const clamp = (value: number) => Math.max(0, Math.min(100, value));
  const total =
    clamp(market) * 0.3 +
    clamp(technical) * 0.35 +
    clamp(onChain ?? 0) * 0.15 +
    clamp(risk) * 0.2;

  return Math.round(total * 10) / 10;
}
