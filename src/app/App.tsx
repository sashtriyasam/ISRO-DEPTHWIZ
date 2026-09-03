import { StrictMode, useCallback, useRef, useState } from "react";
import * as THREE from "three";
import { AppShell } from "../components/AppShell/AppShell";
import { Viewer, type ViewerHandle } from "../viewer/Viewer";
import { useTestFixture } from "../fixtures/useTestFixture";
import { StatusBar } from "../components/StatusBar/StatusBar";
import { CameraControls } from "../components/CameraControls/CameraControls";
import type { CameraMode } from "../camera/types";

export function App() {
  const fixture = useTestFixture();
  const viewerRef = useRef<ViewerHandle>(null);
  const [cameraMode, setCameraMode] = useState<CameraMode | null>("orbit");

  const handleCameraReady = useCallback(() => {
    setCameraMode("orbit");
  }, []);

  const handleFrameScene = useCallback(() => {
    const manager = viewerRef.current?.getCameraManager();
    if (!manager) return;
    const b = fixture.metadata.bounds;
    if (!b) return;
    const center = new THREE.Vector3(
      (b.minX + b.maxX) / 2,
      (b.minY + b.maxY) / 2,
      (b.minZ + b.maxZ) / 2
    );
    const size = new THREE.Vector3(
      b.maxX - b.minX,
      b.maxY - b.minY,
      b.maxZ - b.minZ
    );
    const box = new THREE.Box3(
      new THREE.Vector3(b.minX, b.minY, b.minZ),
      new THREE.Vector3(b.maxX, b.maxY, b.maxZ)
    );
    const sphere = new THREE.Sphere();
    box.getBoundingSphere(sphere);
    manager.frameBounds({ center, size, sphere, box });
  }, [fixture]);

  const handleReset = useCallback(() => {
    viewerRef.current?.getCameraManager()?.reset();
  }, []);

  return (
    <StrictMode>
      <AppShell
        header={<Header />}
        viewport={
          <Viewer
            ref={viewerRef}
            scene={fixture}
            onCameraReady={handleCameraReady}
          />
        }
        panel={
          <SidePanel>
            <CameraControls
              currentMode={cameraMode}
              onFrameScene={handleFrameScene}
              onReset={handleReset}
            />
          </SidePanel>
        }
        statusbar={<StatusBar />}
      />
    </StrictMode>
  );
}

function Header() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-md)", height: "100%" }}>
      <span style={{ fontWeight: 600, fontSize: "var(--font-size-md)" }}>DepthWizard</span>
      <span style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-xs)" }}>
        v0.1.0-dev
      </span>
    </div>
  );
}

function SidePanel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: "var(--spacing-md)", display: "flex", flexDirection: "column", gap: "var(--spacing-md)" }}>
      {children}
      <div>
        <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
          Scene Info
        </div>
        <div style={{ fontSize: "var(--font-size-sm)", color: "var(--color-text-secondary)" }}>
          Deterministic test fixture
        </div>
      </div>
      <div>
        <div style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
          Status
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)" }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-status-ok)" }} />
          <span style={{ fontSize: "var(--font-size-sm)", color: "var(--color-status-ok)" }}>Ready</span>
        </div>
      </div>
    </div>
  );
}
