// Deep Forest — Japanese eco-minimal design system

export const C = {
  // Backgrounds
  bg:        "#0E1A11",  // deep forest
  s1:        "#162019",  // dark moss (cards)
  s2:        "#1D2B1F",  // bamboo panel (inputs, nested)
  s3:        "#243027",  // lifted panel

  // Borders
  border:    "#2A3D2C",  // natural divider
  borderBright: "#3A5040", // focused / active border

  // Text
  text:      "#E8E6DC",  // warm cream
  mid:       "#95A895",  // sage gray
  dim:       "#4A5F4C",  // forest dim (placeholders)

  // Accent — bamboo green
  accent:    "#7CB87F",
  accentDim: "#1E3022",  // tinted surface
  accentPress: "#5A9F5D",

  // Semantic
  green:     "#6BBF6B",  // moss green (success)
  greenDim:  "#1A2E1A",
  amber:     "#D4A04A",  // autumn leaf
  red:       "#C46060",  // dried maple
  redDim:    "#2E1414",

  // Chat-specific
  userMsg:   "#1E3022",  // user bubble bg
  userText:  "#C8DCC8",  // user bubble text
};

export const F = {
  xs:  11,
  sm:  13,
  md:  15,
  lg:  17,
  xl:  20,
  xxl: 28,
  huge: 44,
};

export const W = {
  regular: "400" as const,
  medium:  "500" as const,
  semi:    "600" as const,
  bold:    "700" as const,
  heavy:   "800" as const,
};

export const R = {
  xs:  4,
  sm:  8,
  md:  14,
  lg:  20,
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

// Pct-based color: green ≥80%, amber 40-79%, red <40%
export function pctColor(pct: number): string {
  if (pct >= 80) return C.green;
  if (pct >= 40) return C.amber;
  return C.red;
}
