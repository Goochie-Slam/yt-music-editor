import vi from "./vi.json";

type Leaves<T, P extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${P}${K}` : Leaves<T[K], `${P}${K}.`>;
}[keyof T & string];

export type MessageKey = Leaves<typeof vi>;

/** Every user-facing string goes through t() (docs/CODING-GUIDE.md §7.1). */
export function t(key: MessageKey, params?: Record<string, string | number>): string {
  let node: unknown = vi;
  for (const part of key.split(".")) {
    node = (node as Record<string, unknown> | undefined)?.[part];
  }
  const text = typeof node === "string" ? node : key;
  return params ? text.replace(/\{(\w+)\}/g, (m, k: string) => String(params[k] ?? m)) : text;
}
