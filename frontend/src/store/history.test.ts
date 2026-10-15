import { COALESCE_MS, emptyHistory, HISTORY_LIMIT, record, redo, undo } from "./history";

type Doc = { name: string; n: number };

describe("history", () => {
  it("undo / redo round-trips", () => {
    let s: Doc = { name: "a", n: 0 };
    let h = emptyHistory();
    ({ state: s, hist: h } = record(s, h, (d) => void (d.name = "b")));
    ({ state: s, hist: h } = record(s, h, (d) => void (d.n = 5)));
    ({ state: s, hist: h } = undo(s, h));
    expect(s).toEqual({ name: "b", n: 0 });
    ({ state: s, hist: h } = undo(s, h));
    expect(s).toEqual({ name: "a", n: 0 });
    ({ state: s, hist: h } = redo(s, h));
    ({ state: s, hist: h } = redo(s, h));
    expect(s).toEqual({ name: "b", n: 5 });
    expect(h.future).toHaveLength(0);
  });

  it("a new change clears redo", () => {
    let s: Doc = { name: "a", n: 0 };
    let h = emptyHistory();
    ({ state: s, hist: h } = record(s, h, (d) => void (d.n = 1)));
    ({ state: s, hist: h } = undo(s, h));
    ({ state: s, hist: h } = record(s, h, (d) => void (d.n = 2)));
    expect(h.future).toHaveLength(0);
    expect(s.n).toBe(2);
  });

  it("coalesces same-key changes inside the window into one step", () => {
    let s: Doc = { name: "a", n: 0 };
    let h = emptyHistory();
    for (let i = 1; i <= 10; i++)
      ({ state: s, hist: h } = record(s, h, (d) => void (d.n = i), "slider", 1000 + i));
    expect(h.past).toHaveLength(1);
    ({ state: s, hist: h } = record(
      s,
      h,
      (d) => void (d.n = 99),
      "slider",
      1010 + COALESCE_MS + 1,
    ));
    expect(h.past).toHaveLength(2);
    ({ state: s, hist: h } = undo(s, h));
    ({ state: s, hist: h } = undo(s, h));
    expect(s.n).toBe(0);
  });

  it("no-op changes are not recorded and keep identity", () => {
    const s: Doc = { name: "a", n: 0 };
    const r = record(s, emptyHistory(), (d) => void (d.n = 0));
    expect(r.state).toBe(s);
    expect(r.hist.past).toHaveLength(0);
  });

  it(`keeps at most ${HISTORY_LIMIT} steps`, () => {
    let s: Doc = { name: "a", n: 0 };
    let h = emptyHistory();
    for (let i = 1; i <= HISTORY_LIMIT + 20; i++)
      ({ state: s, hist: h } = record(s, h, (d) => void (d.n = i)));
    expect(h.past).toHaveLength(HISTORY_LIMIT);
  });
});
