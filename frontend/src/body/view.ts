import type { Status } from "../contracts";
import type { RegionId, StructureId } from "./structures";

export const LAYERS = ["muscles", "skeleton", "vessels", "organs", "brain"] as const;
export type LayerId = (typeof LAYERS)[number];

export const LAYER_LABEL: Record<LayerId, string> = {
  muscles: "Muscles",
  skeleton: "Skeleton",
  vessels: "Vessels",
  organs: "Organs",
  brain: "Brain",
};

export interface LayerView {
  visible: boolean;
  /** 0 (invisible) … 1 (solid) */
  opacity: number;
}

export interface StructureView {
  /** Status glow; null = no glow. */
  status: Status | null;
  /** Opacity override (insight view); null = follow the layer. */
  opacity: number | null;
}

/** Zoom level: whole body → region → one structure. */
export type Focus =
  | { level: "body" }
  | { level: "region"; region: RegionId }
  | { level: "structure"; structure: StructureId };

/** Everything the 3D body must draw. The renderer applies it; it decides nothing. */
/** Which body model to draw, from the Crew record. */
export type BodyModel = "male" | "female";

export interface BodyView {
  model: BodyModel;
  focus: Focus;
  layers: Record<LayerId, LayerView>;
  structures: Record<string, StructureView>;
  /** Whole-body Status tint (radiation dose, body temperature); null = none. */
  wholeBody: Status | null;
  /** Beats per minute for the heart, or null for still. */
  heartRate: number | null;
  /** Breaths per minute for the lungs, or null for still. */
  breathRate: number | null;
}

/** The drawing surface behind the body: Three.js in the app, a recorder in tests. */
export interface BodyScene {
  apply(view: BodyView): void;
  dispose(): void;
}

/** How the scene reports that its model finished (or failed) loading. */
export interface BodySceneEvents {
  onLoaded(): void;
  onError(message: string): void;
}

export type BodySceneFactory = (host: HTMLElement, events: BodySceneEvents) => BodyScene;
