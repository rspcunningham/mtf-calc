# MTF Calculator Architecture

## Ownership

### Python backend owns

- The authoritative workspace state for the running local session.
- Workflow progression and which page is currently actionable.
- Source dataset lifecycle: load, validate, cache, reset, and metadata.
- ROI records: geometry, ordering, labels, active ROI, and future per-ROI analysis state.
- Scientific state and outputs: cropped arrays, profiles, coefficients, derived numbers, and final MTF curves.
- Dirty-state and recomputation rules when a source or ROI changes.

### Browser client owns

- Rendering of the current view page.
- Display-only state such as zoom, pan, window, and level.
- A local float32 source buffer used only for fast display interactions.
- Ephemeral interaction state such as hover, drag, draw-in-progress, and selection highlight.

## Practical rule

- If losing the value on refresh would change the scientific result, Python should own it.
- If losing the value on refresh would only affect what the user is looking at, the browser can own it.

## Current workflow model

The near-term app only has two real steps:

1. Select a starting source array.
2. View that source array.

ROI selection, analysis, and final MTF outputs are future stages, but they are not part of the active plan for the current implementation pass.

## Backend shape

The backend is now split into four layers:

- [mtf_calc/server.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/server.py)
  Startup only: CLI args, port selection, browser launch, and `uvicorn.run(...)`.
- [mtf_calc/application.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/application.py)
  App assembly only: create the FastAPI app, mount static assets, and wire routers and services together.
- [mtf_calc/routes/pages.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/routes/pages.py), [mtf_calc/routes/actions.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/routes/actions.py), and [mtf_calc/routes/render.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/routes/render.py)
  HTTP layer only: page routing, action posts, and float32 render delivery.
- [mtf_calc/services/workspace.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/services/workspace.py) plus [mtf_calc/workspace.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/workspace.py)
  Processing and state: workspace operations, validation, source lifecycle, and domain errors.

The preferred direction for the current 2-step app is server-rendered page flow:

- `GET /`
  Server renders either the source-selection page or the source-view page based on server-side state.
- `POST /actions/source/sample`
  Loads the bundled sample into the server-side session, then redirects back to `/`.
- `POST /actions/source/upload`
  Loads a user-provided source array into the server-side session, then redirects back to `/`.
- `POST /actions/source/reset`
  Clears the loaded source from the server-side session, then redirects back to `/`.
- `GET /render/source.float32`
  Returns the current source array as a raw float32 buffer for browser-side display rendering.
- `GET /render/source-metadata`
  Optional helper endpoint if metadata is not embedded directly in the rendered HTML.

The browser should not fetch a full application-state snapshot just to reconstruct the UI. The server should decide which HTML to return. The only data fetch needed for the current viewer is the raw source buffer used for client-side display interactions.

## Frontend shape

The frontend should be a very thin shell with three concerns:

- Render the server-returned page.
- Fetch the raw float32 source buffer after the view page loads.
- Keep only transient display state locally.

The browser should never be responsible for deciding what the canonical source, ROI definitions, coefficients, or MTF outputs are.

## Why Float32

For the current view step, the browser should receive the source image as raw float32 data instead of repeatedly requesting server-rendered PNGs.

- PNG is acceptable for infrequent updates, but it adds avoidable encode/decode latency during rapid window/level changes.
- A float32 buffer lets the browser update window/level immediately on a canvas without round-tripping every drag event through the server.
- This still respects the ownership boundary because the float32 buffer is only a display artifact. The server remains authoritative for the loaded source and all application state.

This is a hybrid model:

- Server-rendered HTML for page flow and authoritative state.
- Client-side rendering for fast view-only interactions.

## Current code that needed refactor

### Backend

The backend is no longer concentrated in one module. Startup lives in [mtf_calc/server.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/server.py), app assembly lives in [mtf_calc/application.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/application.py), HTTP route handling lives in [mtf_calc/routes/pages.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/routes/pages.py), [mtf_calc/routes/actions.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/routes/actions.py), and [mtf_calc/routes/render.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/routes/render.py), and processing/state logic lives in [mtf_calc/services/workspace.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/services/workspace.py) plus [mtf_calc/workspace.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/workspace.py).

### Frontend

[mtf_calc/ui/app.js](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/ui/app.js) now only owns:

- file upload event handling on the select page
- fetching the raw float32 source buffer on the view page
- display-only state such as zoom, pan, window, and level
- local canvas rendering and pixel inspection

Anything authoritative about the loaded source stays in Python.

### UI shell

[mtf_calc/page_render.py](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/page_render.py) now renders the select and view pages on the server, and [mtf_calc/ui/styles.css](/Users/robin/Desktop/parasight/mtf-calc/mtf_calc/ui/styles.css) styles those pages and the viewer controls.
