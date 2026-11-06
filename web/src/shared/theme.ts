// Every colour, face and size the dashboard uses. Components read these, never literals.
export const color = {
  paper: "#F2F4F6",
  surface: "#FFFFFF",
  ink: "#1B2230",
  muted: "#5B6577",
  rule: "#D5DAE1",
  accent: "#2D4BA0",
  accentSoft: "#E3E8F5",
} as const;

export type State = "held" | "regressed" | "watch" | "improved" | "untested" | "suspect";
export type Verdict = "safe" | "review" | "block";

export const stateColor: Record<State | "unread", string> = {
  held: "#2E7A64",
  improved: "#2E7A64",
  regressed: "#C23B2E",
  watch: "#B7800F",
  suspect: "#6A4BB0",
  untested: "#8B94A5",
  unread: "#8B94A5",
};

export const verdictColor: Record<Verdict, string> = {
  block: "#C23B2E",
  review: "#B7800F",
  safe: "#2E7A64",
};

export const verdictLabel: Record<Verdict, string> = {
  block: "Stay on the current model",
  review: "A person should look",
  safe: "Can switch",
};

export const stateLabel: Record<State | "unread", string> = {
  held: "Kept",
  improved: "Better",
  regressed: "Broken",
  watch: "Possibly broken",
  suspect: "Check doubtful",
  untested: "Not tested",
  unread: "Not read",
};

export const font = {
  text: "'Newsreader', Georgia, serif",
  ui: "'Instrument Sans', system-ui, sans-serif",
} as const;

// A 1.25 scale from 15px.
export const size = { xs: 12, sm: 13.5, base: 15, md: 18.75, lg: 23.4, xl: 29.3, xxl: 45.8 } as const;
export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48 } as const;
export const radius = { small: 3, panel: 8 } as const;

export const motion = { quick: { duration: 0.18, ease: [0.2, 0, 0, 1] }, settle: { type: "spring", stiffness: 380, damping: 34 } } as const;

export function cssVariables(): string {
  const vars = Object.entries(color).map(([k, v]) => `--${k}: ${v};`);
  return `:root{${vars.join("")}}`;
}
