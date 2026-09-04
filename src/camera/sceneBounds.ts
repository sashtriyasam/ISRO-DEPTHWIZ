import * as THREE from "three";

export function computeDisplayBounds(meshes: THREE.Object3D[]): DisplayBoundsResult {
  const box = new THREE.Box3();
  for (const obj of meshes) {
    if (obj instanceof THREE.Mesh) {
      obj.geometry.computeBoundingBox();
      if (obj.geometry.boundingBox) {
        box.union(obj.geometry.boundingBox);
      }
    }
  }

  if (box.min.x === Infinity) {
    box.set(new THREE.Vector3(-1, -1, -1), new THREE.Vector3(1, 1, 1));
  }

  const center = new THREE.Vector3();
  box.getCenter(center);

  const size = new THREE.Vector3();
  box.getSize(size);

  const sphere = new THREE.Sphere();
  box.getBoundingSphere(sphere);

  return { center, size, sphere, box };
}

export interface DisplayBoundsResult {
  center: THREE.Vector3;
  size: THREE.Vector3;
  sphere: THREE.Sphere;
  box: THREE.Box3;
}

export function computeFrameCameraPosition(
  bounds: DisplayBoundsResult,
  fov: number,
  _aspect: number,
  direction?: THREE.Vector3
): { position: THREE.Vector3; target: THREE.Vector3 } {
  const maxDim = Math.max(bounds.size.x, bounds.size.y, bounds.size.z);
  const fovRad = (fov * Math.PI) / 180;
  const distance = (maxDim / 2) / Math.tan(fovRad / 2) * 1.5;

  const dir = direction ? direction.clone().normalize() : new THREE.Vector3(1, 0.8, 1).normalize();
  const position = bounds.center.clone().add(dir.multiplyScalar(distance));

  return { position, target: bounds.center.clone() };
}
