# Project control-plane recovery (labels, milestones, Project #4)

The GitHub MCP toolset available to the bootstrap agent supports
**issues, branches, PRs, files, and search** — it exposes no
ProjectsV2, label-admin, or milestone-admin operations. Those objects
therefore cannot be created or edited through MCP and must be applied
once, by a maintainer, with `gh` CLI (or the web UI). This script is
idempotent: re-running it only creates what is still missing.

```powershell
# 0. Auth + target
gh auth login
$owner = "sashtriyasam"
$repo = "ISRO-DEPTHWIZ"

# 1. Labels (track / type / priority / sih / state)
$labels = @(
  # track
  @("track:core","1d76db","Core / architecture track"),
  @("track:ml","5319e7","ML / model track"),
  @("track:geospatial","0e8a16","Geospatial track"),
  @("track:calibration","fbca04","Calibration track"),
  @("track:dsm","0e8a16","DSM track"),
  @("track:3d","1d76db","Mesh / 3D track"),
  @("track:desktop","5319e7","Desktop track"),
  @("track:integration","d876e3","Integration track"),
  @("track:qa","e99695","QA / validation track"),
  @("track:release","b60205","Release track"),
  # type
  @("type:feature","1d76db","Product feature"),
  @("type:bug","d73a4a","Bug"),
  @("type:research","5319e7","Research investigation"),
  @("type:refactor","fbca04","Refactor"),
  @("type:documentation","0075ca","Documentation"),
  @("type:test","0e8a16","Test / verification"),
  @("type:experiment","5319e7","Runnable experiment"),
  @("type:integration","d876e3","Integration work"),
  # priority
  @("priority:p0","b60205","Priority 0"),
  @("priority:p1","d93f0b","Priority 1"),
  @("priority:p2","fbca04","Priority 2"),
  @("priority:p3","0e8a16","Priority 3"),
  # sih
  @("sih:input","0075ca","SIH input"),
  @("sih:elevation","0075ca","SIH elevation"),
  @("sih:calibration","0075ca","SIH calibration"),
  @("sih:dsm","0075ca","SIH DSM"),
  @("sih:flythrough","0075ca","SIH flythrough"),
  @("sih:visualization","0075ca","SIH visualization"),
  @("sih:analysis","0075ca","SIH analysis"),
  @("sih:validation","0075ca","SIH validation"),
  @("sih:deployment","0075ca","SIH deployment"),
  # state
  @("state:blocked","b60205","Blocked"),
  @("state:needs-review","fbca04","Needs review"),
  @("state:ready","0e8a16","Ready")
)
foreach ($l in $labels) {
  gh label create $l[0] --repo "$owner/$repo" --color $l[1] --description $l[2] 2>$null
  if ($LASTEXITCODE -ne 0) { Write-Output "exists: $($l[0])" }
}

# 2. Milestones (dependency order; no dates — dates need planning evidence)
@("Foundation","Core","ML","Calibration","DSM","3D","Desktop",
  "Integration","Validation","Packaging","Final") | ForEach-Object {
  gh api "repos/$owner/$repo/milestones" -f title="$_" `
    -f state=open `
    -f description="DepthWizard phase: $_ (see docs/project/MASTER_PLAN.md)" 2>$null | Out-Null
}

# 3. Project #4 -> rename (user-owned project; needs project scope)
#    Web UI fallback: https://github.com/users/sashtriyasam/projects/4 → … → Rename
gh project view 4 --owner $owner 2>$null
# If visible: rename via UI (title "DepthWizard — SIH 26175") and set the
# description from docs/project/MASTER_PLAN.md "Project information" intent.
# Then add custom fields (Status, Owner, Track, SIH Area, Priority,
# Verification, Release Gate, Milestone, Dependency, Start/Target Date),
# views (Master Roadmap, Active Board, Master Table, Shivam, Shravan,
# Aryan, SIH Traceability, Release Gates), and add all open issues.
```

After running: re-read the Project, attach the created issues to it,
and set Owner/Track/SIH Area/Priority/Verification/Release Gate/Status
per `docs/project/PROJECT_STATUS.md` and each issue body.
