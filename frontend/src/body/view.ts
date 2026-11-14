import type { Status } from "../contracts";

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

/** Everything the 3D body must draw. The renderer applies it; it decides nothing. */
export interface BodyView {
  layers: Record<LayerId, LayerView>;
  structures: Record<string, StructureView>;
  /** Beats per minute for the heart, or null for still. */
  heartRate: number | null;
}

/** The drawing surface behind the body: Three.js in the app, a recorder in tests. */
export interface BodyScene {
  apply(view: BodyView): void;
  dispose(): void;
}

export type BodySceneFactory = (host: HTMLElement) => BodyScene;
