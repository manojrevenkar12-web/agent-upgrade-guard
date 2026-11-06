export const pct = (x: number) => `${(x * 100).toFixed(x >= 0.995 || x === 0 ? 0 : 1)}%`;
export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

// Bench agents are named after their domain ("Crm assistant 20"); show the acronyms as people write them.
export const agentName = (n: string) => n.replace(/^(Crm|It|Hr)\b/, (m) => m.toUpperCase());

export const kindLabel: Record<string, string> = {
  language: "Answer language",
  cite_sources: "Names its source",
  json_output: "Returns valid JSON",
  tool_first: "Calls the action first",
  refuse_topic: "Declines a forbidden topic",
  stay_in_scope: "Stays in scope",
  max_words: "Stays under the word limit",
  ask_if_missing: "Asks for missing details",
  formal_address: "Formal address (Sie)",
  grounded: "Keeps the facts from its knowledge",
};
