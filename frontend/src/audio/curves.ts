/**
 * Fade gain curves — must stay identical to backend/app/audio/curves.py.
 * Both are tested against shared/fixtures/curves.json.
 * x ∈ [0, 1] is fade progress; a fade-out is the fade-in reversed in time.
 */
export type Curve = "equal-power" | "linear" | "log" | "s-curve";

export const LOG_EXPONENT = 2.5;

export function gainIn(curve: Curve, x: number): number {
  const v = Math.min(1, Math.max(0, x));
  switch (curve) {
    case "equal-power":
      return Math.sin((v * Math.PI) / 2);
    case "linear":
      return v;
    case "log":
      return Math.pow(v, LOG_EXPONENT);
    case "s-curve":
      return (1 - Math.cos(Math.PI * v)) / 2;
  }
}

export function gainOut(curve: Curve, x: number): number {
  return gainIn(curve, 1 - x);
}
