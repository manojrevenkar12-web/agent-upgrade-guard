import type { State, Verdict } from "../theme";

export interface Example {
  probe: string;
  baseline: string;
  candidate: string;
  why: string;
  baseline_actions: string[];
  candidate_actions: string[];
}

export interface ObligationCard {
  kind: string;
  source: string;
  implicit: boolean;
  params: Record<string, unknown>;
  hard: boolean;
  state: State;
  p: number;
  slice: string;
  baseline: [number, number];
  candidate: [number, number];
  examples: Example[];
}

export interface AgentCard {
  agent_id: string;
  agent_name: string;
  baseline: string;
  candidate: string;
  verdict: Verdict;
  obligations: ObligationCard[];
  probes_run: number;
  tokens_estimate: number;
  idle_days: number;
  domain: string;
  instructions: string;
  knowledge_docs: string[];
  tools: string[];
  consumer: string;
  unread: string[];
}

export interface GateScore {
  recall: number;
  false_alarm_rate: number;
  false_alarms_on_reworded: number;
}

export interface Score {
  agents: number;
  regressed_agents: number;
  clean_agents: number;
  guard: GateScore & { hard_blocked: number; obligation_recall: number; missed_by_kind: Record<string, Record<string, number>> };
  text_diff: GateScore & { threshold: number };
  recall_by_strength: Record<string, { agents: number; guard: number; text_diff: number }>;
  cost: { probes_per_agent: number; tokens_per_agent: number };
}

export interface Mining {
  precision: number;
  recall: number;
  per_kind: Record<string, { tp: number; fp: number; fn: number; wrong_params: number }>;
}

export interface HeldOut {
  set: string;
  run_at: string;
  world_sha256: string;
  score: Score;
  mining: Mining;
  misses: string[];
}

export interface Results {
  config: Record<string, unknown>;
  dev: { score: Score; mining: Mining };
  budget: { per_kind: number; recall: number; false_alarm_rate: number; tokens_per_agent: number; probes_per_agent: number }[];
  agents: AgentCard[];
  heldout: Record<string, HeldOut>;
}
