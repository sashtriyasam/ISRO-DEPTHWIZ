#Requires -Version 5.1
<#
.SYNOPSIS
  Bootstrap DepthWizard GitHub issues (master + 11 epics + 15 SIH
  requirements + 11 release gates + final acceptance gate).
.DESCRIPTION
  The GitHub MCP token available during the bootstrap run was read-only
  (issue creation returned 403), so no issue could be created via MCP.
  Run this script once with a token/scope that allows issue creation
  (gh auth login; classic scope repo or fine-grained Issues:write on
  sashtriyasam/ISRO-DEPTHWIZ). Idempotent: existing titles are skipped.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/bootstrap-control-plane-issues.ps1
#>

$ErrorActionPreference = "Stop"
$Repo = "sashtriyasam/ISRO-DEPTHWIZ"

function Get-ExistingTitles {
  $titles = @{}
  $page = 1
  while ($true) {
    $rows = gh issue list --repo $Repo --state all --limit 100 --page $page `
      --json title 2>$null | ConvertFrom-Json
    if (-not $rows -or $rows.Count -eq 0) { break }
    foreach ($r in $rows) { $titles[$r.title] = $true }
    if ($rows.Count -lt 100) { break }
    $page += 1
  }
  return $titles
}

$Issues = New-Object System.Collections.ArrayList

function Add-Issue($title, $body) {
  [void]$script:Issues.Add(@{ title = $title; body = $body })
}

function Add-Simple($title, $desc, $owner, $track, $area, $pri, $ver, $ms) {
  $body = $desc + "`nProject: Owner=" + $owner + " | Track=" + $track + `
    " | SIH Area=" + $area + " | Priority=" + $pri + `
    " | Verification=" + $ver + " | Release Gate=No | Status=Backlog" + `
    " | Milestone=" + $ms
  Add-Issue $title $body
}

# ---------------------------------------------------------------- master
Add-Issue "SIH 26175 - Complete End-to-End Software System" @'
# Objective

Deliver the complete standalone DepthWizard software system required by SIH Problem Statement 26175.

# Required pipeline

Single-view optical RGB remote-sensing image -> input inspection -> depth/geometric representation -> calibration/reference where required -> rDSM/DSM -> terrain mesh -> RGB texture projection -> interactive 3D -> analysis/measurement -> validation -> standalone deployment.

# Input path A

PNG/JPG/non-georeferenced RGB. Required semantics: relative geometry -> rDSM -> mesh -> texture -> visualization. Must NOT fabricate CRS, geographic coordinates, absolute metres, or metric elevation.

# Input path B

GeoTIFF / georeferenced RGB. Required semantics: RGB -> relative geometry -> reference/calibration -> metric DSM when justified -> geospatial output -> mesh -> interactive visualization. Preserve CRS, affine transform, spatial metadata, provenance. Metric claims require valid calibration/reference evidence.

# Final acceptance

Input: [ ] PNG [ ] JPG [ ] TIFF [ ] GeoTIFF [ ] metadata validation
Elevation: [ ] relative depth [ ] rDSM [ ] calibrated metric DSM where justified [ ] standard geospatial export [ ] nodata/validity semantics [ ] provenance
3D: [ ] terrain mesh [ ] RGB texture projection [ ] correct spatial geometry [ ] scene generation [ ] flythrough
Interaction: [ ] orbit [ ] first-person [ ] aerial [ ] height inspection [ ] slope analysis [ ] distance/measurement [ ] elevation profile where supported
Validation: [ ] reference comparison [ ] RMSE [ ] MAE [ ] correlation [ ] stability analysis [ ] evidence recorded
Software: [ ] standalone deployment [ ] fresh-machine startup [ ] no developer-only paths [ ] reproducible setup [ ] documentation [ ] licenses/provenance

Only close this issue when repository + runtime evidence support the full checklist.

Project: Owner=Shivam | Track=release | SIH Area=Deployment | Priority=P0 | Verification=End-to-End | Release Gate=Yes | Status=Backlog | Milestone=Final
'@

# ---------------------------------------------------------------- epics
Add-Issue "[EPIC] Repository and Engineering Foundation" @'
Purpose: Python + TS tooling, test/lint/typecheck baselines, .gitignore data rules, governance control plane.
Scope: pyproject, package.json scripts, tests layout, CI expectations, docs/project, AGENTS.md, templates. Out: any model/3D work.
SIH: enables all rows R1-R15. Owner: Shivam. Track: core. Milestone: Foundation.
Done: pytest/ruff/mypy + typecheck/test/build green; GATE 1 PASS.
Verification: unit. Dependencies: none.
Project: Owner=Shivam | Track=core | Priority=P0 | Verification=Unit | Release Gate=No | Status=Done | Milestone=Foundation
'@

Add-Issue "[EPIC] Input and Geospatial Understanding" @'
Purpose: Ingestion, semantic validation, Path A/B routing, CRS/transform validators, overlap/alignment/reprojection, reference rasters.
Scope: depthwizard.ingestion + geospatial (+ dem reference reads). Out: depth inference, calibration mapping.
SIH: R1, R3. Owner: Shivam. Track: geospatial. Milestone: Core.
Done: invalid-input rejection demonstrated; CRS/transform round-trips green; GATE 2 PASS.
Verification: unit + integration. Dependencies: [EPIC] Foundation.
Project: Owner=Shivam | Track=geospatial | SIH Area=Input | Priority=P0 | Verification=Integration | Release Gate=No | Status=Review | Milestone=Core
'@

Add-Issue "[EPIC] Monocular Geometry / Depth" @'
Purpose: DepthBackend interface + DA-V2 Small integration + deterministic runtime + provenance behind the frozen contract.
Scope: depthwizard.backends, inference runtime, model loading. Out: metric meaning (belongs to calibration).
SIH: R2 feedstock (relative geometry). Owner: Shravan (boundary: Shivam). Track: ml. Milestone: ML.
Done: real DA-V2 runs deterministically with recorded provenance; relative-only enforced; GATE 3 PASS.
Verification: runtime + integration. Dependencies: [EPIC] Input (inspection shape).
Project: Owner=Shravan | Track=ml | SIH Area=Elevation | Priority=P0 | Verification=Runtime | Release Gate=No | Status=Integration | Milestone=ML
'@

Add-Issue "[EPIC] Metric Calibration" @'
Purpose: Relative-to-metric mapping against validated DEM/GCP/reference controls + quality checks + validity rules.
Scope: depthwizard.calibration + controls + dem. Out: uncalibrated metric claims (forbidden).
SIH: R4. Owner: Shivam. Track: calibration. Milestone: Calibration.
Done: uncalibrated metric requests rejected by rule; calibrated outputs carry method+units+provenance; GATE 4 PASS.
Verification: scientific + integration. Dependencies: [EPIC] Depth, [EPIC] Input.
Project: Owner=Shivam | Track=calibration | SIH Area=Calibration | Priority=P0 | Verification=Scientific | Release Gate=No | Status=In Progress | Milestone=Calibration
'@

Add-Issue "[EPIC] rDSM / DSM Products" @'
Purpose: DSM/rDSM construction, height semantics, nodata handling, standard GeoTIFF export.
Scope: depthwizard.dsm + rdsm + height + export. Out: mesh, viewer.
SIH: R2, R5. Owner: Shivam. Track: dsm. Milestone: DSM.
Done: exports open correctly placed in standard GIS with CRS/transform/nodata/provenance; GATE 5 PASS.
Verification: unit + integration + scientific. Dependencies: [EPIC] Calibration.
Project: Owner=Shivam | Track=dsm | SIH Area=DSM | Priority=P0 | Verification=Integration | Release Gate=No | Status=In Progress | Milestone=DSM
'@

Add-Issue "[EPIC] Terrain Mesh and Texture" @'
Purpose: Renderer-independent terrain mesh with preserved coordinates + UVs/source identity; viewer-side RGB projection.
Scope: depthwizard.mesh (Shivam) + viewer texturing (Aryan). Out: navigation/analysis UX.
SIH: R6, R7. Owner: Shivam + Aryan. Track: 3d. Milestone: 3D.
Done: mesh tests green; textured scene demonstrated; GATE 6 PASS.
Verification: integration + visual. Dependencies: [EPIC] DSM products.
Project: Owner=Shivam | Track=3d | SIH Area=3D | Priority=P1 | Verification=Visual | Release Gate=No | Status=In Progress | Milestone=3D
'@

Add-Issue "[EPIC] Interactive 3D / Desktop" @'
Purpose: Desktop app: session workflow, scene creation, camera system, flythrough, measurement/analysis tools, layers, UX.
Scope: src/* (session, viewer, camera, flythrough, measurement, inspection, layers, display). Out: backend semantics.
SIH: R8-R11, R13. Owner: Aryan. Track: desktop. Milestone: Desktop.
Done: orbit/FP/aerial + waypoints + tools validated vs known geometry; GATE 7 PASS.
Verification: visual + runtime. Dependencies: [EPIC] Integration (SceneArtifact).
Project: Owner=Aryan | Track=desktop | SIH Area=Flythrough | Priority=P0 | Verification=Visual | Release Gate=No | Status=In Progress | Milestone=Desktop
'@

Add-Issue "[EPIC] Validation and Scientific Evidence" @'
Purpose: Benchmark framework + real-data evaluation + recorded RMSE/MAE/correlation/stability (+ significance where claimed).
Scope: depthwizard.evaluation, eval protocol, GAMUS manifests (never raw data). Out: product accuracy claims without evidence.
SIH: R12. Owner: Shravan (+ Shivam methodology). Track: qa. Milestone: Validation.
Done: SIH-wide accuracy evidenced or explicitly open; GATE 8 PASS. Note: current 32-tile evidence (MAE 4.40 / RMSE 5.86 / R2 0.23) is research signal, not validation.
Verification: scientific. Dependencies: [EPIC] DSM products.
Project: Owner=Shravan | Track=qa | SIH Area=Validation | Priority=P0 | Verification=Scientific | Release Gate=No | Status=Blocked | Milestone=Validation
'@

Add-Issue "[EPIC] End-to-End Integration" @'
Purpose: Canonical adapter + transport + local service + desktop consumption running full Path A and Path B.
Scope: depthwizard.integration, transport, service, desktop client. Out: silent semantic changes (forbidden by contract).
SIH: cross-cutting (all rows integrated). Owner: Shivam + Aryan. Track: integration. Milestone: Integration.
Done: recorded Path A + Path B runs; GATE 9 PASS.
Verification: end-to-end + runtime. Dependencies: all product epics above.
Project: Owner=Shivam | Track=integration | Priority=P0 | Verification=End-to-End | Release Gate=No | Status=Integration | Milestone=Integration
'@

Add-Issue "[EPIC] Packaging and Standalone Deployment" @'
Purpose: Reproducible provisioning, native host, installer, fresh-machine acceptance.
Scope: provisioning automation, host boundary, installer, install docs. Out: dev-path dependencies (forbidden).
SIH: R14. Owner: Aryan (+ Shivam runtime). Track: release. Milestone: Packaging.
Done: fresh-machine launch log; GATE 10 PASS.
Verification: end-to-end + runtime. Dependencies: [EPIC] Integration.
Project: Owner=Aryan | Track=release | SIH Area=Deployment | Priority=P1 | Verification=End-to-End | Release Gate=No | Status=Backlog | Milestone=Packaging
'@

Add-Issue "[EPIC] SIH Final Acceptance" @'
Purpose: Umbrella epic tracking every acceptance checkbox to evidenced completion. Never closed by planning alone.
Scope: all SIH rows + gates. Owner: all (merge authority: Shivam). Track: release. Milestone: Final.
Done: GATE 11 PASS (see Final Acceptance Gate issue for the checklist).
Verification: all types. Dependencies: GATEs 1-10.
Project: Owner=Shivam | Track=release | SIH Area=Deployment | Priority=P0 | Verification=End-to-End | Release Gate=Yes | Status=Backlog | Milestone=Final
'@

# ---------------------------------------------------------------- SIH requirements
Add-Simple "SIH - RGB Image Input" "R1: PNG/JPG/TIFF/GeoTIFF + metadata validation via depthwizard.ingestion. Deps: Foundation. Done: routing + rejection tests green." "Shivam" "core" "Input" "P0" "Integration" "Core"
Add-Simple "SIH - Non-Georeferenced rDSM" "R2: relative output, LOCAL frame, units absent, no invented CRS via depthwizard.rdsm. Deps: Depth. Done: rDSM tests green." "Shivam" "geospatial" "Elevation" "P0" "Scientific" "DSM"
Add-Simple "SIH - GeoTIFF Georeferenced Input" "R3: CRS/transform preserved end to end via depthwizard.geospatial. Deps: Foundation. Done: round-trip tests green." "Shivam" "geospatial" "Input" "P0" "Integration" "Core"
Add-Simple "SIH - Absolute Metric DSM Calibration" "R4: explicit reference only (DEM/GCP/controls) via calibration. Every metric product carries method+units+provenance; rejection rule tested. Deps: Depth, Input." "Shivam" "calibration" "Calibration" "P0" "Scientific" "Calibration"
Add-Simple "SIH - Standard Geospatial Output" "R5: GeoTIFF export + nodata/validity + provenance via export. Deps: Calibration. Done: GIS-open check." "Shivam" "dsm" "DSM" "P0" "Integration" "DSM"
Add-Simple "SIH - Terrain Mesh Generation" "R6: correct spatial geometry, preserved coordinates via mesh. Deps: DSM products. Done: mesh tests green." "Shivam" "3d" "3D" "P1" "Integration" "3D"
Add-Simple "SIH - RGB Texture Projection" "R7: UVs + source identity into viewer texturing. Owner: Shivam + Aryan. Deps: Mesh. Done: textured scene." "Aryan" "3d" "3D" "P1" "Visual" "3D"
Add-Simple "SIH - Interactive 3D Flythrough" "R8: orbit/FP/aerial + waypoints via camera/flythrough/viewer. Deps: Integration. Done: trajectory workflow validated." "Aryan" "desktop" "Flythrough" "P0" "Visual" "Desktop"
Add-Simple "SIH - Height Analysis" "R9: inspection, exaggeration, profiles; readout matches DSM values. Deps: Flythrough." "Aryan" "desktop" "Analysis" "P1" "Visual" "Desktop"
Add-Simple "SIH - Slope Analysis" "R10: desktop slope tools vs reference computation. Deps: Height Analysis." "Aryan" "desktop" "Analysis" "P2" "Visual" "Desktop"
Add-Simple "SIH - Measurement Tools" "R11: distance/profile tools vs known geometry. Deps: Flythrough." "Aryan" "desktop" "Analysis" "P1" "Visual" "Desktop"
Add-Simple "SIH - DSM Validation" "R12: reference comparison RMSE/MAE/correlation/stability via evaluation. BLOCKED: SIH-wide accuracy unproven; current 32-tile GAMUS evidence is research signal only. Deps: DSM products." "Shravan" "qa" "Validation" "P0" "Scientific" "Validation"
Add-Simple "SIH - Visualization / UX" "R13: project workflow, sessions, layers. Deps: Flythrough. Done: session lifecycle tests green." "Aryan" "desktop" "Flythrough" "P1" "Runtime" "Desktop"
Add-Simple "SIH - Standalone Deployment" "R14: native host + installer + fresh-machine launch. Deps: Integration. Done: fresh-machine log." "Aryan" "release" "Deployment" "P1" "End-to-End" "Packaging"
Add-Simple "SIH - Technical Documentation" "R15: architecture, provenance, licenses verified vs code. Done: docs present and current." "Shivam" "release" "Documentation" "P2" "Review" "Final"

# ---------------------------------------------------------------- gates
Add-Simple "[RELEASE] GATE 1 - Engineering Foundation" "Prereqs: repo layout, pyproject (pytest/ruff/mypy), TS tooling, .gitignore data rules. Verification: unit. Evidence: clean suites. Status: Done." "Shivam" "release" "Documentation" "P0" "Review" "Foundation"
Add-Simple "[RELEASE] GATE 2 - Input and Geospatial Correctness" "Prereqs: ingestion + validation, Path A/B routing, CRS/transform validators, alignment/reprojection. Verification: unit + integration. Evidence: ingestion/geospatial suites. Status: Review/Integration." "Shivam" "release" "Input" "P0" "Review" "Core"
Add-Simple "[RELEASE] GATE 3 - Depth Runtime" "Prereqs: DepthBackend + DA-V2 Small + determinism + provenance. Verification: runtime + integration. Evidence: S16/S16R on main. Status: Integration." "Shravan" "release" "Elevation" "P0" "Review" "ML"
Add-Simple "[RELEASE] GATE 4 - Calibration / Reference Validity" "Prereqs: mapping + DEM/GCP + controls + quality checks + validity rules. Verification: scientific + integration. Evidence: calibration tests. Status: In Progress." "Shivam" "release" "Calibration" "P0" "Review" "Calibration"
Add-Simple "[RELEASE] GATE 5 - DSM / rDSM Product Correctness" "Prereqs: construction + height semantics + nodata + export. Verification: unit + integration + scientific. Evidence: dsm/height/export suites + GIS-open check. Status: In Progress." "Shivam" "release" "DSM" "P0" "Review" "DSM"
Add-Simple "[RELEASE] GATE 6 - Mesh + Texture" "Prereqs: mesh engine + UVs + viewer texturing. Verification: integration + visual. Evidence: mesh tests + textured scene. Status: In Progress." "Shivam" "release" "3D" "P0" "Review" "3D"
Add-Simple "[RELEASE] GATE 7 - Interactive 3D" "Prereqs: navigation + waypoints + analysis/measurement tools + sessions. Verification: visual + runtime. Evidence: flythrough validation + known-geometry checks. Status: In Progress." "Aryan" "release" "Flythrough" "P0" "Review" "Desktop"
Add-Simple "[RELEASE] GATE 8 - Scientific Validation" "Prereqs: benchmark framework + real-data RMSE/MAE/corr/stability. Verification: scientific. Evidence: level-3 evidence docs + broader runs. Status: Blocked (open research)." "Shravan" "release" "Validation" "P0" "Review" "Validation"
Add-Simple "[RELEASE] GATE 9 - End-to-End Integration" "Prereqs: adapter + transport + service + desktop on Path A and Path B. Verification: end-to-end + runtime. Evidence: recorded runs + integration tests. Status: Integration (Path A partial)." "Shivam" "release" "Flythrough" "P0" "Review" "Integration"
Add-Simple "[RELEASE] GATE 10 - Standalone Deployment" "Prereqs: provisioning + native host + installer + fresh-machine launch. Verification: end-to-end + runtime. Evidence: fresh-machine log. Status: Backlog." "Aryan" "release" "Deployment" "P0" "Review" "Packaging"
Add-Simple "[RELEASE] GATE 11 - Final SIH Acceptance" "Prereqs: GATEs 1-10 passed. Merge authority: Shivam. Verification: all types. Evidence: full checklist in Final Acceptance Gate issue. Status: Backlog." "Shivam" "release" "Deployment" "P0" "Review" "Final"

# ---------------------------------------------------------------- final acceptance gate
Add-Issue "SIH 26175 - Final Acceptance Gate" @'
NOT a generic project-complete checkbox. Closes only on evidence.

[ ] PNG/JPG input works
[ ] GeoTIFF input works
[ ] correct georeferenced/non-georeferenced routing
[ ] relative output semantics are correct
[ ] metric output is produced only when justified
[ ] standard geospatial export works
[ ] CRS/transform preserved
[ ] nodata/validity semantics correct
[ ] terrain mesh generated
[ ] RGB projected correctly
[ ] 3D scene generated
[ ] interactive flythrough works
[ ] height inspection works
[ ] slope analysis works
[ ] measurement works
[ ] validation against reference works
[ ] RMSE recorded where applicable
[ ] MAE recorded where applicable
[ ] correlation recorded where applicable
[ ] stability evidence recorded
[ ] standalone build works
[ ] fresh-machine launch works
[ ] no developer-path dependency
[ ] documentation complete
[ ] third-party/model/data provenance documented

Project: Owner=Shivam | Track=release | SIH Area=Validation | Priority=P0 | Verification=End-to-End | Release Gate=Yes | Status=Backlog | Milestone=Final
'@

# ---------------------------------------------------------------- create
$existing = Get-ExistingTitles
$created = 0
$skipped = 0
foreach ($i in $Issues) {
  if ($existing.ContainsKey($i.title)) { Write-Output "skip: $($i.title)"; $skipped += 1; continue }
  $tmp = [System.IO.Path]::GetTempFileName()
  Set-Content -LiteralPath $tmp -Value $i.body -Encoding UTF8
  gh issue create --repo $Repo --title $i.title --body-file $tmp | Write-Output
  Remove-Item -LiteralPath $tmp -Force
  $created += 1
}
Write-Output "done: created=$created skipped=$skipped total=$($Issues.Count)"
