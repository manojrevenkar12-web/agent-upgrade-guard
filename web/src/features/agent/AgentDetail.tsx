import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { AgentCard, ObligationCard } from "../../shared/data/types";
import { agentName, kindLabel, plural } from "../../shared/format";
import { color, font, radius, size, space, stateColor, stateLabel, verdictColor, verdictLabel } from "../../shared/theme";
import { Evidence } from "./Evidence";
import { InstructionText } from "./InstructionText";
import { worst } from "./sentences";

export function AgentDetail({ agent }: { agent: AgentCard }) {
  const [active, setActive] = useState<ObligationCard | null>(worst(agent.obligations) ?? null);
  useEffect(() => setActive(worst(agent.obligations) ?? null), [agent]);
  const setup = [
    agent.knowledge_docs.length ? plural(agent.knowledge_docs.length, "knowledge document", "knowledge documents") : null,
    agent.tools.length ? `action ${agent.tools.join(", ")}` : null,
    agent.consumer === "workflow" ? "read by a workflow step" : "read by people",
  ].filter(Boolean);

  return (
    <motion.article
      key={agent.agent_id}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      style={{ background: color.surface, border: `1px solid ${color.rule}`, borderRadius: radius.panel, padding: space[6], minWidth: 0 }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", gap: space[4], flexWrap: "wrap", alignItems: "baseline" }}>
        <div>
          <h2 style={{ fontFamily: font.ui, fontSize: size.lg, margin: 0, fontWeight: 600 }}>{agentName(agent.agent_name)}</h2>
          <p style={{ margin: `${space[1]}px 0 0`, fontSize: size.sm, color: color.muted }}>
            {setup.join(", ")}; checked with {agent.probes_run} test messages on each model
          </p>
        </div>
        <div style={{ fontSize: size.base, fontWeight: 600, color: verdictColor[agent.verdict], borderLeft: `3px solid ${verdictColor[agent.verdict]}`, paddingLeft: space[3] }}>
          {verdictLabel[agent.verdict]}
        </div>
      </header>

      <div style={{ marginTop: space[6] }}>
        <InstructionText agent={agent} active={active} onPick={setActive} />
      </div>

      <table style={{ marginTop: space[6] }}>
        <thead>
          <tr>
            <th>Obligation</th>
            <th>Result</th>
            <th className="num">Current fails</th>
            <th className="num">Candidate fails</th>
          </tr>
        </thead>
        <tbody>
          {agent.obligations.map((o) => (
            <tr key={o.kind + o.source} onClick={() => setActive(o)} style={{ cursor: "pointer", background: active === o ? color.accentSoft : undefined }}>
              <td>
                <button onClick={() => setActive(o)} style={{ font: "inherit", background: "none", border: 0, padding: 0, cursor: "pointer", textAlign: "left", color: color.ink }}>
                  {kindLabel[o.kind] ?? o.kind}
                  {o.hard && <span style={{ color: color.muted }}> (hard rule)</span>}
                </button>
              </td>
              <td style={{ color: stateColor[o.state], fontWeight: 600 }}>{stateLabel[o.state]}</td>
              <td className="num">
                {o.baseline[0]}/{o.baseline[1]}
              </td>
              <td className="num" style={{ color: o.state === "regressed" ? stateColor.regressed : undefined }}>
                {o.candidate[0]}/{o.candidate[1]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {active && <Evidence agent={agent} o={active} />}
    </motion.article>
  );
}
