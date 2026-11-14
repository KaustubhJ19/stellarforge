import { render, screen } from "@testing-library/react";
import { App } from "./App";
import { marsMission } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";

describe("runs from replay files with no server", () => {
  it("renders the whole home screen without any network call", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("service is stopped"));
    const xhrSpy = vi.spyOn(XMLHttpRequest.prototype, "open").mockImplementation(() => {
      throw new Error("service is stopped");
    });

    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);

    expect(screen.getByRole("region", { name: "Mission" })).toHaveTextContent("28.5 min");
    expect(screen.getByRole("region", { name: "Physical health" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Trends" })).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(xhrSpy).not.toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});
