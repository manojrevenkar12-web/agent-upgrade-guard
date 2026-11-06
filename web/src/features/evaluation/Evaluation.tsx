import type { Results, Score } from "../../shared/data/types";
import { kindLabel, pct } from "../../shared/format";
import { color, font, radius, size, space, stateColor } from "../../shared/theme";
import { BudgetChart } from "./BudgetChart";

const panel = { background: color.surface, border: `1px solid ${color.rule}`, borderRadius: radius.panel, padding: space[6] } as const;

export function Evaluation({ data }: { data: Results }) {
  const rows: { name: string; note: string; s: Score; read: number }[] = [
    { name: "Development", note: "tuned on", s: data.dev.score, read: data.dev.mining.recall },
    ...Object.values(data.heldout).map((h) => ({
      name: `Held-out ${h.set}`,
      note: h.set === "v1" ? "first version, run once" : "current version, run once",
      s: h.score,
      read: h.mining.recall,
    })),
  ];
  const latest = Object.values(data.heldout).at(-1);
  return (
    <div style={{ display: "grid", gap: space[5] }}>
      <section style={panel}>
        {latest && (
          <p style={{ fontFamily: font.text, fontSize: size.lg, lineHeight: 1.4, margin: 0, maxWidth: "46ch" }}>
            On {latest.score.agents} agents whose instructions it had never seen, the guard caught {pct(latest.score.guard.recall)} of the upgrades that broke something and
            flagged none of the clean ones. Comparing answer text caught {pct(latest.score.text_diff.recall)} and flagged {pct(latest.score.text_diff.false_alarm_rate)} of clean agents.
          </p>
        )}
        <table style={{ marginTop: space[6] }}>
          <thead>
            <tr>
              <th>Workspace</th>
              <th className="num">Agents</th>
              <th className="num">Caught, guard</th>
              <th className="num">Caught, text diff</th>
              <th className="num">Clean flagged, guard</th>
              <th className="num">Clean flagged, text diff</th>
              <th className="num">Instructions read</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name}>
                <td>
                  {r.name}
                  <div style={{ fontSize: size.xs, color: color.muted }}>{r.note}</div>
                </td>
                <td className="num">{r.s.agents}</td>
                <td className="num" style={{ fontWeight: 600 }}>{pct(r.s.guard.recall)}</td>
                <td className="num">{pct(r.s.text_diff.recall)}</td>
                <td className="num" style={{ fontWeight: 600 }}>{pct(r.s.guard.false_alarm_rate)}</td>
                <td className="num" style={{ color: r.s.text_diff.false_alarm_rate > 0.2 ? stateColor.regressed : undefined }}>{pct(r.s.text_diff.false_alarm_rate)}</td>
                <td className="num" style={{ color: r.read < 0.8 ? stateColor.regressed : undefined }}>{pct(r.read)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: size.xs, color: color.muted, marginTop: space[3], lineHeight: 1.5, maxWidth: "90ch" }}>
          Simulated models with planted regressions; the text-diff gate uses its best threshold on development ({data.config.text_diff_threshold as number}). Held-out workspaces were pinned by
          sha256 before their only run.
        </p>
      </section>

      <div className="pair" style={{ gap: space[5] }}>
        <section style={panel}>
          <h2 style={{ fontSize: size.md, margin: 0, fontWeight: 600 }}>Where the current version misses</h2>
          <p style={{ fontSize: size.sm, color: color.muted, lineHeight: 1.5 }}>
            Held-out {latest?.set}: most misses are instructions the rules could not read, not tests that failed to notice. The checks and the statistics hold; reading new wording is the weak part.
          </p>
          {latest && <Misses missed={latest.score.guard.missed_by_kind} />}
        </section>
        <section style={panel}>
          <h2 style={{ fontSize: size.md, margin: 0, fontWeight: 600 }}>How many test messages</h2>
          <p style={{ fontSize: size.sm, color: color.muted, lineHeight: 1.5 }}>Development workspace. More messages per kind catch rarer slips and cost more tokens; 12 per kind is the setting.</p>
          <BudgetChart budget={data.budget} chosen={data.config.per_kind as number} />
        </section>
      </div>
    </div>
  );
}

function Misses({ missed }: { missed: Record<string, Record<string, number>> }) {
  const entries = Object.entries(missed);
  if (!entries.length) return <p style={{ fontSize: size.sm }}>No misses.</p>;
  const max = Math.max(...entries.map(([, v]) => v["not mined"] + v.untested + v.held));
  const seg: [string, string][] = [
    ["not mined", stateColor.unread],
    ["held", stateColor.watch],
    ["untested", color.rule],
  ];
  return (
    <div>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: "grid", gridTemplateColumns: "minmax(140px, 200px) 1fr", gap: space[3], alignItems: "center", marginTop: space[2] }}>
          <span style={{ fontSize: size.sm }}>{kindLabel[k] ?? k}</span>
          <div style={{ display: "flex", height: 12 }}>
            {seg.map(([key, c]) => (v[key] ? <div key={key} title={`${v[key]} ${key}`} style={{ width: `${(100 * v[key]) / max}%`, background: c }} /> : null))}
          </div>
        </div>
      ))}
      <div style={{ display: "flex", gap: space[4], fontSize: size.xs, color: color.muted, marginTop: space[4] }}>
        <span><span style={{ display: "inline-block", width: 10, height: 10, background: stateColor.unread, marginRight: 6 }} />instruction not read</span>
        <span><span style={{ display: "inline-block", width: 10, height: 10, background: stateColor.watch, marginRight: 6 }} />tested, not significant</span>
      </div>
    </div>
  );
}
