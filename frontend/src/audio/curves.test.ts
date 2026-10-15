import fixture from "../../../shared/fixtures/curves.json";
import { gainIn, gainOut, type Curve } from "./curves";

const data = fixture as Record<Curve, { in: number[]; out: number[] }>;

describe("curves match the backend (shared/fixtures/curves.json)", () => {
  for (const curve of Object.keys(data) as Curve[]) {
    it(curve, () => {
      const pts = data[curve];
      pts.in.forEach((expected, i) => {
        const x = i / (pts.in.length - 1);
        expect(Math.abs(gainIn(curve, x) - expected)).toBeLessThan(1e-6);
        expect(Math.abs(gainOut(curve, x) - pts.out[i]!)).toBeLessThan(1e-6);
      });
    });
  }

  it("clamps outside [0, 1]", () => {
    expect(gainIn("linear", -1)).toBe(0);
    expect(gainIn("linear", 2)).toBe(1);
  });
});
