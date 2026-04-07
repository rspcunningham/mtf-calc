const $ = (id) => document.getElementById(id);

// -- File upload (load page) --

const dropZone = $("drop-zone");
const fileInput = $("file-input");
const status = $("landing-status");

if (dropZone && fileInput) {
  const browseBtn = $("browse-btn");

  const upload = async (file) => {
    if (status) status.textContent = `Uploading ${file.name}...`;

    const response = await fetch("/actions/load", {
      method: "POST",
      body: file,
    });

    if (response.ok || response.redirected) {
      window.location.assign("/");
    } else {
      const msg = await response.text();
      if (status) {
        status.textContent = msg;
        status.className = "landing-status error";
      }
    }
  };

  if (browseBtn) browseBtn.addEventListener("click", (e) => { e.stopPropagation(); fileInput.click(); });
  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => { if (e.target.files[0]) upload(e.target.files[0]); });

  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]);
  });
}

// -- Stage navigation --

const btnNext = $("btn-next");

if (btnNext) {
  btnNext.addEventListener("click", async () => {
    btnNext.disabled = true;
    const response = await fetch("/actions/next", { method: "POST" });
    if (response.ok || response.redirected) {
      window.location.assign("/");
    }
  });
}
