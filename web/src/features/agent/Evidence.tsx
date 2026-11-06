import { AnimatePresence, motion } from "framer-motion";
import type { AgentCard, ObligationCard } from "../../shared/data/types";
import { kindLabel } from "../../shared/format";
import { color, font, radius, size, space, stateColor, stateLabel } from "../../shared/theme";

function Rate({ label, f, n, tone }: { label: string; f: number; n: number; tone: string }) {
  return (
    <div style={{ minWidth: 150 }}>
      <div style={{ fontSize: size.xs, color: color.muted }}>{label}</div>
      <div style={{ fontFamily: font.text, fontSize: size.xl, lineHeight: 1.1, color: tone }}>
        {f}
        <span style={{ fontSize: size.md, color: color.muted }}> of {n} failed</span>
      </div>
      <div aria-hidden style={{ height: 4, background: color.rule, marginTop: space[2], borderRadius: 2 }}>
        <motion.div initial={false} animate={{ width: `${n ? (100 * f) / n : 0}%` }} style={{ height: 4, background: tone, borderRadius: 2 }} />
      </div>
    </div>
  );
}

export function Evidence({ agent, o }: { agent: AgentCard; o: ObligationCard }) {
  const tone = stateColor[o.state];
  const why: Record<string, string> = {
    regressed: `The candidate fails this more often than chance would explain (p = ${o.p.toFixed(4)}${o.slice !== "all" ? `, on ${o.slice} questions` : ""}).`,
    watch: `The candidate fails this more often, but not by enough to be sure (p = ${o.p.toFixed(3)}). Worth a look.`,
    suspect: "The current model fails this check most of the time too, so the check or the reading of the instruction is probably wrong. Nobody should trust a pass here.",
    held: "Both models keep this about equally well.",
    improved: "The candidate keeps this better than the current model.",
    untested: "None of the test messages could check this.",
  };
  return (
    <section aria-label="Evidence" style={{ marginTop: space[6] }}>
      <h3 style={{ fontFamily: font.ui, fontSize: size.base, margin: 0 }}>
        {kindLabel[o.kind] ?? o.kind} <span style={{ color: tone, fontWeight: 500 }}>{stateLabel[o.state].toLowerCase()}</span>
        {o.hard && o.state === "regressed" && <span style={{ color: color.muted, fontWeight: 400 }}>, a hard rule, so this agent stays on the current model</span>}
      </h3>
      <p style={{ fontSize: size.sm, color: color.muted, margin: `${space[2]}px 0 ${space[4]}px`, maxWidth: "70ch", lineHeight: 1.5 }}>{why[o.state]}</p>
      <div style={{ display: "flex", gap: space[6], flexWrap: "wrap" }}>
        <Rate label={agent.baseline} f={o.baseline[0]} n={o.baseline[1]} tone={color.ink} />
        <Rate label={agent.candidate} f={o.candidate[0]} n={o.candidate[1]} tone={tone} />
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={o.kind} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }}>
          {o.examples.length === 0 ? (
            <p style={{ fontSize: size.sm, color: color.muted, marginTop: space[5] }}>No answer where only the candidate failed, so there is nothing to compare side by side.</p>
          ) : (
            o.examples.map((e, i) => (
              <figure key={i} style={{ margin: `${space[5]}px 0 0` }}>
                <figcaption style={{ fontSize: size.sm, marginBottom: space[2] }}>
                  <span style={{ color: color.muted }}>Asked: </span>
                  <span style={{ fontFamily: font.text, fontSize: size.base }}>{e.probe}</span>
                </figcaption>
                <div className="pair">
                  <Answer who={agent.baseline} text={e.baseline} actions={e.baseline_actions} />
                  <Answer who={agent.candidate} text={e.candidate} actions={e.candidate_actions} note={e.why} tone={tone} />
                </div>
              </figure>
            ))
          )}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}

function Answer({ who, text, actions, note, tone }: { who: string; text: string; actions: string[]; note?: string; tone?: string }) {
  return (
    <div style={{ background: color.paper, borderRadius: radius.small, padding: space[3], borderTop: `2px solid ${tone ?? color.rule}` }}>
      <div style={{ fontSize: size.xs, color: color.muted, marginBottom: space[1] }}>
        {who}
        {actions.length > 0 && `, called ${actions.join(", ")}`}
      </div>
      <div style={{ fontFamily: font.text, fontSize: size.base, lineHeight: 1.55, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{text || "(no text, only an action)"}</div>
      {note && <div style={{ fontSize: size.xs, color: tone, marginTop: space[2], fontWeight: 600 }}>{note}</div>}
    </div>
  );
}
