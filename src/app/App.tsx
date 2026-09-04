import { StrictMode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { AppShell } from "../components/AppShell/AppShell";
import { Viewer, type ViewerHandle } from "../viewer/Viewer";
import { StatusBar } from "../components/StatusBar/StatusBar";
import { CameraControls } from "../components/CameraControls/CameraControls";
import { LayerControls } from "../components/LayerControls/LayerControls";
import { HeightExaggeration } from "../components/HeightExaggeration/HeightExaggeration";
import { InspectorPanel } from "../components/InspectorPanel/InspectorPanel";
import { MeasurementPanel } from "../components/MeasurementPanel/MeasurementPanel";
import { ProfilePanel } from "../components/ProfilePanel/ProfilePanel";
import { SceneInfo } from "../components/SceneInfo/SceneInfo";
import { ProcessingPanel } from "../components/ProcessingPanel/ProcessingPanel";
import { ArtifactLoader, FixtureSource } from "../artifact";
import { BackendArtifactSource } from "../backend/source";
import { runProcessingOperation, type ProcessingState } from "../processing";
import { createLayerState, setActiveLayer } from "../layers";
import { DEFAULT_EXAGGERATION } from "../display";
import { calculateMeasurement } from "../measurement/calculator";
import { generateProfile } from "../profile/sampler";
import { updateMeasurementGraphics, updateProfileGraphics } from "../viewer/Viewer";
import type { ArtifactState } from "../artifact/types";
import type { SceneArtifact } from "../types/scene";
import type { CameraMode } from "../camera/types";
import type { LayerId, LayerState } from "../layers/types";
import type { ExaggerationLevel } from "../display/types";
import type { InspectionResult, InspectionState } from "../inspection/types";
import type { MeasurementMode, MeasurementPoint, MeasurementState } from "../measurement/types";
import type { ProfileState } from "../profile/types";

export function App() {
  const [artifact, setArtifact] = useState<SceneArtifact | null>(null);
  const [artifactState, setArtifactState] = useState<ArtifactState>("idle");
  const [cameraMode, setCameraMode] = useState<CameraMode | null>(null);
  const [layerState, setLayerState] = useState<LayerState | null>(null);
  const [exaggeration, setExaggeration] = useState<ExaggerationLevel>(DEFAULT_EXAGGERATION);
  const [inspectionState, setInspectionState] = useState<InspectionState>({ status: "empty" });
  const [measurementMode, setMeasurementMode] = useState<MeasurementMode>("distance");
  const [measurementState, setMeasurementState] = useState<MeasurementState>({ status: "empty" });
  const [profileState, setProfileState] = useState<ProfileState>({ status: "empty" });
  const [sourceType, setSourceType] = useState<"fixture" | "backend">("fixture");
  const [processing, setProcessing] = useState<ProcessingState>({ status: "idle" });
  const viewerRef = useRef<ViewerHandle>(null);
  const loaderRef = useRef(new ArtifactLoader());
  const operationRef = useRef<{ sourceId: string; controller: AbortController } | null>(null);
  const operationCounterRef = useRef(0);
  const artifactRef = useRef<SceneArtifact | null>(null);
  artifactRef.current = artifact;

  const startOperation = useCallback((nextSourceType: "fixture" | "backend") => {
    const source = nextSourceType === "backend"
      ? new BackendArtifactSource()
      : new FixtureSource();
    const active = operationRef.current;
    if (active && active.sourceId === source.id) {
      return;
    }
    if (active) {
      active.controller.abort();
    }
    const controller = new AbortController();
    operationRef.current = { sourceId: source.id, controller };
    operationCounterRef.current += 1;
    const operationId = `op-${operationCounterRef.current}`;
    void (async () => {
      const hadArtifact = artifactRef.current !== null;
      if (!hadArtifact) {
        setArtifactState("loading");
      }
      const outcome = await runProcessingOperation(
        { status: "idle" },
        {
          source,
          loader: loaderRef.current,
          operationId,
          previousAvailable: hadArtifact,
          signal: controller.signal,
        },
        setProcessing
      );
      if (operationRef.current?.controller !== controller) {
        return;
      }
      operationRef.current = null;
      if (outcome.kind === "ready") {
        setArtifact(outcome.artifact);
        setLayerState(createLayerState(outcome.artifact));
        setArtifactState("ready");
      } else if (outcome.kind === "failed" && !hadArtifact) {
        setArtifactState("error");
      }
    })();
  }, []);

  useEffect(() => {
    startOperation(sourceType);
    return () => {
      operationRef.current?.controller.abort();
      operationRef.current = null;
    };
  }, [sourceType, startOperation]);

  const handleCancelOperation = useCallback(() => {
    operationRef.current?.controller.abort();
  }, []);

  const handleRetryOperation = useCallback(() => {
    startOperation(sourceType);
  }, [sourceType, startOperation]);

  const handleDismissOperation = useCallback(() => {
    setProcessing({ status: "idle" });
  }, []);

  const activeLayerId = useMemo(() => {
    return layerState?.activeLayerId ?? "dsm";
  }, [layerState]);

  const interactionMode = useMemo(() => {
    if (measurementState.status !== "empty") return "measure";
    if (profileState.status !== "empty") return "profile";
    return "inspect";
  }, [measurementState.status, profileState.status]);

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

  const handleLayerSelect = useCallback((layerId: LayerId) => {
    setLayerState((prev) => prev ? setActiveLayer(prev, layerId) : prev);
    viewerRef.current?.clearSelection();
    setInspectionState({ status: "empty" });
    setMeasurementState({ status: "empty" });
    viewerRef.current?.clearMeasurementGraphics();
    setProfileState({ status: "empty" });
    viewerRef.current?.clearProfileGraphics();
  }, []);

  const handleExaggerationChange = useCallback((level: ExaggerationLevel) => {
    setExaggeration(level);
  }, []);

  const getArtifactUnits = useCallback(() => {
    if (!artifact?.metadata.backend) return { units: "meters" as const, source: "fixture-coordinate-system" as const };
    return {
      units: artifact.metadata.backend.depth_scale === "metric" ? "meters" as const : "relative" as const,
      source: "backend" as const,
    };
  }, [artifact]);

  const handlePointSelected = useCallback((result: InspectionResult | null) => {
    if (!result) {
      setInspectionState({ status: "empty" });
    } else {
      setInspectionState({ status: "selected", result });
    }
  }, []);

  const handleClearInspection = useCallback(() => {
    viewerRef.current?.clearSelection();
    setInspectionState({ status: "empty" });
  }, []);

  const handleStartMeasurement = useCallback(() => {
    viewerRef.current?.clearSelection();
    setInspectionState({ status: "empty" });
    setProfileState({ status: "empty" });
    viewerRef.current?.clearProfileGraphics();
    setMeasurementState({ status: "selecting-first" });
  }, []);

  const handleMeasurementModeChange = useCallback((mode: MeasurementMode) => {
    setMeasurementMode(mode);
    if (measurementState.status !== "empty") {
      setMeasurementState({ status: "empty" });
      viewerRef.current?.clearMeasurementGraphics();
    }
  }, [measurementState.status]);

  const handleMeasurementPointSelected = useCallback((point: MeasurementPoint | null) => {
    if (!point) {
      setMeasurementState({ status: "empty" });
      viewerRef.current?.clearMeasurementGraphics();
      return;
    }

    setMeasurementState((prev) => {
      if (prev.status === "selecting-first") {
        return { status: "selecting-second", pointA: point };
      }
      if (prev.status === "selecting-second") {
        const result = calculateMeasurement(measurementMode, prev.pointA, point, getArtifactUnits());
        return { status: "completed", result };
      }
      return prev;
    });
  }, [measurementMode, getArtifactUnits]);

  useEffect(() => {
    if (measurementState.status === "selecting-first") {
      updateMeasurementGraphics(
        viewerRef.current as unknown as { threeScene: null; measurementMarkerA: null; measurementMarkerB: null; measurementLine: null; verticalScaleRef: number },
        null,
        null
      );
    } else if (measurementState.status === "selecting-second") {
      updateMeasurementGraphics(
        viewerRef.current as unknown as { threeScene: null; measurementMarkerA: null; measurementMarkerB: null; measurementLine: null; verticalScaleRef: number },
        measurementState.pointA,
        null
      );
    } else if (measurementState.status === "completed") {
      updateMeasurementGraphics(
        viewerRef.current as unknown as { threeScene: null; measurementMarkerA: null; measurementMarkerB: null; measurementLine: null; verticalScaleRef: number },
        measurementState.result.pointA,
        measurementState.result.pointB
      );
    }
  }, [measurementState]);

  const handleClearMeasurement = useCallback(() => {
    setMeasurementState({ status: "empty" });
    viewerRef.current?.clearMeasurementGraphics();
  }, []);

  const handleStartProfile = useCallback(() => {
    viewerRef.current?.clearSelection();
    setInspectionState({ status: "empty" });
    setMeasurementState({ status: "empty" });
    viewerRef.current?.clearMeasurementGraphics();
    setProfileState({ status: "selecting-first" });
  }, []);

  const handleProfilePointSelected = useCallback((point: MeasurementPoint | null) => {
    if (!point) {
      setProfileState({ status: "empty" });
      viewerRef.current?.clearProfileGraphics();
      return;
    }

    setProfileState((prev) => {
      if (prev.status === "selecting-first") {
        return { status: "selecting-second", pointA: point };
      }
      if (prev.status === "selecting-second") {
        const profile = generateProfile(
          prev.pointA,
          point,
          artifact?.elevation,
          artifact?.layers?.agl,
          artifact?.metadata.transform,
          {
            ...getArtifactUnits(),
            elevationSemantics: artifact?.metadata.backend?.elevation_semantics,
          }
        );
        return { status: "completed", profile };
      }
      return prev;
    });
  }, [artifact, getArtifactUnits]);

  useEffect(() => {
    if (profileState.status === "selecting-first") {
      updateProfileGraphics(
        viewerRef.current as unknown as { threeScene: null; profileMarkerA: null; profileMarkerB: null; profileLine: null; verticalScaleRef: number },
        null,
        null
      );
    } else if (profileState.status === "selecting-second") {
      updateProfileGraphics(
        viewerRef.current as unknown as { threeScene: null; profileMarkerA: null; profileMarkerB: null; profileLine: null; verticalScaleRef: number },
        profileState.pointA,
        null
      );
    } else if (profileState.status === "completed") {
      updateProfileGraphics(
        viewerRef.current as unknown as { threeScene: null; profileMarkerA: null; profileMarkerB: null; profileLine: null; verticalScaleRef: number },
        profileState.profile.pointA,
        profileState.profile.pointB
      );
    }
  }, [profileState]);

  const handleClearProfile = useCallback(() => {
    setProfileState({ status: "empty" });
    viewerRef.current?.clearProfileGraphics();
  }, []);

  return (
    <StrictMode>
      <AppShell
        header={<Header />}
        viewport={
          artifact && layerState ? (
            <Viewer
              ref={viewerRef}
              scene={artifact}
              layerId={activeLayerId}
              verticalScale={exaggeration}
              interactionMode={interactionMode}
              onCameraReady={handleCameraReady}
              onPointSelected={handlePointSelected}
              onMeasurementPointSelected={handleMeasurementPointSelected}
              onProfilePointSelected={handleProfilePointSelected}
            />
          ) : (
            <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-text-muted)" }}>
              {artifactState === "loading" ? "Loading artifact..." : artifactState === "error" ? "Failed to load artifact" : ""}
            </div>
          )
        }
        panel={
          <SidePanel>
            <SourceControl
              sourceType={sourceType}
              onSourceChange={setSourceType}
              artifact={artifact}
              state={artifactState}
            />
            <ProcessingPanel
              state={processing}
              onCancel={handleCancelOperation}
              onRetry={handleRetryOperation}
              onDismiss={handleDismissOperation}
            />
            <CameraControls
              currentMode={cameraMode}
              onFrameScene={handleFrameScene}
              onReset={handleReset}
            />
            <HeightExaggeration
              current={exaggeration}
              onChange={handleExaggerationChange}
            />
            {layerState && (
              <LayerControls
                layerState={layerState}
                onLayerSelect={handleLayerSelect}
              />
            )}
            <MeasurementPanel
              state={measurementState}
              mode={measurementMode}
              onModeChange={handleMeasurementModeChange}
              onStartMeasurement={handleStartMeasurement}
              onClear={handleClearMeasurement}
            />
            <ProfilePanel
              state={profileState}
              onStartProfile={handleStartProfile}
              onClear={handleClearProfile}
            />
            <InspectorPanel
              state={inspectionState}
              metadata={artifact?.metadata}
              onClear={handleClearInspection}
            />
            <SceneInfo
              artifact={artifact}
              state={artifactState}
              sourceLabel={
                artifact?.metadata.backend
                  ? "Synthetic Development Backend"
                  : artifact
                    ? "Development Fixture"
                    : sourceType === "backend"
                      ? "Synthetic Development Backend"
                      : "Development Fixture"
              }
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

function SourceControl({
  sourceType,
  onSourceChange,
  artifact,
  state,
}: {
  sourceType: "fixture" | "backend";
  onSourceChange: (type: "fixture" | "backend") => void;
  artifact: SceneArtifact | null;
  state: ArtifactState;
}) {
  return (
    <div className="panel-section">
      <div className="panel-section-header">Source</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
        <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-xs)", cursor: "pointer" }}>
          <input
            type="radio"
            name="source"
            checked={sourceType === "fixture"}
            onChange={() => onSourceChange("fixture")}
          />
          <span>Development Fixture</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "var(--spacing-xs)", cursor: "pointer" }}>
          <input
            type="radio"
            name="source"
            checked={sourceType === "backend"}
            onChange={() => onSourceChange("backend")}
          />
          <span>Synthetic Development Backend</span>
        </label>
      </div>
      {state === "ready" && artifact?.metadata.backend && (
        <div style={{ marginTop: "var(--spacing-xs)", fontSize: "var(--font-size-xs)", color: "var(--color-text-muted)" }}>
          <div>Backend: {artifact.metadata.backend.model_name}</div>
          <div>Version: {artifact.metadata.backend.model_version ?? "unknown"}</div>
          <div>Scale: {artifact.metadata.backend.depth_scale}</div>
          <div>Semantics: {artifact.metadata.backend.elevation_semantics}</div>
          {artifact.metadata.backend.depth_scale === "relative" && (
            <div style={{ color: "var(--color-warning)" }}>Relative depth (not metric)</div>
          )}
        </div>
      )}
    </div>
  );
}
