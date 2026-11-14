import type { IndicatorId } from "../contracts";
import { INDICATORS } from "../indicators";
import type { Glow } from "./glow";
import { STRUCTURES, type StructureId } from "./structures";
import type { BodyView, Focus, LayerId, LayerView } from "./view";

/** Insight view: muscles, skeleton and vessels faint; organs and brain clearer when relevant. */
const INSIGHT_FAINT: Record<LayerId, number> = {
  muscles: 0.05,
  skeleton: 0.08,
  vessels: 0.08,
  organs: 0.12,
  brain: 0.12,
};
const INSIGHT_RELEVANT = 0.35;
const INSIGHT_OTHER_STRUCTURE = 0.06;

/** Structures an Indicator can be shown on, or [] when it has no body place (mood, whole body). */
export function insightStructures(indicator: IndicatorId): StructureId[] {
  const place = INDICATORS[indicator]?.place;
  return Array.isArray(place) ? place : [];
}

/** Where to point the camera for an insight: the structure, its region, or the whole body. */
function insightFocus(ids: StructureId[]): Focus {
  if (ids.length === 1) return { level: "structure", structure: ids[0] };
  const regions = new Set(ids.map((id) => STRUCTURES[id].region));
  if (regions.size === 1) return { level: "region", region: [...regions][0] };
  return { level: "body" };
}

export function buildBodyView(input: {
  focus: Focus;
  layers: Record<LayerId, LayerView>;
  glow: Glow;
  heartRate: number | null;
  insight: IndicatorId | null;
}): BodyView {
  const { focus, layers, glow, heartRate, insight } = input;
  const ids = insight ? insightStructures(insight) : [];

  if (ids.length === 0) {
    return {
      focus,
      layers,
      structures: Object.fromEntries(
        Object.entries(glow.structures).map(([id, status]) => [id, { status, opacity: null }]),
      ),
      wholeBody: glow.wholeBody,
      heartRate,
    };
  }

  const focused = new Set<StructureId>(ids);
  const relevantLayers = new Set(ids.map((id) => STRUCTURES[id].layer));
  const insightLayers = Object.fromEntries(
    (Object.keys(INSIGHT_FAINT) as LayerId[]).map((layer) => [
      layer,
      {
        visible: true,
        opacity:
          (layer === "organs" || layer === "brain") && relevantLayers.has(layer)
            ? INSIGHT_RELEVANT
            : INSIGHT_FAINT[layer],
      },
    ]),
  ) as Record<LayerId, LayerView>;

  return {
    focus: insightFocus(ids),
    layers: insightLayers,
    structures: Object.fromEntries(
      (Object.keys(glow.structures) as StructureId[]).map((id) => [
        id,
        focused.has(id)
          ? { status: glow.structures[id], opacity: 1 }
          : { status: null, opacity: INSIGHT_OTHER_STRUCTURE },
      ]),
    ),
    wholeBody: null,
    heartRate,
  };
}
