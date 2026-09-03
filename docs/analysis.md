# Deterministic analysis

ORBIT keeps calculations in testable Python code and treats any language-model layer as optional presentation only.

## Score formula

Each component is clamped to 0–100:

```text
final = market × 0.30
      + technical × 0.35
      + on_chain × 0.15
      + risk × 0.20
```

When a component is unavailable, the API keeps it `null`, lists its name in `score.missing_components`, and contributes zero to the weighted total. This makes missing evidence visible rather than silently turning it into a positive signal.

The engine currently derives conservative momentum and volatility from the available 24-hour change only. It does not claim to provide historical indicators, on-chain data, or financial advice. The deterministic explanation provider reports only validated fields from the analysis result.
