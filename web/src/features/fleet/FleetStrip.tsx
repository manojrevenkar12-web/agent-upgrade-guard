import { motion } from "framer-motion";
import type { AgentCard } from "../../shared/data/types";
import { agentName } from "../../shared/format";
import { color, font, size, space, verdictColor, verdictLabel } from "../../shared/theme";
import { verdictOrder } from "./order";

// One mark per agent, in verdict order: the whole upgrade at a glance.
export function FleetStrip({ agents, selected, onSelect }: { agents: AgentCard[]; selected: string | null; onSelect: (id: string) => void }) {
  const counts = verdictOrder.map((v) => ({ v, n: agents.filter((a) => a.verdict === v).length }));
  return (
    <div>
      <div role="list" aria-label="Agents by verdict" style={{ display: "flex", gap: 1, height: 44, alignItems: "stretch" }}>
        {agents.map((a, i) => (
          <motion.button
            role="listitem"
            key={a.agent_id}
            aria-label={`${agentName(a.agent_name)}: ${verdictLabel[a.verdict]}`}
            aria-pressed={selected === a.agent_id}
            onClick={() => onSelect(a.agent_id)}
            initial={{ scaleY: 0 }}
            animate={{ scaleY: selected === a.agent_id ? 1.18 : 1 }}
            transition={{ delay: selected === null ? i * 0.004 : 0, type: "spring", stiffness: 500, damping: 32 }}
            style={{
              flex: 1,
              minWidth: 0,
              border: 0,
              padding: 0,
              cursor: "pointer",
              background: verdictColor[a.verdict],
              opacity: selected && selected !== a.agent_id ? 0.55 : 1,
              transformOrigin: "bottom",
              borderRadius: 1,
            }}
          />
        ))}
      </div>
      <div className="strip-legend" style={{ marginTop: space[2], fontSize: size.sm, color: color.muted, fontFamily: font.ui }}>
        {counts.map(({ v, n }) => (
          <div key={v} style={{ ["--share" as string]: n || 0.0001 }}>
            {n > 0 && (
              <>
                <span style={{ color: verdictColor[v], fontWeight: 600 }}>{n}</span> {verdictLabel[v].toLowerCase()}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
