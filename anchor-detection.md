# Anchor Point Detection Workflow

## Goal

Given a `.npy` image of a USAF 1951 resolution target, find the precise center and
orientation of the large reference square. This provides the anchor point and rotation
needed to predict the pixel coordinates of every element in the target.

## Outputs

- Center coordinates (sub-pixel) of the large reference square
- Rotation angle of the target relative to image axes
- Pixel scale (µm/px), derived from square edge length vs known physical size

## Workflow

### Step 1: ROI selection (VLM)

The VLM looks at the image and selects a bounding box around the large black reference
square, with some margin.

### Step 2: Edge detection (CV)

Within the ROI, run edge detection (e.g., Sobel/Canny gradient) to find the 4 edges
of the square. Fit a line to each edge.

No hardcoded hyperparameters — start with reasonable defaults.

### Step 3: Validation (VLM)

Overlay the detected edges on the image and show to the VLM. The VLM checks:

- Do the 4 detected edges align with the visible square edges?
- Are there false detections or missing edges?

If the result is wrong, the VLM adjusts hyperparameters (e.g., gradient threshold,
edge pixel selection criteria) and reruns Step 2.

### Step 4: Compute anchor point and orientation (CV)

From the 4 fitted edge lines:

1. Intersect adjacent pairs to get 4 corner points
2. Center = mean of the 4 corners
3. Orientation = angle of the edge lines relative to image horizontal
4. Edge length in pixels = distance between adjacent corners
5. Scale = known physical edge length / pixel edge length

### Step 5: Validation via second square (CV + VLM)

Using the anchor point, orientation, and scale, predict where the small reference
square should be (from the known USAF 1951 layout geometry). Compare predicted
location to actual (found via centroid of binarized component or VLM inspection).

Agreement confirms the anchor, orientation, and scale are correct.
