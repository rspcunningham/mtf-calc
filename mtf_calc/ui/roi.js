import { screenToPixel } from "./render.js";
import { clamp } from "./utils.js";

export function createROIController({ config, canvasContainer, display }) {
  const roiCanvas = document.getElementById("roi-canvas");
  const roiCtx = roiCanvas.getContext("2d");
  const roiPrompt = document.getElementById("roi-prompt");
  const roiProgress = document.getElementById("roi-progress");
  const roiList = document.getElementById("roi-list");
  const sidebar = document.getElementById("roi-sidebar");

  let sequence = config.roiSequence || [];
  let activeIndex = findNextIncomplete(0);
  let drawing = false;
  let drawStart = null;
  let drawEnd = null;

  function findNextIncomplete(from) {
    for (let i = from; i < sequence.length; i++) {
      if (!sequence[i].rect) return i;
    }
    return sequence.length;
  }

  function roiLabel(slot) {
    if (slot.type === "norm") return slot.kind;
    return `${slot.frequency.toExponential(2)} ${slot.axis}`;
  }

  function roiColor(slot) {
    if (slot.type === "norm") return slot.kind === "black" ? "rgba(255,107,107," : "rgba(255,217,61,";
    return slot.axis === "h" ? "rgba(61,216,197," : "rgba(107,138,253,";
  }

  function updatePrompt() {
    if (activeIndex >= sequence.length) {
      roiPrompt.textContent = "All ROIs defined";
      roiProgress.textContent = `${sequence.length}/${sequence.length}`;
      return;
    }

    const slot = sequence[activeIndex];
    const label = roiLabel(slot);
    roiPrompt.textContent = `Draw ${label}`;

    const done = sequence.filter((s) => s.rect).length;
    roiProgress.textContent = `${done}/${sequence.length}`;
  }

  function renderSidebar() {
    roiList.innerHTML = "";
    sequence.forEach((slot, index) => {
      const item = document.createElement("div");
      item.className = "roi-item";
      item.dataset.active = String(index === activeIndex);
      item.dataset.complete = String(!!slot.rect);

      const label = document.createElement("span");
      label.className = "roi-item-label";
      label.innerHTML = `<span class="roi-dot"></span>${roiLabel(slot)}`;
      label.addEventListener("click", () => {
        activeIndex = index;
        updatePrompt();
        renderSidebar();
      });
      item.appendChild(label);

      if (slot.rect) {
        const clearBtn = document.createElement("button");
        clearBtn.className = "roi-clear";
        clearBtn.textContent = "\u00d7";
        clearBtn.addEventListener("click", async (event) => {
          event.stopPropagation();
          try {
            const response = await fetch(`/actions/roi/${encodeURIComponent(slot.key)}`, {
              method: "DELETE",
            });
            if (!response.ok) return;
            const updated = await response.json();
            sequence = updated;
            activeIndex = index;
            updatePrompt();
            renderSidebar();
            renderOverlays();
            syncTransform();
          } catch {
            // clear failed
          }
        });
        item.appendChild(clearBtn);
      }

      roiList.appendChild(item);
    });
  }

  function renderOverlays() {
    roiCanvas.width = config.cols;
    roiCanvas.height = config.rows;

    roiCtx.clearRect(0, 0, config.cols, config.rows);

    for (const slot of sequence) {
      if (!slot.rect) continue;
      const { row, col, height, width } = slot.rect;
      const colorBase = roiColor(slot);
      roiCtx.strokeStyle = colorBase + "1)";
      roiCtx.lineWidth = 2;
      roiCtx.strokeRect(col + 0.5, row + 0.5, width - 1, height - 1);
      roiCtx.fillStyle = colorBase + "0.08)";
      roiCtx.fillRect(col, row, width, height);
    }

    if (drawing && drawStart && drawEnd) {
      let r = normalizeRect(drawStart, drawEnd);
      r = applyWhiteSnap(r);
      roiCtx.strokeStyle = "#ffffff";
      roiCtx.lineWidth = 1;
      roiCtx.setLineDash([4, 4]);
      roiCtx.strokeRect(r.col + 0.5, r.row + 0.5, r.width - 1, r.height - 1);
      roiCtx.setLineDash([]);
    }
  }

  function syncTransform() {
    roiCanvas.style.transform = `translate(${display.panX}px, ${display.panY}px) scale(${display.zoom})`;
  }

  function getBlackRect() {
    const black = sequence.find((s) => s.key === "black");
    return black && black.rect ? black.rect : null;
  }

  function applyWhiteSnap(rect) {
    if (activeIndex >= sequence.length) return rect;
    const slot = sequence[activeIndex];
    if (slot.key !== "white") return rect;

    const blackRect = getBlackRect();
    if (!blackRect) return rect;

    return { row: rect.row, col: rect.col, height: blackRect.height, width: blackRect.width };
  }

  function normalizeRect(a, b) {
    const row = Math.min(a.y, b.y);
    const col = Math.min(a.x, b.x);
    const height = Math.abs(b.y - a.y);
    const width = Math.abs(b.x - a.x);
    return { row, col, height, width };
  }

  function handleMouseDown(event) {
    if (event.button !== 0 || activeIndex >= sequence.length) return;
    if (event.shiftKey) return; // allow pan with shift

    const pixel = screenToPixel(canvasContainer, display, event.clientX, event.clientY);
    if (pixel.x < 0 || pixel.x >= config.cols || pixel.y < 0 || pixel.y >= config.rows) return;

    drawing = true;
    drawStart = pixel;
    drawEnd = pixel;
    event.preventDefault();
    event.stopPropagation();
  }

  function handleMouseMove(event) {
    if (!drawing) return;

    const pixel = screenToPixel(canvasContainer, display, event.clientX, event.clientY);
    drawEnd = {
      x: clamp(pixel.x, 0, config.cols),
      y: clamp(pixel.y, 0, config.rows),
    };
    renderOverlays();
    syncTransform();
  }

  async function handleMouseUp() {
    if (!drawing) return;
    drawing = false;

    const rect = normalizeRect(drawStart, drawEnd);
    if (rect.width < 2 || rect.height < 2) {
      renderOverlays();
      syncTransform();
      return;
    }

    const slot = sequence[activeIndex];
    try {
      const response = await fetch("/actions/roi", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: slot.key, rect }),
      });

      if (!response.ok) return;

      const updated = await response.json();
      sequence = updated;

      activeIndex = findNextIncomplete(activeIndex);
      updatePrompt();
      renderSidebar();
      renderOverlays();
      syncTransform();
    } catch {
      // commit failed
    }
  }

  canvasContainer.addEventListener("mousedown", handleMouseDown);
  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);

  updatePrompt();
  renderSidebar();

  return {
    render() {
      renderOverlays();
      syncTransform();
    },
    syncTransform,
    setSequence(seq) {
      sequence = seq;
      activeIndex = findNextIncomplete(0);
      updatePrompt();
      renderSidebar();
      renderOverlays();
      syncTransform();
    },
  };
}
