// LIOS — German Compliance Design System
// Clean, precise, institutional. EU blue + white + structured gray.

export const C = {
  // Backgrounds
  bg:    "#F1F4F9",   // cool light gray — main background
  card:  "#FFFFFF",   // pure white — card surfaces
  s2:    "#EBF0F8",   // blue-tinted — inputs, nested panels
  s3:    "#E3EAF5",   // deeper tint — modal sheets

  // Borders
  border:      "#C8D3E3",
  borderBright:"#7A9CC8",   // focused / active

  // Text
  text:  "#0F1C33",   // near-black navy
  mid:   "#4A5E7A",   // medium blue-gray
  dim:   "#8A9BB5",   // placeholder / muted

  // Primary — EU institutional blue
  primary:     "#003399",
  primaryDark: "#001F6B",
  primaryDim:  "#DAEAFF",   // tinted background
  primaryPress:"#0044CC",

  // Chat bubbles
  userMsg:  "#003399",   // user: primary blue bubble
  userText: "#FFFFFF",   // user: white text on blue
  aiBg:     "#FFFFFF",   // AI: white card
  aiText:   "#0F1C33",

  // Semantic
  green:   "#15692A",   // compliance confirmed
  greenBg: "#D1FAE5",
  amber:   "#7C4D0F",   // warning
  amberBg: "#FEF3C7",
  red:     "#991B1B",   // error / violation
  redBg:   "#FEE2E2",

  // Status dots (used in badges)
  online:  "#16A34A",
  offline: "#DC2626",
};

export const F = {
  xs:   11,
  sm:   13,
  md:   15,
  lg:   17,
  xl:   20,
  xxl:  26,
  huge: 42,
};

export const W = {
  regular: "400" as const,
  medium:  "500" as const,
  semi:    "600" as const,
  bold:    "700" as const,
  heavy:   "800" as const,
};

export const R = {
  xs:   3,
  sm:   6,
  md:   12,
  lg:   18,
  xl:   24,
  full: 999,
};

export const S = {
  xs:  4,
  sm:  8,
  md:  16,
  lg:  24,
  xl:  32,
  xxl: 48,
};

export function pctColor(pct: number): string {
  if (pct >= 80) return C.green;
  if (pct >= 40) return C.amber;
  return C.red;
}

export function pctBgColor(pct: number): string {
  if (pct >= 80) return C.greenBg;
  if (pct >= 40) return C.amberBg;
  return C.redBg;
}
