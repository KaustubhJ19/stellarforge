import { render } from "@testing-library/react";
import { App } from "../App";
import { marsMission, missionWith } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { Mission } from "../test/replay";

function drawn(mission: Mission) {
  const body = fakeBodyScene();
  render(<App {...mission} bodyScene={body.factory} />);
  return body.view;
}

describe("heart and lungs move with the real rates", () => {
  it("beats the heart at the latest heart-rate Reading", () => {
    expect(drawn(marsMission()).heartRate).toBe(70);
  });

  it("keeps the heart still when there is no heart-rate Reading", () => {
    expect(drawn(missionWith([{ indicator: "stress", value: 30, status: "green" }])).heartRate).toBeNull();
  });

  it("breathes the lungs at the latest respiratory-rate Reading", () => {
    expect(drawn(missionWith([{ indicator: "respiration_rate", value: 15, status: "green" }])).breathRate).toBe(15);
  });
});
