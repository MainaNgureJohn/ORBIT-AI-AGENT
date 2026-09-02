import { describe, expect, it } from "vitest";

import { calculateOpportunityScore } from "../lib/scoring";

describe("calculateOpportunityScore", () => {
  it("uses the documented weights and treats unavailable on-chain data as zero", () => {
    expect(
      calculateOpportunityScore({
        market: 72.72,
        technical: 66,
        onChain: null,
        risk: 58,
      }),
    ).toBe(56.5);
  });

  it("clamps every component to the 0–100 range", () => {
    expect(
      calculateOpportunityScore({
        market: 140,
        technical: -20,
        onChain: 100,
        risk: 100,
      }),
    ).toBe(65);
  });
});
