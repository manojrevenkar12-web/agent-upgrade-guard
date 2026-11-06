import { motion } from "framer-motion";
import { color, font, size, space } from "../theme";

const box = { padding: space[7], maxWidth: 560, margin: "0 auto", fontFamily: font.ui, color: color.ink } as const;

export function Loading() {
  return (
    <div style={box} role="status" aria-live="polite">
      <motion.div
        style={{ height: 3, background: color.accent, transformOrigin: "left", borderRadius: 2 }}
        initial={{ scaleX: 0.05 }}
        animate={{ scaleX: [0.05, 0.7, 0.05] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      />
      <p style={{ marginTop: space[4], color: color.muted, fontSize: size.sm }}>Loading the upgrade check…</p>
    </div>
  );
}

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div style={box} role="alert">
      <h2 style={{ fontFamily: font.text, fontSize: size.lg, fontWeight: 500, margin: 0 }}>The results could not be loaded</h2>
      <p style={{ color: color.muted, fontSize: size.base, lineHeight: 1.5 }}>{message}</p>
      <button onClick={onRetry} style={buttonStyle}>
        Try again
      </button>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: space[6], fontFamily: font.ui, color: color.muted, fontSize: size.sm, lineHeight: 1.5 }}>
      <p style={{ margin: 0, color: color.ink, fontWeight: 600 }}>{title}</p>
      <p style={{ margin: `${space[2]}px 0 0` }}>{children}</p>
    </div>
  );
}

export const buttonStyle = {
  font: `600 ${size.sm}px ${font.ui}`,
  color: color.surface,
  background: color.accent,
  border: 0,
  borderRadius: 4,
  padding: `${space[2]}px ${space[4]}px`,
  cursor: "pointer",
} as const;
