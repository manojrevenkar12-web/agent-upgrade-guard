import type { AgentCard, ObligationCard } from "../../shared/data/types";
import type { State } from "../../shared/theme";

// Same split as guard.spec.sentences, so a sentence here is exactly an obligation's source.
export function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+|\n+/)
    .map((s) => s.replace(/^[\s\-•*]+|[\s\-•*]+$/g, ""))
    .filter(Boolean);
}

const rank: State[] = ["regressed", "suspect", "watch", "untested", "improved", "held"];

export function worst(obs: ObligationCard[]): ObligationCard | undefined {
  return [...obs].sort((a, b) => rank.indexOf(a.state) - rank.indexOf(b.state))[0];
}

export function bySentence(agent: AgentCard): { text: string; obligations: ObligationCard[] }[] {
  return sentences(agent.instructions).map((text) => ({ text, obligations: agent.obligations.filter((o) => !o.implicit && o.source === text) }));
}
