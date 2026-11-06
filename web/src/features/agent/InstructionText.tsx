import { motion } from "framer-motion";
import type { AgentCard, ObligationCard } from "../../shared/data/types";
import { kindLabel } from "../../shared/format";
import { color, font, size, space, stateColor, stateLabel } from "../../shared/theme";
import { bySentence, worst } from "./sentences";

// The agent's own instructions, each sentence marked with what became of it on the candidate model.
export function InstructionText({ agent, active, onPick }: { agent: AgentCard; active: ObligationCard | null; onPick: (o: ObligationCard) => void }) {
  const parts = bySentence(agent);
  const implicit = agent.obligations.filter((o) => o.implicit);
  return (
    <div>
      <p style={{ fontFamily: font.text, fontSize: size.md, lineHeight: 1.75, margin: 0, color: color.ink, maxWidth: "68ch" }}>
        {parts.map(({ text, obligations }, i) => {
          const w = worst(obligations);
          if (!w) {
            return (
              <span key={i} title="No check came from this sentence" style={{ color: color.muted, textDecoration: `underline dotted ${stateColor.unread}`, textUnderlineOffset: 5 }}>
                {text}{" "}
              </span>
            );
          }
          const on = active !== null && obligations.includes(active);
          return (
            <span key={i}>
              <motion.button
                onClick={() => onPick(w)}
                aria-pressed={on}
                aria-label={`${text} — ${obligations.map((o) => `${kindLabel[o.kind]}: ${stateLabel[o.state]}`).join("; ")}`}
                animate={{ backgroundColor: on ? `${stateColor[w.state]}1F` : "rgba(0,0,0,0)" }}
                transition={{ duration: 0.2 }}
                style={{
                  font: "inherit",
                  color: "inherit",
                  border: 0,
                  padding: "1px 2px",
                  margin: "0 -2px",
                  cursor: "pointer",
                  textAlign: "left",
                  textDecoration: `underline ${w.state === "regressed" ? "solid" : w.state === "held" ? "solid" : "wavy"} ${stateColor[w.state]}`,
                  textDecorationThickness: w.state === "regressed" ? 3 : 2,
                  textUnderlineOffset: 5,
                  borderRadius: 2,
                  display: "inline",
                }}
              >
                {text}
              </motion.button>{" "}
            </span>
          );
        })}
      </p>
      {implicit.length > 0 && (
        <p style={{ fontSize: size.sm, color: color.muted, margin: `${space[4]}px 0 0` }}>
          From the setup, not the text:{" "}
          {implicit.map((o, i) => (
            <span key={o.kind}>
              {i > 0 && ", "}
              <button
                onClick={() => onPick(o)}
                style={{ font: "inherit", background: "none", border: 0, padding: 0, cursor: "pointer", color: stateColor[o.state], textDecoration: active === o ? "underline" : "none", textUnderlineOffset: 3 }}
              >
                {kindLabel[o.kind]} ({stateLabel[o.state].toLowerCase()})
              </button>
            </span>
          ))}
          .
        </p>
      )}
      <Legend />
    </div>
  );
}

function Legend() {
  const items: [keyof typeof stateColor, string][] = [
    ["held", "solid"],
    ["regressed", "solid"],
    ["watch", "wavy"],
    ["suspect", "wavy"],
    ["unread", "dotted"],
  ];
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: `${space[2]}px ${space[4]}px`, marginTop: space[4], fontSize: size.xs, color: color.muted }}>
      {items.map(([s, style]) => (
        <span key={s} style={{ textDecoration: `underline ${style} ${stateColor[s]}`, textDecorationThickness: 2, textUnderlineOffset: 4 }}>
          {stateLabel[s]}
        </span>
      ))}
    </div>
  );
}
