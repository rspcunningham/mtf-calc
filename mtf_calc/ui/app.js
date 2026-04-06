import {
  applyCanvasTransform,
  fitDisplay,
  oneToOneDisplay,
  percentileFromHistogram,
  renderHistogram,
  renderSourceImage,
  screenToPixel,
} from "./render.js";
import { createROIController } from "./roi.js";
import { clamp, fmtNum } from "./utils.js";

const $ = (id) => document.getElementById(id);

const page = document.body.dataset.page;

if (page === "select") {
  initSelectPage();
} else if (page === "view") {
  initViewPage();
}

function initSelectPage() {
  const dropZone = $("drop-zone");
  const browseButton = $("browse-btn");
  const fileInput = $("file-input");
  const status = $("landing-status");

  const setStatus = (message, tone = "") => {
    status.textContent = message;
    status.className = tone ? `landing-status ${tone}` : "landing-status";
  };

  const beginUpload = async (file) => {
    setStatus(`Uploading ${file.name}...`);

    try {
      await uploadSourceFile(file);
      window.location.assign("/");
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      fileInput.value = "";
    }
  };

  browseButton.addEventListener("click", (event) => {
    event.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (event) => {
    if (event.target.files && event.target.files[0]) {
      beginUpload(event.target.files[0]);
    }
  });

  dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
  });

  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-over");

    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      beginUpload(event.dataTransfer.files[0]);
    }
  });

  document.body.addEventListener("dragover", (event) => event.preventDefault());
  document.body.addEventListener("drop", (event) => event.preventDefault());

  initConfigPanel();
}

async function initConfigPanel() {
  const freqList = $("freq-list");
  const addBtn = $("freq-add");
  const saveBtn = $("freq-save");

  const renderRows = (frequencies) => {
    freqList.innerHTML = "";
    frequencies.forEach((freq, index) => {
      const row = document.createElement("div");
      row.className = "freq-row";
      row.innerHTML =
        `<input class="freq-input" type="text" value="${freq.toExponential(2)}" data-index="${index}">` +
        `<button class="freq-remove" type="button" data-index="${index}">&times;</button>`;
      freqList.appendChild(row);
    });
  };

  const loadFrequencies = async () => {
    const response = await fetch("/config");
    const data = await response.json();
    renderRows(data.frequencies);
  };

  const collectFrequencies = () => {
    const inputs = freqList.querySelectorAll(".freq-input");
    const freqs = [];
    for (const input of inputs) {
      const val = Number(input.value);
      if (!Number.isFinite(val) || val <= 0) return null;
      freqs.push(val);
    }
    return freqs;
  };

  addBtn.addEventListener("click", () => {
    const row = document.createElement("div");
    row.className = "freq-row";
    row.innerHTML =
      `<input class="freq-input" type="text" value="">` +
      `<button class="freq-remove" type="button">&times;</button>`;
    freqList.appendChild(row);
    row.querySelector(".freq-input").focus();
  });

  freqList.addEventListener("click", (event) => {
    if (event.target.classList.contains("freq-remove")) {
      event.target.closest(".freq-row").remove();
    }
  });

  saveBtn.addEventListener("click", async () => {
    const freqs = collectFrequencies();
    if (!freqs || freqs.length === 0) return;

    await fetch("/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frequencies: freqs }),
    });

    await loadFrequencies();
  });

  loadFrequencies();
}

