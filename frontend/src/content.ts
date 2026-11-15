import type { CardContent, IndicatorId } from "./contracts";

/**
 * Spec 5's content, read from content/ at the repo root (copied from the
 * specs-5-integration-and-submission branch). Bundled at build time, so it works offline.
 */
const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): string | undefined => (typeof v === "string" && v.trim() !== "" ? v : undefined);
const texts = (v: unknown): string[] | undefined => {
  const list = Array.isArray(v) ? v.filter((s): s is string => !!text(s)) : [];
  return list.length ? list : undefined;
};

/**
 * Keeps only the fields in the structured shape the card can show. A field in another shape
 * (e.g. the old flat strings) or left empty is dropped, so its section reads "Not added yet."
 * instead of breaking the card.
 */
export function normalizeCards(docs: unknown[]): CardContent[] {
  return docs.flatMap((d): CardContent[] => {
    if (!isObject(d) || !text(d.indicator)) return [];
    const card: CardContent = { indicator: d.indicator as string };
    const set = <K extends keyof CardContent>(key: K, value: CardContent[K] | undefined) => {
      if (value !== undefined) card[key] = value;
    };
    set("related_indicators", texts(d.related_indicators));
    set("unit", text(d.unit));
    set("how", texts(d.how));
    if (isObject(d.why) && text(d.why.text)) {
      const why: NonNullable<CardContent["why"]> = { text: d.why.text as string };
      for (const k of ["hrp_risk", "uncovered_reason", "source"] as const) if (text(d.why[k])) why[k] = d.why[k] as string;
      card.why = why;
    }
    if (isObject(d.if_abnormal)) {
      const steps: NonNullable<CardContent["if_abnormal"]> = {};
      for (const k of ["now", "remeasure", "tell_crew", "tell_ground"] as const) {
        if (text(d.if_abnormal[k])) steps[k] = d.if_abnormal[k] as string;
      }
      if (Object.keys(steps).length) card.if_abnormal = steps;
    }
    set("space_note", text(d.space_note));
    set("labels", texts(d.labels));
    set("sources", texts(d.sources));
    return [card];
  });
}

export const CONTENT_CARDS: CardContent[] = normalizeCards(
  Object.values(import.meta.glob("../../content/cards/*.json", { eager: true, import: "default" })),
);

/** The card that explains an Indicator: its own, or one listing it as related. */
export function cardFor(cards: CardContent[], indicator: IndicatorId): CardContent | undefined {
  return (
    cards.find((c) => c.indicator === indicator) ?? cards.find((c) => c.related_indicators?.includes(indicator))
  );
}

/** A mission profile file (content/profiles/<id>.json); only the fields the app shows. */
export interface ProfileContent {
  id: string;
  name: string;
  comm_delay?: { value: unknown; unit?: string; status?: string };
}

export const CONTENT_PROFILES: ProfileContent[] = Object.values(
  import.meta.glob<ProfileContent>("../../content/profiles/*.json", { eager: true, import: "default" }),
).filter((p) => typeof p.id === "string" && typeof p.name === "string");
