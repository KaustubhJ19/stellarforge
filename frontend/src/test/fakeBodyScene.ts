import type { BodyScene, BodySceneFactory, BodyView } from "../body/view";

/** Stands in for the WebGL body (jsdom has no GPU). Records what it was told to draw. */
export function fakeBodyScene() {
  const drawn: { view: BodyView | null } = { view: null };
  const factory: BodySceneFactory = (): BodyScene => ({
    apply(view) {
      drawn.view = view;
    },
    dispose() {},
  });
  return {
    factory,
    get view(): BodyView {
      if (!drawn.view) throw new Error("body was never drawn");
      return drawn.view;
    },
  };
}
