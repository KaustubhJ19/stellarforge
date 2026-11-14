import type { BodyScene, BodySceneEvents, BodySceneFactory, BodyView } from "../body/view";

/** Stands in for the WebGL body (jsdom has no GPU). Records what it was told to draw. */
export function fakeBodyScene({ loadsImmediately = true } = {}) {
  const drawn: { view: BodyView | null } = { view: null };
  let events: BodySceneEvents | null = null;
  const factory: BodySceneFactory = (_host, e): BodyScene => {
    events = e;
    if (loadsImmediately) e.onLoaded();
    return {
      apply(view) {
        drawn.view = view;
      },
      dispose() {},
    };
  };
  return {
    factory,
    get view(): BodyView {
      if (!drawn.view) throw new Error("body was never drawn");
      return drawn.view;
    },
    finishLoading: () => events!.onLoaded(),
    failLoading: (message: string) => events!.onError(message),
  };
}
