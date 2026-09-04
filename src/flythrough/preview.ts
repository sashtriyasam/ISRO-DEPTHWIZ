import * as THREE from "three";
import type { WaypointPosition } from "./types";

export const PREVIEW_COMPLETED_COLOR = 0x2a6a8a;
export const PREVIEW_FUTURE_COLOR = 0x44ccff;
export const PREVIEW_START_COLOR = 0x44ff88;
export const PREVIEW_END_COLOR = 0xff6666;
export const PREVIEW_MIDDLE_COLOR = 0x44ccff;

export interface PreviewBuild {
  group: THREE.Group;
  waypointCount: number;
}

function toVector(point: WaypointPosition): THREE.Vector3 {
  return new THREE.Vector3(point.x, point.y, point.z);
}

function makeLine(points: THREE.Vector3[], color: number, opacity: number): THREE.Line {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity,
    depthTest: false,
  });
  const line = new THREE.Line(geometry, material);
  line.renderOrder = 999;
  line.frustumCulled = false;
  line.userData.pickable = false;
  return line;
}

function makeMarker(
  position: THREE.Vector3,
  color: number,
  radius: number,
  highlighted: boolean
): THREE.Mesh {
  const geometry = new THREE.SphereGeometry(radius, 12, 12);
  const material = new THREE.MeshBasicMaterial({ color, depthTest: false, transparent: true, opacity: 0.95 });
  const marker = new THREE.Mesh(geometry, material);
  marker.position.copy(position);
  marker.scale.setScalar(highlighted ? 1.6 : 1);
  marker.renderOrder = 1000;
  marker.userData.pickable = false;
  return marker;
}

export function buildPreviewGroup(
  points: WaypointPosition[],
  currentIndex: number,
  markerRadius: number
): PreviewBuild | null {
  if (points.length < 2) {
    return null;
  }
  const vectors = points.map(toVector);
  const group = new THREE.Group();
  group.userData.pickable = false;

  const split = Math.max(0, Math.min(vectors.length - 1, currentIndex));
  const completed = vectors.slice(0, split + 1);
  const future = vectors.slice(split);
  if (completed.length >= 2) {
    group.add(makeLine(completed, PREVIEW_COMPLETED_COLOR, 0.45));
  }
  if (future.length >= 2) {
    group.add(makeLine(future, PREVIEW_FUTURE_COLOR, 0.9));
  }

  vectors.forEach((position, index) => {
    const color =
      index === 0
        ? PREVIEW_START_COLOR
        : index === vectors.length - 1
          ? PREVIEW_END_COLOR
          : PREVIEW_MIDDLE_COLOR;
    group.add(makeMarker(position, color, markerRadius, index === currentIndex));
  });

  return { group, waypointCount: vectors.length };
}

export function disposePreviewGroup(group: THREE.Group): void {
  group.traverse((child) => {
    if (child instanceof THREE.Line || child instanceof THREE.Mesh) {
      child.geometry.dispose();
      const material = child.material as THREE.Material | THREE.Material[];
      if (Array.isArray(material)) {
        for (const entry of material) {
          entry.dispose();
        }
      } else {
        material.dispose();
      }
    }
  });
}
