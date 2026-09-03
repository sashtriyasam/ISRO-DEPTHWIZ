import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as THREE from "three";
import { CameraManager } from "./CameraManager";

function createMockDomElement(): HTMLElement {
  const mockDocument = {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  const el = {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    clientWidth: 800,
    clientHeight: 600,
    ownerDocument: { defaultView: null },
    getRootNode: () => mockDocument,
    style: { touchAction: "" },
    tagName: "DIV",
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }),
  } as unknown as HTMLElement;
  return el;
}

describe("CameraManager", () => {
  let camera: THREE.PerspectiveCamera;
  let domElement: HTMLElement;
  let manager: CameraManager;

  beforeEach(() => {
    camera = new THREE.PerspectiveCamera(50, 800 / 600, 0.1, 100);
    camera.position.set(6, 5, 6);
    domElement = createMockDomElement();
    manager = new CameraManager(camera, domElement);
  });

  afterEach(() => {
    manager.dispose();
  });

  it("activates orbit mode", () => {
    const bounds = {
      center: new THREE.Vector3(),
      size: new THREE.Vector3(2, 1, 2),
      sphere: new THREE.Sphere(),
      box: new THREE.Box3(),
    };
    manager.activate("orbit", new THREE.Vector3(), bounds);
    expect(manager.getMode()).toBe("orbit");
  });

  it("returns null mode when no controller active", () => {
    expect(manager.getMode()).toBeNull();
  });

  it("setInitial stores initial position", () => {
    const pos = new THREE.Vector3(10, 8, 10);
    const target = new THREE.Vector3(0, 0, 0);
    manager.setInitial(pos, target);
    manager.reset();
    expect(camera.position.x).toBeCloseTo(10);
    expect(camera.position.y).toBeCloseTo(8);
    expect(camera.position.z).toBeCloseTo(10);
  });

  it("reset restores initial position", () => {
    manager.setInitial(new THREE.Vector3(5, 3, 5), new THREE.Vector3());
    camera.position.set(100, 100, 100);
    manager.reset();
    expect(camera.position.x).toBeCloseTo(5);
    expect(camera.position.y).toBeCloseTo(3);
    expect(camera.position.z).toBeCloseTo(5);
  });

  it("resize updates camera aspect", () => {
    manager.resize(1600, 900);
    expect(camera.aspect).toBeCloseTo(1600 / 900);
  });

  it("getState returns null without controller", () => {
    expect(manager.getState()).toBeNull();
  });

  it("dispose cleans up", () => {
    manager.dispose();
    expect(manager.getMode()).toBeNull();
  });
});
