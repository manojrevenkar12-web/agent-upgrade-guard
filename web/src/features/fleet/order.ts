import type { AgentCard } from "../../shared/data/types";
import type { Verdict } from "../../shared/theme";

export const verdictOrder: Verdict[] = ["block", "review", "safe"];

export const broken = (a: AgentCard) => a.obligations.filter((o) => o.state === "regressed" || o.state === "watch" || o.state === "suspect");

export function sortAgents(agents: AgentCard[]): AgentCard[] {
  return [...agents].sort(
    (a, b) => verdictOrder.indexOf(a.verdict) - verdictOrder.indexOf(b.verdict) || broken(b).length - broken(a).length || a.agent_id.localeCompare(b.agent_id),
  );
}
