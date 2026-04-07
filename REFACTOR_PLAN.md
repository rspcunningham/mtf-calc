# Library-First Refactor Plan

## Goal

Make `mtf-calc` a Python library of reusable measurement tools.

Then build multiple user-facing layers on top of that library:

- scripts for deterministic and semi-guided execution
- AI-agent orchestration for eventual end-to-end automation
- GUI tools for review, selection, correction, and publication-quality visualization

The core idea is:

- if the required choices are already known, the calculation should run in one shot
- if the required choices are unknown, the system should expose tools that help a human or AI agent choose them
- GUI should be a wrapper over the same tools, not the place where the workflow fundamentally lives

## Product Model

The right top-level model is not "CLI app" or "desktop app".

It is:

1. library primitives
2. selection/assist tools
3. orchestration scripts
4. optional GUI and agent wrappers

### Library primitives

These are deterministic operations with explicit inputs and outputs:

- load and validate a source array
- detect anchor
- identify or suggest scale groups
- define and validate ROI sets
- extract averaged profiles
- normalize against black/white references
- fit square-wave-plus-harmonics models
- compute MTF values
- generate plots and export artifacts

### Selection/assist tools

These are still library tools, but they help choose the "magic numbers":

- scale group selection aids
- ROI candidate generation / scoring
- profile crop selection aids (`p/q` or equivalent)
- harmonic-count selection aids (`n_coeffs`)
- diagnostics, previews, and confidence measures

These tools must work whether the selector is:

- a human
- a saved config
- a script
- an AI agent

### Orchestration scripts

These stitch the tools together:

- fully deterministic batch runs
- semi-guided scripted runs that pause when a choice is needed
- automation-oriented entrypoints for AI agents

### GUI wrappers

The GUI should:

- expose the same underlying tool outputs
- help inspect and choose magic numbers
- show overlays, profile plots, fitted curves, and final MTF graphs
- support correction and rerun

The GUI should not be the primary home of workflow state or scientific logic.

## End User-Facing Result

The end-user-facing system should support three modes cleanly.

### 1. One-shot scripted calculation

Use when the required inputs are known:

- source file
- scale groups
- ROI bounding boxes
- crop values
- harmonic count

The script runs the full workflow and emits:

- structured results
- exports
- visualizations

### 2. Guided selection workflow

Use when some magic numbers are unknown.

A script or toolchain runs deterministic steps automatically, then calls selection helpers when needed:

- choose scale numbers
- choose ROI bounding boxes
- choose crop parameters
- choose `n_coeffs`

Those choices may be supplied by:

- a user
- an AI agent
- a reusable prior config

### 3. Review and visualization workflow

Use when a user needs to:

- inspect what was selected
- verify or correct ROIs
- compare fit quality
- produce publication graphs

This is where the GUI is useful.

## Current Assessment

Audit date: 2026-04-07

The repo has started to accumulate reusable scientific modules, but the overall architecture is still app-first rather than library-first.

### What is already aligned with the desired direction

- `src/mtf_calc/usaf1951.py`
  Pure domain math.
- `src/mtf_calc/workflow/find_anchors.py`
  Mostly reusable computational logic.
- `src/mtf_calc/workflow/stage6_profiles.py`
  Pure profile/normalization computation.
- `src/mtf_calc/workflow/stage6_fit.py`
  Pure fitting logic over profile data.
- `src/mtf_calc/pipeline.py`
  Useful as a UI/workflow description layer, though it should not become the core architecture boundary.

### What is not aligned yet

- `src/mtf_calc/workspace.py`
  Still acts as the central application object and mixes persistence, validation, workflow state, stage orchestration, reusable config logic, Stage 6 computation, migration logic, and cache invalidation.
- `src/mtf_calc/workflow_session.py`
  Exposes application commands in websocket-specific form.
- `src/mtf_calc/routes.py`
  Uses the workspace object directly and duplicates command behavior already present in websockets.
- `src/mtf_calc/app.py`
  Builds the app around `WorkspaceStore`.
- `src/mtf_calc/server.py` and `src/mtf_calc/__main__.py`
  Still define the only real product entrypoints.
- `pyproject.toml`
  Still exposes only a web server entrypoint.

## Architectural Direction

The repo should move toward these layers:

1. `domain`
2. `tools`
3. `orchestrators`
4. `adapters`

## Proposed Module Layout

Suggested layout:

- `src/mtf_calc/domain/`
  Shared models and pure domain rules.
- `src/mtf_calc/tools/`
  Reusable measurement and selection tools.
- `src/mtf_calc/orchestrators/`
  Script-oriented flows that stitch tools together.
- `src/mtf_calc/io/`
  Input/output helpers, persistence helpers, export helpers.
- `src/mtf_calc/adapters/web/`
  FastAPI/websocket layer.
- `src/mtf_calc/ui/`
  Static frontend assets.
