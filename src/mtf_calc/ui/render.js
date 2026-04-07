import { clamp } from "./utils.js";

export function renderSourceImage({ canvas, context, data, rows, cols, display }) {
  if (!data) return;

  const low = display.level - display.window / 2;
  const scale = display.window > 0 ? 1 / display.window : 1;

  const imageData = context.createImageData(cols, rows);
  const pixels = imageData.data;

  for (let i = 0; i < data.length; i++) {
    const normalized = clamp((data[i] - low) * scale, 0, 1);
    const byte = Math.round(normalized * 255);
    const p = i * 4;
    pixels[p] = byte;
    pixels[p + 1] = byte;
    pixels[p + 2] = byte;
    pixels[p + 3] = 255;
  }

  canvas.width = cols;
  canvas.height = rows;
  context.putImageData(imageData, 0, 0);
}

export function applyCanvasTransform({ canvas, display, zoomIndicator }) {
  canvas.style.transform = `translate(${display.panX}px, ${display.panY}px) scale(${display.zoom})`;
  if (zoomIndicator) {
    zoomIndicator.textContent = `${display.zoom.toFixed(2)}x`;
  }
}

export function fitDisplay(container, rows, cols) {
  const width = container.clientWidth;
  const height = container.clientHeight;
  const scale = Math.min(width / cols, height / rows);
  const zoom = clamp(scale * 0.96, 0.05, 64);

  return {
    zoom,
    panX: (width - cols * zoom) / 2,
    panY: (height - rows * zoom) / 2,
  };
}

export function screenToPixel(container, display, clientX, clientY) {
  const rect = container.getBoundingClientRect();
  return {
    x: Math.floor((clientX - rect.left - display.panX) / display.zoom),
    y: Math.floor((clientY - rect.top - display.panY) / display.zoom),
  };
}
