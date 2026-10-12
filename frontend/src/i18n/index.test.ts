import { t } from ".";

describe("t()", () => {
  it("looks up nested keys and fills params", () => {
    expect(t("steps.mix")).toBe("Mix");
    expect(t("placeholder.milestone", { milestone: "M3" })).toBe("Đang xây dựng — M3");
  });
  it("leaves unknown params visible rather than dropping them", () => {
    expect(t("placeholder.milestone")).toBe("Đang xây dựng — {milestone}");
  });
});
