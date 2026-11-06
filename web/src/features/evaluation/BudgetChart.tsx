import { motion } from "framer-motion";
import type { Results } from "../../shared/data/types";
import { pct } from "../../shared/format";
import { color, font, size } from "../../shared/theme";

// Caught share against tokens per agent, one point per test-message budget.
export function BudgetChart({ budget, chosen }: { budget: Results["budget"]; chosen: number }) {
  if (budget.length < 2) return null;
  const W = 520, H = 220, L = 48, B = 36, T = 16, R = 36;
  const xs = budget.map((b) => b.tokens_per_agent);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const x = (v: number) => L + ((v - x0) / (x1 - x0)) * (W - L - R);
  const y = (v: number) => T + (1 - (v - 0.6) / 0.4) * (H - T - B);
  const path = budget.map((b, i) => `${i ? "L" : "M"}${x(b.tokens_per_agent)},${y(b.recall)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Share of regressed agents caught against tokens per agent" style={{ width: "100%", maxWidth: W, fontFamily: font.ui }}>
      {[0.6, 0.7, 0.8, 0.9, 1].map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke={color.rule} />
          <text x={L - 8} y={y(t) + 4} textAnchor="end" fontSize={size.xs} fill={color.muted}>
            {pct(t)}
          </text>
        </g>
      ))}
      <motion.path d={path} fill="none" stroke={color.accent} strokeWidth={2} initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.8, ease: "easeOut" }} />
      {budget.map((b) => (
        <g key={b.per_kind}>
          <circle cx={x(b.tokens_per_agent)} cy={y(b.recall)} r={b.per_kind === chosen ? 5 : 3.5} fill={b.per_kind === chosen ? color.accent : color.surface} stroke={color.accent} strokeWidth={2} />
          <text x={x(b.tokens_per_agent)} y={y(b.recall) - 10} textAnchor="middle" fontSize={size.xs} fill={b.per_kind === chosen ? color.ink : color.muted}>
            {b.per_kind}/kind
          </text>
          <text x={x(b.tokens_per_agent)} y={H - 12} textAnchor="middle" fontSize={size.xs} fill={color.muted}>
            {(b.tokens_per_agent / 1000).toFixed(1)}k
          </text>
        </g>
      ))}
      <text x={W - R} y={H - 0} textAnchor="end" fontSize={size.xs} fill={color.muted}>
        tokens per agent and model
      </text>
    </svg>
  );
}
