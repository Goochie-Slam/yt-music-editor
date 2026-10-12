import { api } from "../api/client";
import type { Project } from "../api/types.gen";
import { AUTOSAVE_MS, useProject } from "./project";

const base = { id: "p1", name: "Mix", updatedAt: "2026-01-01T00:00:00Z" } as unknown as Project;

beforeEach(() => {
  vi.useFakeTimers();
  useProject.getState().load(structuredClone(base), "D:/Mix");
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("project store autosave", () => {
  it("debounces edits into a single save and keeps edits made meanwhile", async () => {
    const save = vi
      .spyOn(api, "saveProject")
      .mockImplementation(async (p) => ({ ...p, updatedAt: "2026-01-01T00:00:01Z" }));
    const { change } = useProject.getState();
    change((d) => void (d.name = "Mi"), "rename");
    change((d) => void (d.name = "Mix 2"), "rename");
    expect(useProject.getState().save).toBe("dirty");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_MS + 10);
    expect(save).toHaveBeenCalledTimes(1);
    expect(save.mock.calls[0]![0].name).toBe("Mix 2");
    const s = useProject.getState();
    expect(s.save).toBe("saved");
    expect(s.project?.updatedAt).toBe("2026-01-01T00:00:01Z");
    expect(s.hist.past).toHaveLength(1); // the two renames coalesced
  });

  it("shows the Vietnamese error when saving fails", async () => {
    const { ApiError } = await import("../api/client");
    vi.spyOn(api, "saveProject").mockRejectedValue(
      new ApiError(422, "invalid_input", "Dữ liệu không hợp lệ"),
    );
    useProject.getState().change((d) => void (d.name = "x"));
    await vi.advanceTimersByTimeAsync(AUTOSAVE_MS + 10);
    expect(useProject.getState()).toMatchObject({
      save: "error",
      saveError: "Dữ liệu không hợp lệ",
    });
  });

  it("undo is also autosaved", async () => {
    const save = vi.spyOn(api, "saveProject").mockImplementation(async (p) => p);
    useProject.getState().change((d) => void (d.name = "x"));
    await vi.advanceTimersByTimeAsync(AUTOSAVE_MS + 10);
    useProject.getState().undo();
    await vi.advanceTimersByTimeAsync(AUTOSAVE_MS + 10);
    expect(save).toHaveBeenCalledTimes(2);
    expect(save.mock.calls[1]![0].name).toBe("Mix");
  });
});
