const NOT_TEXT = new Set(["checkbox", "radio", "button", "submit", "range", "color", "file"]);

/** Shortcuts stay off while the user is typing — but a focused checkbox is not typing. */
export function isTyping(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement | null;
  if (!el) return false;
  if (el.tagName === "INPUT") return !NOT_TEXT.has((el as HTMLInputElement).type);
  return el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable === true;
}