async function initViewPage() {
  const configNode = $("source-config");
  if (!configNode) {
    return;
  }

  const config = JSON.parse(configNode.textContent);
  const fileInput = $("file-input");
  const histogramCanvas = $("histogram-canvas");
  const histogramContainer = $("histogram-container");
  const histLabelMin = $("hist-label-min");
  const histLabelMax = $("hist-label-max");
  const histWlInfo = $("hist-wl-info");
  const canvasContainer = $("canvas-container");
  const mainCanvas = $("main-canvas");
  const mainCtx = mainCanvas.getContext("2d");
  const inspector = $("inspector");
  const zoomIndicator = $("zoom-indicator");

  let roiController = null;

  const state = {
    data: null,
    display: {
      window: Math.max(config.dataMax - config.dataMin, 0.001),
      level: (config.dataMax + config.dataMin) / 2,
      zoom: 1,
      panX: 0,
      panY: 0,
    },
    interaction: {
      histDragMode: null,
      histDragStartX: 0,
      histDragStartLevel: 0,
      histDragStartWindow: 0,
      isPanning: false,
      panStartX: 0,
      panStartY: 0,
    },
  };

  const syncAllTransforms = () => {
    applyCanvasTransform({
      canvas: mainCanvas,
      display: state.display,
      zoomIndicator,
    });
    if (roiController) roiController.syncTransform();
  };


  const renderAll = () => {
    if (!state.data) {
      return;
    }

    renderHistogram({
      canvas: histogramCanvas,
      container: histogramContainer,
      counts: config.histogram,
      display: state.display,
      dataMin: config.dataMin,
      dataMax: config.dataMax,
      labels: {
        min: histLabelMin,
        max: histLabelMax,
      },
      info: histWlInfo,
      fmtNum,
    });

    renderSourceImage({
      canvas: mainCanvas,
      context: mainCtx,
      data: state.data,
      rows: config.rows,
      cols: config.cols,
      display: state.display,
    });

    syncAllTransforms();
    if (roiController) roiController.render();
  };

  const fitToView = () => {
    const next = fitDisplay(canvasContainer, config.rows, config.cols);
    state.display.zoom = next.zoom;
    state.display.panX = next.panX;
    state.display.panY = next.panY;
    syncAllTransforms();
  };

  const setOneToOne = () => {
    const next = oneToOneDisplay(canvasContainer, config.rows, config.cols);
    state.display.zoom = next.zoom;
    state.display.panX = next.panX;
    state.display.panY = next.panY;
    syncAllTransforms();
  };

  const updateInspector = (clientX, clientY) => {
    if (!state.data) {
      inspector.style.display = "none";
      return;
    }

    const point = screenToPixel(canvasContainer, state.display, clientX, clientY);
    const inside = point.x >= 0 && point.x < config.cols && point.y >= 0 && point.y < config.rows;
    if (!inside) {
      inspector.style.display = "none";
      return;
    }

    const value = state.data[point.y * config.cols + point.x];
    inspector.style.display = "block";
    inspector.innerHTML =
      `<span class="coord">[${point.y}, ${point.x}]</span>` +
      `<br><span class="inspector-label">value</span> ` +
      `<span class="inspector-value">${fmtNum(value)}</span>`;
  };

  const resetWindowLevel = () => {
    state.display.window = Math.max(config.dataMax - config.dataMin, 0.001);
    state.display.level = (config.dataMin + config.dataMax) / 2;
    renderAll();
  };

  const autoWindowLevel = () => {
    const low = percentileFromHistogram(config.histogram, 0.02);
    const high = percentileFromHistogram(config.histogram, 0.98);
    state.display.window = Math.max(high - low, 0.001);
    state.display.level = (low + high) / 2;
    renderAll();
  };

  const uploadReplacementSource = async (file) => {
    try {
      await uploadSourceFile(file);
      window.location.assign("/");
    } catch {
      // upload failed — stay on current view
    } finally {
      fileInput.value = "";
    }
  };

  const handleHistogramPointerDown = (event) => {
    const rect = histogramContainer.getBoundingClientRect();
    const fx = clamp((event.clientX - rect.left) / rect.width, 0, 1);
    const winLo = state.display.level - state.display.window / 2;
    const winHi = state.display.level + state.display.window / 2;

    if (Math.abs(fx - winLo) < 0.02) {
      state.interaction.histDragMode = "left-edge";
    } else if (Math.abs(fx - winHi) < 0.02) {
      state.interaction.histDragMode = "right-edge";
    } else if (fx > winLo && fx < winHi) {
      state.interaction.histDragMode = "center";
    } else {
      state.display.level = fx;
      state.interaction.histDragMode = "center";
      renderAll();
    }

    state.interaction.histDragStartX = fx;
    state.interaction.histDragStartLevel = state.display.level;
    state.interaction.histDragStartWindow = state.display.window;
  };

  const handleHistogramPointerMove = (event) => {
    if (!state.interaction.histDragMode) {
      return;
    }

    const rect = histogramContainer.getBoundingClientRect();
    const fx = clamp((event.clientX - rect.left) / rect.width, 0, 1);
    const delta = fx - state.interaction.histDragStartX;

    if (state.interaction.histDragMode === "center") {
      state.display.level = clamp(state.interaction.histDragStartLevel + delta, 0, 1);
    } else if (state.interaction.histDragMode === "left-edge") {
      const right = state.interaction.histDragStartLevel + state.interaction.histDragStartWindow / 2;
      const left = clamp(
        state.interaction.histDragStartLevel - state.interaction.histDragStartWindow / 2 + delta,
        0,
        right - 0.001,
      );
      state.display.window = right - left;
      state.display.level = (left + right) / 2;
    } else if (state.interaction.histDragMode === "right-edge") {
      const left = state.interaction.histDragStartLevel - state.interaction.histDragStartWindow / 2;
      const right = clamp(
        state.interaction.histDragStartLevel + state.interaction.histDragStartWindow / 2 + delta,
        left + 0.001,
        1,
      );
      state.display.window = right - left;
      state.display.level = (left + right) / 2;
    }

    state.display.window = clamp(state.display.window, 0.001, 1);
    state.display.level = clamp(state.display.level, 0, 1);
    renderAll();
  };

  const handleMouseWheel = (event) => {
    if (!state.data) {
      return;
    }

    event.preventDefault();
    const rect = canvasContainer.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    const oldZoom = state.display.zoom;
    const factor = event.deltaY < 0 ? 1.1 : 1 / 1.1;

    state.display.zoom = clamp(state.display.zoom * factor, 0.05, 128);
    state.display.panX = mouseX - (mouseX - state.display.panX) * (state.display.zoom / oldZoom);
    state.display.panY = mouseY - (mouseY - state.display.panY) * (state.display.zoom / oldZoom);

    syncAllTransforms();
  };

  const handleCanvasMouseDown = (event) => {
    if (event.button !== 0 || !event.shiftKey) {
      return;
    }

    state.interaction.isPanning = true;
    state.interaction.panStartX = event.clientX - state.display.panX;
    state.interaction.panStartY = event.clientY - state.display.panY;
  };

  const handleWindowMouseMove = (event) => {
    if (state.interaction.isPanning) {
      state.display.panX = event.clientX - state.interaction.panStartX;
      state.display.panY = event.clientY - state.interaction.panStartY;
      syncAllTransforms();
    }

    updateInspector(event.clientX, event.clientY);
    handleHistogramPointerMove(event);
  };

  const handleWindowMouseUp = () => {
    state.interaction.isPanning = false;
    state.interaction.histDragMode = null;
  };

  $("btn-open").addEventListener("click", () => fileInput.click());
  $("btn-fit").addEventListener("click", fitToView);
  $("btn-1x").addEventListener("click", setOneToOne);

  $("hist-auto-btn").addEventListener("click", autoWindowLevel);
  $("hist-reset-btn").addEventListener("click", resetWindowLevel);

  fileInput.addEventListener("change", (event) => {
    if (event.target.files && event.target.files[0]) {
      uploadReplacementSource(event.target.files[0]);
    }
  });

  histogramContainer.addEventListener("mousedown", handleHistogramPointerDown);
  canvasContainer.addEventListener("wheel", handleMouseWheel, { passive: false });
  canvasContainer.addEventListener("mousedown", handleCanvasMouseDown);
  window.addEventListener("mousemove", handleWindowMouseMove);
  window.addEventListener("mouseup", handleWindowMouseUp);

  window.addEventListener("keydown", (event) => {
    if (event.target && event.target.tagName === "INPUT") {
      return;
    }

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "o") {
      event.preventDefault();
      fileInput.click();
    } else if (event.key === "f") {
      fitToView();
    } else if (event.key === "1") {
      setOneToOne();
    } else if (event.key === "a") {
      autoWindowLevel();
    } else if (event.key === "r") {
      resetWindowLevel();
    }
  });

  window.addEventListener("resize", () => {
    if (state.data) {
      renderAll();
    }
  });

  try {
    const buffer = await fetchSourceBuffer();
    const data = new Float32Array(buffer);
    const expectedLength = config.rows * config.cols;
    if (data.length !== expectedLength) {
      throw new Error("Source buffer length does not match source metadata.");
    }

    state.data = data;

    roiController = createROIController({
      config,
      canvasContainer,
      display: state.display,
    });

    renderAll();
    requestAnimationFrame(() => fitToView());
  } catch {
    // source fetch failed
  }
}

async function uploadSourceFile(file) {
  const query = new URLSearchParams({ name: file.name });
  const response = await fetch(`/actions/source/upload?${query.toString()}`, {
    method: "POST",
    body: file,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Upload failed with ${response.status}.`);
  }
}

async function fetchSourceBuffer() {
  const response = await fetch("/render/source.float32");
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Source request failed with ${response.status}.`);
  }

  return response.arrayBuffer();
}
