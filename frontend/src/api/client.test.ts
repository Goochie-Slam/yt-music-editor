import { api, ApiError } from "./client";

afterEach(() => vi.restoreAllMocks());

describe("api client", () => {
  it("turns backend errors into ApiError with the Vietnamese message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: "project_corrupt",
          message_vi: "File project bị hỏng",
          detail: "x",
        }),
        {
          status: 422,
        },
      ),
    );
    const err = await api.openProject("C:/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 422,
      code: "project_corrupt",
      messageVi: "File project bị hỏng",
    });
  });

  it("reports a network failure in Vietnamese", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const err = (await api.recent().catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("network");
    expect(err.messageVi).toMatch(/Không kết nối/);
  });

  it("sends JSON bodies", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));
    await api.createProject("Mix", "D:/Nhạc");
    const [url, init] = spy.mock.calls[0]!;
    expect(url).toBe("/api/projects");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ name: "Mix", parentDir: "D:/Nhạc" });
  });
});
