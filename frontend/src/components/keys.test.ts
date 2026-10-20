import { isTyping } from "./keys";

const on = (el: HTMLElement) => ({ target: el }) as unknown as KeyboardEvent;

describe("isTyping", () => {
  it("is true in text fields and false on checkboxes and buttons", () => {
    const text = document.createElement("input");
    const box = document.createElement("input");
    box.type = "checkbox";
    expect(isTyping(on(text))).toBe(true);
    expect(isTyping(on(document.createElement("textarea")))).toBe(true);
    expect(isTyping(on(box))).toBe(false); // Del after ticking a row must still delete it
    expect(isTyping(on(document.createElement("button")))).toBe(false);
  });
});
