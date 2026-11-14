import { render } from "@testing-library/react";
import { App } from "../App";
import { marsReplay, replayWith } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { ReplayFile } from "../contracts";

function drawn(replay: ReplayFile) {
  const body = fakeBodyScene();
  render(<App replay={replay} bodyScene={body.factory} />);
  return body.view;
}

describe("heart and lungs move with the real rates", () => {
  it("beats the heart at the latest heart-rate Reading", () => {
    expect(drawn(marsReplay()).heartRate).toBe(70);
  });

  it("keeps the heart still when there is no heart-rate Reading", () => {
    expect(drawn(replayWith([{ indicator: "stress", value: 30, state: "green" }])).heartRate).toBeNull();
  });

  it("breathes the lungs at the latest respiratory-rate Reading", () => {
    expect(drawn(replayWith([{ indicator: "respiratory_rate", value: 15, state: "green" }])).breathRate).toBe(15);
  });
});
