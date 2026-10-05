import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BackendBridge } from "../../backend/bridge";
import { SolarShadowPanel } from "./SolarShadowPanel";

const EMPTY_RESULT = { constraints: [], count: 0, refused_reason: "no metadata" };

afterEach(() => {
  vi.restoreAllMocks();
});

function inputs() {
  const [elevation, azimuth] = screen.getAllByRole("spinbutton");
  return { elevation, azimuth };
}

describe("SolarShadowPanel", () => {
  it("starts without invented sun angles", () => {
    render(<SolarShadowPanel inputPath="scene.tif" />);
    const { elevation, azimuth } = inputs();
    expect((elevation as HTMLInputElement).value).toBe("");
    expect((azimuth as HTMLInputElement).value).toBe("");
  });

  it("sends no sun angles when both are empty (backend reads metadata)", async () => {
    const spy = vi
      .spyOn(BackendBridge.prototype, "executeSolar")
      .mockResolvedValue(EMPTY_RESULT);
    render(<SolarShadowPanel inputPath="scene.tif" />);
    fireEvent.click(screen.getByRole("button", { name: "Run Solar Analysis" }));
    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    const config = spy.mock.calls[0][1];
    expect(config.sunElevationDeg).toBeUndefined();
    expect(config.sunAzimuthDeg).toBeUndefined();
    expect(config.assumeNorthUp).toBe(false);
  });

  it("refuses a single sun angle without calling the backend", () => {
    const spy = vi
      .spyOn(BackendBridge.prototype, "executeSolar")
      .mockResolvedValue(EMPTY_RESULT);
    render(<SolarShadowPanel inputPath="scene.tif" />);
    fireEvent.change(inputs().elevation, { target: { value: "40" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Solar Analysis" }));
    expect(screen.getByRole("alert").textContent).toMatch(/both sun elevation and azimuth/);
    expect(spy).not.toHaveBeenCalled();
  });

  it("passes explicit angles and the north-up declaration", async () => {
    const spy = vi
      .spyOn(BackendBridge.prototype, "executeSolar")
      .mockResolvedValue(EMPTY_RESULT);
    render(<SolarShadowPanel inputPath="scene.png" />);
    fireEvent.change(inputs().elevation, { target: { value: "0" } });
    fireEvent.change(inputs().azimuth, { target: { value: "135" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Run Solar Analysis" }));
    await waitFor(() => expect(spy).toHaveBeenCalledOnce());
    const config = spy.mock.calls[0][1];
    expect(config.sunElevationDeg).toBe(0);
    expect(config.sunAzimuthDeg).toBe(135);
    expect(config.assumeNorthUp).toBe(true);
  });
});
