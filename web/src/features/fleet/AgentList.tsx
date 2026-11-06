import { AnimatePresence, motion } from "framer-motion";
import type { AgentCard } from "../../shared/data/types";
import { agentName, kindLabel } from "../../shared/format";
import { color, font, radius, size, space, verdictColor, verdictLabel, type Verdict } from "../../shared/theme";
import { Empty } from "../../shared/ui/States";
import { broken, verdictOrder } from "./order";

const EMPTY: Record<Verdict, string> = {
  block: "No agent breaks a hard rule on the candidate model.",
  review: "Nothing here needs a person's judgement.",
  safe: "Every agent has at least one obligation to look at first.",
};

export function AgentList({
  agents,
  filter,
  onFilter,
  selected,
  onSelect,
}: {
  agents: AgentCard[];
  filter: Verdict;
  onFilter: (v: Verdict) => void;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const shown = agents.filter((a) => a.verdict === filter);
  return (
    <nav aria-label="Agents" style={{ background: color.surface, borderRadius: radius.panel, border: `1px solid ${color.rule}` }}>
      <div role="tablist" style={{ display: "flex", borderBottom: `1px solid ${color.rule}` }}>
        {verdictOrder.map((v) => (
          <button
            key={v}
            role="tab"
            aria-selected={filter === v}
            onClick={() => onFilter(v)}
            style={{ flex: 1, position: "relative", background: "none", border: 0, padding: `${space[3]}px ${space[2]}px`, cursor: "pointer", fontSize: size.sm, color: filter === v ? color.ink : color.muted, fontWeight: filter === v ? 600 : 500 }}
          >
            {v === "block" ? "Stay" : v === "review" ? "Look" : "Switch"} <span style={{ color: verdictColor[v] }}>{agents.filter((a) => a.verdict === v).length}</span>
            {filter === v && <motion.span layoutId="list-tab" style={{ position: "absolute", left: 8, right: 8, bottom: -1, height: 2, background: verdictColor[v] }} />}
          </button>
        ))}
      </div>
      <p style={{ margin: 0, padding: `${space[3]}px ${space[4]}px 0`, fontSize: size.xs, color: color.muted }}>{verdictLabel[filter]}</p>
      <div className="scroll">
        {shown.length === 0 ? (
          <Empty title="No agents in this group">{EMPTY[filter]}</Empty>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: space[2] }}>
            <AnimatePresence initial={false} mode="popLayout">
              {shown.map((a) => {
                const b = broken(a);
                const on = selected === a.agent_id;
                return (
                  <motion.li key={a.agent_id} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
                    <button
                      onClick={() => onSelect(a.agent_id)}
                      aria-current={on}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        border: 0,
                        borderLeft: `3px solid ${on ? verdictColor[a.verdict] : "transparent"}`,
                        background: on ? color.accentSoft : "transparent",
                        padding: `${space[2]}px ${space[3]}px`,
                        cursor: "pointer",
                        borderRadius: radius.small,
                      }}
                    >
                      <div style={{ fontSize: size.sm, fontWeight: 600, color: color.ink }}>{agentName(a.agent_name)}</div>
                      <div style={{ fontSize: size.xs, color: color.muted, marginTop: 2, fontFamily: font.ui }}>
                        {b.length ? b.map((o) => kindLabel[o.kind] ?? o.kind).join(", ") : `${a.obligations.length} obligations kept`}
                      </div>
                    </button>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
        )}
      </div>
    </nav>
  );
}
