import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { AppShell } from "../components/AppShell/AppShell";
import { Viewer, type ViewerHandle } from "../viewer/Viewer";
import { StatusBar } from "../components/StatusBar/StatusBar";
import { CameraControls } from "../components/CameraControls/CameraControls";
import { SceneInfo } from "../components/SceneInfo/SceneInfo";
import { ArtifactLoader, FixtureSource } from "../artifact";
import type { ArtifactState } from "../artifact/types";
import type { SceneArtifact } from "../types/scene";
import type { CameraMode } from "../camera/types";

export function App() {
  const [artifact, setArtifact] = useState<SceneArtifact | null>(null);
  const [artifactState, setArtifactState] = useState<ArtifactState>("idle");
  const [cameraMode, setCameraMode] = useState<CameraMode | null>(null);
  const viewerRef = useRef<ViewerHandle>(null);
  const loaderRef = useRef(new ArtifactLoader());

  useEffect(() => {
    const source = new FixtureSource();
    setArtifactState("loading");
    loaderRef.current.load(source).then(
      (result) => {
        setArtifact(result.artifact);
        setArtifactState("ready");
      },
      (err) => {
        console.error("Failed to load fixture:", err);
        setArtifactState("error");
      }
    );
  }, []);

  const handleCameraReady = useCallback(() => {
    setCameraMode("orbit");
  }, []);

  const handleFrameScene = useCallback(() => {
    const manager = viewerRef.current?.getCameraManager();
    if (!manager || !artifact?.metadata.bounds) return;
    const b = artifact.metadata.bounds;
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
  }, [artifact]);

  const handleReset = useCallback(() => {
    viewerRef.current?.getCameraManager()?.reset();
  }, []);

  return (
    <StrictMode>
      <AppShell
        header={<Header />}
        viewport={
          artifact ? (
            <Viewer
              ref={viewerRef}
              scene={artifact}
              onCameraReady={handleCameraReady}
            />
          ) : (
            <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-text-muted)" }}>
              {artifactState === "loading" ? "Loading artifact..." : artifactState === "error" ? "Failed to load artifact" : ""}
            </div>
          )
        }
        panel={
          <SidePanel>
            <CameraControls
              currentMode={cameraMode}
              onFrameScene={handleFrameScene}
              onReset={handleReset}
            />
            <SceneInfo
              artifact={artifact}
              state={artifactState}
              sourceLabel="Development Fixture"
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
    </div>
  );
}
