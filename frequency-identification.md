# USAF 1951 Bar Frequency Identification Workflow

## Goal

Given a `.npy` image of a USAF 1951 resolution target, automatically identify which
group/element each set of bars corresponds to, and derive the pixel scale (µm/px).

## Required Tools

1. **File access** — read the `.npy` array
2. **Python interpreter** — image processing (binarization, connected components, measurements)
3. **Vision (LLM)** — visually inspect the image to read printed group numbers
4. **USAF 1951 spec** — look up known physical dimensions (see `usaf1951-spec.md`)

## Workflow

### Step 1: Load and inspect the image

Load the `.npy` file. Confirm it is a 2D grayscale array. Note the shape, dtype, and
intensity range.

### Step 2: Find the black reference squares

1. Binarize the image with a low intensity threshold (e.g., < 0.15)
2. Label connected components
3. Filter for square-like components:
   - Aspect ratio (min dimension / max dimension) > 0.9
   - Fill ratio (component area / bounding box area) > 0.85
4. There should be exactly two: one large (outer group) and one small (inner group)
5. Record their pixel dimensions and center coordinates

### Step 3: Identify which groups are visible

Use vision (LLM looking at the image) to read the printed group numbers on the target.
This tells you which groups the two squares belong to.

The squares belong to **even-numbered groups** (per the USAF 1951 spec, even groups
contain the reference squares).

### Step 4: Compute physical square sizes

From the spec, the square's edge length = bar length of Element 2 in that group:

```
square_edge = 5 × line_width(group, element=2)
```

Where line width is:

```
line_width (µm) = 1000 / (2 × 2^(group + (element - 1) / 6))
```

### Step 5: Derive pixel scale

```
scale (µm/px) = square_edge (µm) / square_edge (px)
```

Compute from both squares independently and check they agree (should be within ~1-2%).

### Step 6: Identify all bar groups

With the pixel scale known, every bar set in the image can be identified:

1. Measure bar width in pixels (from a line profile perpendicular to the bars)
2. Convert to µm using the scale
3. Look up the nearest group/element in the USAF 1951 table

Or in reverse: predict the expected pixel width of every visible group/element and
use template matching to locate them.

## Validation

- The two squares should have a pixel size ratio of exactly 4:1 (they are 2 groups apart,
  each group doubles frequency, so sizes differ by 2² = 4)
- Derived scale from both squares should agree
- Measured bar widths should match predicted values from the spec within measurement error
