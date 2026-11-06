import { color, cssVariables, font, size } from "./theme";

export const globalCss = `
${cssVariables()}
*{box-sizing:border-box}
html,body{margin:0;background:${color.paper};color:${color.ink};font-family:${font.ui};font-size:${size.base}px;-webkit-font-smoothing:antialiased}
button{font-family:inherit}
:focus-visible{outline:2px solid ${color.accent};outline-offset:2px;border-radius:2px}
.layout{display:grid;grid-template-columns:minmax(260px,320px) 1fr;gap:24px;align-items:start}
@media (max-width: 980px){.layout{grid-template-columns:1fr}}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width: 720px){.pair{grid-template-columns:1fr}}
.scroll{max-height:calc(100vh - 290px);overflow:auto}
@media (max-width: 980px){.scroll{max-height:340px}}
.strip-legend{display:flex}
.strip-legend>div{flex:var(--share);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:8px}
@media (max-width: 720px){.strip-legend{flex-direction:column;gap:2px}.strip-legend>div{flex:none}}
table{border-collapse:collapse;width:100%}
th{text-align:left;font-weight:600;color:${color.muted};font-size:${size.xs}px;padding:6px 8px;border-bottom:1px solid ${color.rule}}
td{padding:8px;border-bottom:1px solid ${color.rule};font-size:${size.sm}px;vertical-align:top}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
`;