- `src/mtf_calc/plotting/`
  Visualization and publication-graph helpers.

This does not need to be implemented as a big-bang move.

## Core Design Rule

Every magic number must become an explicit input to a tool.

Examples:

- selected scale groups
- bar ROI rectangles
- normalization ROI rectangles
- crop values (`p/q`)
- harmonic count (`n_coeffs`)

These values should not live only as implicit GUI state.

That is what enables:

- deterministic scripted runs
- reviewable and reproducible automation
- AI-agent use
- GUI reuse

## Proposed Responsibility Split

### 1. Domain layer

Owns typed concepts such as:

- source metadata
- rectangles / ROIs
- scale selections
- profile sets
- normalization summaries
- fit results
- MTF results
- run parameters
- run artifacts

Suggested modules:

- `domain/models.py`
- `domain/roi.py`
- `domain/validation.py`
- `domain/results.py`

### 2. Tool layer

Owns reusable operations with explicit input/output contracts.

Suggested tool families:

- `tools/load_source.py`
- `tools/find_anchor.py`
- `tools/select_scale.py`
- `tools/roi_profiles.py`
- `tools/normalize_profiles.py`
- `tools/fit_profile.py`
- `tools/compute_mtf.py`
- `tools/plot_results.py`

Selection-assist tools can sit here too:

- suggest ROI candidates
- score fit quality across harmonic counts
- propose crop windows
- align a saved reusable config onto a new source

### 3. Orchestrator layer

Owns script-level flows, not scientific primitives.

Examples:

- `run_known_inputs(...)`
- `run_guided(...)`
- `run_with_reusable_config(...)`
- `run_with_agent(...)`

These are allowed to pause and request missing values from:

- function arguments
- config files
- callbacks
- AI agents
- GUI wrappers

### 4. Adapter layer

Owns transport and interaction concerns only:

- web app
- websocket sessions
- future desktop wrapper
- script entrypoints

Adapters should call orchestrators and tools, not own scientific logic.

## What To Do With The Current Workspace Layer

`WorkspaceStore` should stop being the center of the design.

The current responsibilities inside `workspace.py` should be split into:

### A. Run/persistence repository

Owns:

- filesystem layout
- loading/saving source arrays
- loading/saving intermediate artifacts
- loading/saving reusable configs
- loading/saving run metadata
- deleting cached outputs

This can remain file-based and simple.

### B. Tool functions and helpers

Move deterministic logic out of the workspace object:

- source validation
- ROI validation
- scale validation
- ROI translation/alignment helpers
- Stage 6 profile generation
- Stage 6 fit execution

### C. Orchestrators

Move flow logic out of the workspace object:

- "advance" and "retreat" stage operations if they are still useful for UI
- apply reusable config
- perform a guided run
- perform a known-input run

The important change is that the workspace should become storage support, not the application brain.

## Recommended End-State API

The most important artifact to expose is a Python library API.

Examples:

- `load_source(path_or_bytes) -> SourceImage`
- `find_anchor(source) -> AnchorResult`
- `build_bar_roi_set(scale_groups, roi_rects) -> BarRoiSet`
- `build_norm_roi_set(black_rect, white_rect) -> NormRoiSet`
- `extract_profiles(source, bar_rois, norm_rois) -> ProfileBundle`
- `fit_bar_profile(profile, crop, harmonic_count) -> FitResult`
- `compute_mtf(fit_result, normalization) -> MtfResult`
- `plot_profiles(...)`
- `plot_mtf_curve(...)`

Then orchestration APIs:

- `run_known_inputs(source, selections, params) -> RunResult`
- `run_guided(source, chooser=...) -> RunResult`
- `run_with_agent(source, agent_tools=...) -> RunResult`

## Script Strategy

The user-facing non-GUI workflow should be script-oriented, not command-heavy CLI-oriented.

That suggests:

- a Python API first
- a small number of script entrypoints second
- only minimal CLI surface for convenience

Good script-facing entrypoints:

- `python -m mtf_calc.scripts.run_known_inputs ...`
- `python -m mtf_calc.scripts.run_guided ...`
- `python -m mtf_calc.scripts.review_run ...`

Or a very small thin wrapper in `pyproject.toml`:

- `mtf-calc-run`
- `mtf-calc-review`
- `mtf-calc-web`

The important thing is that these should be wrappers over library/orchestrator APIs, not the primary architecture.

## GUI Strategy

The GUI should become:

- a selection tool
- a review tool
- a visualization tool
- a correction tool

The GUI should not be:

- the only place where the workflow can run
- the only place where intermediate state exists
- the source of truth for magic-number choices

The GUI should read and write explicit selections and run artifacts.

## Automation Strategy

End-to-end automation is a requirement, so the architecture must support that directly.

That means:

- deterministic tools with explicit inputs
- explicit representation of every magic-number choice
- resumable run artifacts
- confidence/diagnostic outputs where selection is uncertain
- ability for a human or AI agent to supply missing values through the same interfaces

