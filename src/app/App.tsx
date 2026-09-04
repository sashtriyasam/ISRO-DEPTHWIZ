import { StrictMode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { AppShell } from "../components/AppShell/AppShell";
import { Viewer, type ViewerHandle } from "../viewer/Viewer";
import { StatusBar } from "../components/StatusBar/StatusBar";
import { CameraControls } from "../components/CameraControls/CameraControls";
import { FlythroughPanel } from "../components/FlythroughPanel/FlythroughPanel";
import {
  DEFAULT_PLAYBACK_SPEED,
  DEFAULT_SEGMENT_DURATION_MS,
  trajectoryStatusForCount,
  type FlythroughWaypoint,
  type PlaybackSpeed,
  type PlaybackStatus,
} from "../flythrough/types";
import { previewPoints } from "../flythrough/trajectory";
import { LayerControls } from "../components/LayerControls/LayerControls";
import { RenderingControls } from "../components/RenderingControls/RenderingControls";
import { HeightExaggeration } from "../components/HeightExaggeration/HeightExaggeration";
import { InspectorPanel } from "../components/InspectorPanel/InspectorPanel";
import { MeasurementPanel } from "../components/MeasurementPanel/MeasurementPanel";
import { ProfilePanel } from "../components/ProfilePanel/ProfilePanel";
import { MetadataPanel } from "../components/MetadataPanel/MetadataPanel";
import { SceneInfo } from "../components/SceneInfo/SceneInfo";
import { ProcessingPanel } from "../components/ProcessingPanel/ProcessingPanel";
import { InputWorkspace } from "../components/InputWorkspace/InputWorkspace";
import { ArtifactLoader } from "../artifact";
import type { ArtifactSource } from "../artifact/types";
import { runProcessingOperation, type ProcessingState } from "../processing";
import { createLayerState, setActiveLayer } from "../layers";
import { DEFAULT_EXAGGERATION } from "../display";
import { calculateMeasurement } from "../measurement/calculator";
import { generateProfile } from "../profile/sampler";
import { updateMeasurementGraphics, updateProfileGraphics } from "../viewer/Viewer";
import type { ArtifactState } from "../artifact/types";
import type { SceneArtifact } from "../types/scene";
import type { CameraMode } from "../camera/types";
import type { LayerId, LayerState, RenderingMode } from "../layers/types";
import { DEFAULT_RENDERING_MODE } from "../layers";
import type { ExaggerationLevel } from "../display/types";
import type { InspectionResult, InspectionState } from "../inspection/types";
import type { MeasurementMode, MeasurementPoint, MeasurementState } from "../measurement/types";
import type { ProfileState } from "../profile/types";

export function App() {
  const [artifact, setArtifact] = useState<SceneArtifact | null>(null);
  const [artifactState, setArtifactState] = useState<ArtifactState>("idle");
  const [cameraMode, setCameraMode] = useState<CameraMode | null>(null);
  const [layerState, setLayerState] = useState<LayerState | null>(null);
  const [renderingMode, setRenderingMode] = useState<RenderingMode>(DEFAULT_RENDERING_MODE);
  const [exaggeration, setExaggeration] = useState<ExaggerationLevel>(DEFAULT_EXAGGERATION);
  const [inspectionState, setInspectionState] = useState<InspectionState>({ status: "empty" });
  const [measurementMode, setMeasurementMode] = useState<MeasurementMode>("distance");
  const [measurementState, setMeasurementState] = useState<MeasurementState>({ status: "empty" });
  const [profileState, setProfileState] = useState<ProfileState>({ status: "empty" });
  const [processing, setProcessing] = useState<ProcessingState>({ status: "idle" });
  const [waypoints, setWaypoints] = useState<FlythroughWaypoint[]>([]);
  const [playbackStatus, setPlaybackStatus] = useState<PlaybackStatus>("idle");
  const [playbackSpeed, setPlaybackSpeed] = useState<PlaybackSpeed>(DEFAULT_PLAYBACK_SPEED);
  const [flythroughIndex, setFlythroughIndex] = useState(0);
  const waypointCounterRef = useRef(0);
  const trajectoryCounterRef = useRef(0);
  const playbackStatusRef = useRef<PlaybackStatus>("idle");
  playbackStatusRef.current = playbackStatus;
  const viewerRef = useRef<ViewerHandle>(null);
  const loaderRef = useRef(new ArtifactLoader());
  const operationRef = useRef<{ sourceId: string; controller: AbortController } | null>(null);
  const operationCounterRef = useRef(0);
  const pendingRef = useRef<ArtifactSource | null>(null);
  const artifactRef = useRef<SceneArtifact | null>(null);
  artifactRef.current = artifact;

  const clearAnalysisState = useCallback(() => {
    viewerRef.current?.clearSelection();
    setInspectionState({ status: "empty" });
    setMeasurementState({ status: "empty" });
    viewerRef.current?.clearMeasurementGraphics();
    setProfileState({ status: "empty" });
    viewerRef.current?.clearProfileGraphics();
  }, []);

  const startOperation = useCallback((source: ArtifactSource) => {
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
        clearAnalysisState();
        viewerRef.current?.setFlythroughPreview(null);
        setWaypoints([]);
        setPlaybackStatus("idle");
        setFlythroughIndex(0);
      } else if (outcome.kind === "failed" && !hadArtifact) {
        setArtifactState("error");
      }
    })();
  }, [clearAnalysisState]);

  useEffect(() => {
    return () => {
      operationRef.current?.controller.abort();
      operationRef.current = null;
    };
  }, []);

  const handleGenerate = useCallback((source: ArtifactSource) => {
    pendingRef.current = source;
    startOperation(source);
  }, [startOperation]);

  const handleCancelOperation = useCallback(() => {
    operationRef.current?.controller.abort();
  }, []);

  const handleRetryOperation = useCallback(() => {
    const pending = pendingRef.current;
    if (pending) {
      startOperation(pending);
    }
  }, [startOperation]);

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

  const desiredCameraModeRef = useRef<CameraMode>("orbit");

  const applyCameraMode = useCallback((mode: CameraMode) => {
    desiredCameraModeRef.current = mode;
    setCameraMode(mode);
    viewerRef.current?.setCameraMode(mode);
  }, []);

  const waypointsRef = useRef<FlythroughWaypoint[]>([]);
  waypointsRef.current = waypoints;

  const syncFlythroughPreview = useCallback((points: FlythroughWaypoint[]) => {
    if (points.length >= 2) {
      viewerRef.current?.setFlythroughPreview(
        previewPoints({ id: "preview", waypoints: points, segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS }).map((p) => ({ x: p.x, y: p.y, z: p.z }))
      );
    } else {
      viewerRef.current?.setFlythroughPreview(null);
    }
  }, []);

  const handleCameraReady = useCallback(() => {
    const desired = desiredCameraModeRef.current;
    setCameraMode(desired);
    viewerRef.current?.setCameraMode(desired);
    if (playbackStatusRef.current === "playing" || playbackStatusRef.current === "paused") {
      setPlaybackStatus(waypointsRef.current.length >= 2 ? "ready" : "idle");
      setFlythroughIndex(0);
    }
    syncFlythroughPreview(waypointsRef.current);
  }, [syncFlythroughPreview]);

  const handleCameraModeChange = useCallback((mode: CameraMode) => {
    if (mode === "first-person") {
      viewerRef.current?.clearSelection();
      setInspectionState({ status: "empty" });
      setMeasurementState({ status: "empty" });
      viewerRef.current?.clearMeasurementGraphics();
      setProfileState({ status: "empty" });
      viewerRef.current?.clearProfileGraphics();
    }
    applyCameraMode(mode);
  }, [applyCameraMode]);

  useEffect(() => {
    if (cameraMode !== "first-person") {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code === "Escape") {
        applyCameraMode("orbit");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [cameraMode, applyCameraMode]);

  const playbackSpeedRef = useRef<PlaybackSpeed>(DEFAULT_PLAYBACK_SPEED);
  playbackSpeedRef.current = playbackSpeed;

  const handleAddWaypoint = useCallback(() => {
    if (playbackStatusRef.current === "playing") {
      return;
    }
    const manager = viewerRef.current?.getCameraManager();
    if (!manager) {
      return;
    }
    const state = manager.getState();
    if (!state) {
      return;
    }
    waypointCounterRef.current += 1;
    const waypoint: FlythroughWaypoint = {
      id: `wp-${waypointCounterRef.current}`,
      position: { x: state.position.x, y: state.position.y, z: state.position.z },
      target: { x: state.target.x, y: state.target.y, z: state.target.z },
    };
    const next = [...waypointsRef.current, waypoint];
    setWaypoints(next);
    syncFlythroughPreview(next);
    setPlaybackStatus(trajectoryStatusForCount(next.length));
  }, [syncFlythroughPreview]);

  const handleRemoveWaypoint = useCallback((id: string) => {
    if (playbackStatusRef.current === "playing") {
      return;
    }
    const next = waypointsRef.current.filter((waypoint) => waypoint.id !== id);
    setWaypoints(next);
    syncFlythroughPreview(next);
    setPlaybackStatus(trajectoryStatusForCount(next.length));
    setFlythroughIndex(0);
  }, [syncFlythroughPreview]);

  const handleClearWaypoints = useCallback(() => {
    if (playbackStatusRef.current === "playing") {
      return;
    }
    viewerRef.current?.setFlythroughPreview(null);
    setWaypoints([]);
    setPlaybackStatus("idle");
    setFlythroughIndex(0);
  }, []);

  const handlePlayFlythrough = useCallback(() => {
    const points = waypointsRef.current;
    if (points.length < 2) {
      return;
    }
    trajectoryCounterRef.current += 1;
    const started = viewerRef.current?.startFlythrough(
      {
        id: `traj-${trajectoryCounterRef.current}`,
        waypoints: points,
        segmentDurationMs: DEFAULT_SEGMENT_DURATION_MS,
      },
      {
        speed: playbackSpeedRef.current,
        onWaypointIndex: (index) => setFlythroughIndex(index),
        onCompleted: () => {
          viewerRef.current?.stopFlythrough();
          setPlaybackStatus("completed");
        },
      }
    );
    if (started) {
      setFlythroughIndex(0);
      setPlaybackStatus("playing");
    }
  }, []);

  const handlePauseFlythrough = useCallback(() => {
    viewerRef.current?.pauseFlythrough();
    setPlaybackStatus("paused");
  }, []);

  const handleResumeFlythrough = useCallback(() => {
    viewerRef.current?.resumeFlythrough();
    setPlaybackStatus("playing");
  }, []);

  const handleStopFlythrough = useCallback(() => {
    viewerRef.current?.stopFlythrough();
    setPlaybackStatus(waypointsRef.current.length >= 2 ? "ready" : "idle");
    setFlythroughIndex(0);
  }, []);

  const handleResetFlythrough = useCallback(() => {
    viewerRef.current?.resetFlythrough();
    setPlaybackStatus(waypointsRef.current.length >= 2 ? "ready" : "idle");
    setFlythroughIndex(0);
  }, []);

  const handleFlythroughSpeed = useCallback((speed: PlaybackSpeed) => {
    setPlaybackSpeed(speed);
    viewerRef.current?.setFlythroughSpeed(speed);
  }, []);

  useEffect(() => {
    if (playbackStatus !== "playing" && playbackStatus !== "paused") {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code === "Escape") {
        viewerRef.current?.stopFlythrough();
        setPlaybackStatus(waypointsRef.current.length >= 2 ? "ready" : "idle");
        setFlythroughIndex(0);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [playbackStatus]);

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
              {artifactState === "loading"
                ? "Generating terrain…"
                : artifactState === "error"
                  ? "Terrain generation failed — select an input to try again"
                  : "Select an input file or the development fixture to begin"}
            </div>
          )
        }
        panel={
          <SidePanel>
            <InputWorkspace
              processingRunning={processing.status === "running"}
              onGenerate={handleGenerate}
            />
            <ProcessingPanel
              state={processing}
              resultMeta={
                processing.status === "ready" && artifact?.metadata.backend
                  ? {
                      backend: artifact.metadata.backend.model_name,
                      target: artifact.metadata.backend.elevation_semantics,
                    }
                  : null
              }
              onCancel={handleCancelOperation}
              onRetry={handleRetryOperation}
              onDismiss={handleDismissOperation}
            />
            <CameraControls
              currentMode={cameraMode}
              onModeChange={handleCameraModeChange}
              onFrameScene={handleFrameScene}
              onReset={handleReset}
              navigationLocked={playbackStatus === "playing" || playbackStatus === "paused"}
            />
            <FlythroughPanel
              waypoints={waypoints}
              status={playbackStatus}
              speed={playbackSpeed}
              currentIndex={flythroughIndex}
              canCapture={cameraMode !== "trajectory" && artifact !== null}
              navigationLocked={playbackStatus === "playing" || playbackStatus === "paused"}
              onAddWaypoint={handleAddWaypoint}
              onRemoveWaypoint={handleRemoveWaypoint}
              onClear={handleClearWaypoints}
              onPlay={handlePlayFlythrough}
              onPause={handlePauseFlythrough}
              onResume={handleResumeFlythrough}
              onStop={handleStopFlythrough}
              onReset={handleResetFlythrough}
              onSpeedChange={handleFlythroughSpeed}
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
            <RenderingControls
              currentMode={renderingMode}
              onModeChange={(mode) => {
                setRenderingMode(mode);
                viewerRef.current?.setRenderingMode(mode);
              }}
            />
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
            <MetadataPanel
              artifact={artifact}
              activeLayerId={activeLayerId}
            />
            <SceneInfo
              artifact={artifact}
              state={artifactState}
              sourceLabel={
                artifact?.metadata.backend
                  ? "Synthetic Development Backend"
                  : artifact
                    ? "Development Fixture"
                    : "No input selected"
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

