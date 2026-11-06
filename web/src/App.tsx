import { MotionConfig, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { AgentDetail } from "./features/agent/AgentDetail";
import { Evaluation } from "./features/evaluation/Evaluation";
import { AgentList } from "./features/fleet/AgentList";
import { FleetStrip } from "./features/fleet/FleetStrip";
import { sortAgents } from "./features/fleet/order";
import type { Results } from "./shared/data/types";
import { useResults } from "./shared/data/useResults";
import { globalCss } from "./shared/globalCss";
import { color, font, size, space, type Verdict } from "./shared/theme";
import { Empty, LoadError, Loading } from "./shared/ui/States";

type View = "agents" | "evaluation";

export function App() {
  const r = useResults();
  return (
    <MotionConfig reducedMotion="user">
      <style>{globalCss}</style>
      {r.status === "loading" && <Loading />}
      {r.status === "error" && <LoadError message={r.message} onRetry={r.retry} />}
      {r.status === "ready" && <Ready data={r.data} />}
    </MotionConfig>
  );
}

function Ready({ data }: { data: Results }) {
  const agents = useMemo(() => sortAgents(data.agents), [data]);
  const [view, setView] = useState<View>("agents");
  const [filter, setFilter] = useState<Verdict>("block");
  const [selected, setSelected] = useState<string | null>(agents[0]?.agent_id ?? null);
  const agent = agents.find((a) => a.agent_id === selected) ?? null;
  const first = agents[0];

  const select = (id: string) => {
    setSelected(id);
    const a = agents.find((x) => x.agent_id === id);
    if (a) setFilter(a.verdict);
    setView("agents");
  };

  return (
    <div style={{ maxWidth: 1320, margin: "0 auto", padding: `${space[6]}px ${space[5]}px ${space[7]}px` }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: space[4], flexWrap: "wrap" }}>
        <div>
          <h1 style={{ fontFamily: font.ui, fontSize: size.base, fontWeight: 600, margin: 0, color: color.muted }}>Upgrade check</h1>
          <p style={{ fontFamily: font.text, fontSize: size.xxl, lineHeight: 1.05, margin: `${space[2]}px 0 0`, letterSpacing: "-0.01em" }}>
            {first ? `${first.baseline.replace(" (simulated)", "")} to ${first.candidate.replace(" (simulated)", "")}` : "No agents"}
          </p>
        </div>
        <div role="tablist" aria-label="View" style={{ display: "flex", gap: space[5] }}>
          {(["agents", "evaluation"] as View[]).map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={view === v}
              onClick={() => setView(v)}
              style={{ position: "relative", background: "none", border: 0, padding: `${space[2]}px 0`, fontSize: size.base, cursor: "pointer", color: view === v ? color.ink : color.muted, fontWeight: view === v ? 600 : 500 }}
            >
              {v === "agents" ? "Agents" : "How well it works"}
              {view === v && <motion.span layoutId="view-tab" style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 2, background: color.accent }} />}
            </button>
          ))}
        </div>
      </header>
      <p style={{ fontSize: size.sm, color: color.muted, margin: `${space[3]}px 0 ${space[5]}px`, maxWidth: "80ch", lineHeight: 1.5 }}>
        Each agent's instructions were read into checkable obligations, then the same test messages went to both models. An agent is held back only where the candidate fails an obligation more often than chance
        explains. Simulated workspace of {agents.length} agents.
      </p>

      {agents.length === 0 ? (
        <Empty title="No agents to check">Run `guard report` to generate the workspace, then reload.</Empty>
      ) : (
        <>
          <FleetStrip agents={agents} selected={view === "agents" ? selected : null} onSelect={select} />
          <div style={{ marginTop: space[6] }}>
            {view === "agents" ? (
              <div className="layout">
                <AgentList agents={agents} filter={filter} onFilter={setFilter} selected={selected} onSelect={select} />
                {agent ? <AgentDetail agent={agent} /> : <Empty title="Pick an agent">Choose one from the list or the strip above.</Empty>}
              </div>
            ) : (
              <Evaluation data={data} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