The automation target should be:

- if all choices are known, run end to end unattended
- if some choices are unknown, surface exactly which values are needed and which tools can determine them
- if confidence is high enough, accept automated choices
- if confidence is low, route to user or agent review

## Concrete Migration Plan

### Phase 1: Stop Growing `WorkspaceStore`

Before restructuring, stop adding new scientific commands to `WorkspaceStore` unless absolutely necessary.

Any new capability should prefer:

- pure tool module first
- orchestrator second
- workspace persistence hook only if needed

### Phase 2: Extract Pure Tools

Continue the direction already started with:

- `workflow/stage6_profiles.py`
- `workflow/stage6_fit.py`
- `usaf1951.py`

Next candidates to extract:

- source validation helpers
- ROI validation helpers
- reusable-config alignment / ROI translation
- normalization helpers

Deliverable:

- deterministic functions with explicit input/output contracts

### Phase 3: Introduce Run Models

Add explicit models for:

- source metadata
- ROI rectangles and ROI sets
- profile bundles
- normalization results
- fit parameters and fit results
- MTF results
- reusable configs
- run parameters
- run outputs

Keep JSON persistence if desired, but serialize through models instead of ad hoc dict mutation.

### Phase 4: Add Orchestrators

Introduce a small orchestrator layer that composes the tools.

Initial orchestrators:

- `run_known_inputs`
- `apply_reusable_config`
- `fit_stage6_profile`
- `run_guided`

These should use explicit parameters rather than hidden workspace state wherever possible.

### Phase 5: Reduce `WorkspaceStore` To Persistence Support

Refactor `workspace.py` into something more like:

- `io/run_repository.py`
- `io/reusable_config_repository.py`
- maybe `io/cache_repository.py`

Move orchestration and validation out.

### Phase 6: Rebuild Adapters Around The Library

Update:

- `routes.py`
- `workflow_session.py`
- `app.py`

so they call orchestrators and tool functions rather than owning direct application logic over `WorkspaceStore`.

### Phase 7: Add Script Entry Points

Add script-oriented entrypoints for:

- known-input one-shot runs
- guided runs
- review/visualization

Do not over-invest in a command-heavy CLI unless real usage proves it necessary.

### Phase 8: Add Agent and Desktop Wrappers As Needed

After the library and script/orchestrator layers are stable:

- build an AI-agent wrapper around the same tool calls
- build a desktop GUI wrapper if the web adapter is no longer sufficient

## File-by-File Recommendations

### `src/mtf_calc/workspace.py`

Shrink this aggressively.

Move out:

- source validation
- scale validation
- ROI validation
- ROI translation logic
- Stage 6 profile generation
- Stage 6 fit execution
- reusable-config application logic
- any future "magic number" selection logic

Keep only persistence-oriented behavior that truly needs to know the on-disk layout.

### `src/mtf_calc/workflow_session.py`

Keep only websocket transport behavior.

It should:

- parse messages
- call library/orchestrator functions
- return results/errors

It should not define the real command surface of the product.

### `src/mtf_calc/routes.py`

Keep as a web adapter.

It should not be the place where scientific operations are implemented or duplicated.

### `src/mtf_calc/app.py`

Keep as app assembly only.

### `src/mtf_calc/server.py`

Demote this from "product entrypoint" to "web adapter entrypoint".

### `src/mtf_calc/workflow/stage6_profiles.py`

Keep pure.

### `src/mtf_calc/workflow/stage6_fit.py`

Keep pure.

### `src/mtf_calc/ui/*`

Treat the frontend as a wrapper layer over library/orchestrator results.

## Risks To Avoid

- Do not let UI stage concepts become the core architecture boundary.
- Do not bury magic-number choices in GUI-only state.
- Do not keep adding scientific logic into `WorkspaceStore`.
- Do not make the web app the only execution path.
- Do not optimize first for desktop packaging before the library/orchestrator split is real.
- Do not overbuild a complicated CLI if scripts and Python APIs are the true usage model.

## Immediate Next Slice

The smallest high-value next step is:

1. add explicit typed models for source, ROIs, profiles, normalization, fits, and results
2. extract source/ROI validation into pure helper modules
3. wrap Stage 6 profile and fit operations in library-style tool functions
4. add one script-oriented orchestrator for "known inputs"
5. keep the current web UI calling the same tool/orchestrator code where possible

That gives the project its real backbone:

- a library first
- scripts second
- GUI third

## Definition Of Done

This refactor is successful when:

- the main measurement workflow can run from Python code without importing FastAPI or websocket code
- a script can execute the workflow in one shot when the required choices are known
- the same underlying tools can be used by a human, GUI, or AI agent to determine missing magic numbers
- visualizations are generated from explicit artifacts, not hidden UI state
- changing the GUI technology no longer changes the scientific architecture
