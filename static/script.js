const canvas = document.getElementById("digitCanvas");
const ctx = canvas.getContext("2d");
const digitSelect = document.getElementById("digitSelect");
const clearBtn = document.getElementById("clearBtn");
const submitBtn = document.getElementById("submitBtn");
const statusEl = document.getElementById("status");

let drawing = false;
let lastX = 0;
let lastY = 0;

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = "status" + (type ? " " + type : "");
}

function resizeForHiDPI() {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.width;
  const height = canvas.height;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  ctx.scale(ratio, ratio);
  initCanvas();
}

function initCanvas() {
  ctx.fillStyle = "#0b1120";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 18;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#ffffff";
}

function getCanvasPos(e) {
  const rect = canvas.getBoundingClientRect();
  const isTouch = e.touches && e.touches.length > 0;
  const clientX = isTouch ? e.touches[0].clientX : e.clientX;
  const clientY = isTouch ? e.touches[0].clientY : e.clientY;
  return {
    x: clientX - rect.left,
    y: clientY - rect.top,
  };
}

function startDrawing(e) {
  e.preventDefault();
  const pos = getCanvasPos(e);
  drawing = true;
  lastX = pos.x;
  lastY = pos.y;
}

function draw(e) {
  if (!drawing) return;
  e.preventDefault();
  const pos = getCanvasPos(e);
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(pos.x, pos.y);
  ctx.stroke();
  lastX = pos.x;
  lastY = pos.y;
}

function stopDrawing(e) {
  if (!drawing) return;
  e.preventDefault();
  drawing = false;
}

function clearCanvas() {
  initCanvas();
  setStatus("");
}

async function submitSample() {
  const label = digitSelect.value;
  if (!label) {
    setStatus("Please choose the correct digit label.", "error");
    return;
  }

  submitBtn.disabled = true;
  clearBtn.disabled = true;
  setStatus("Sending sample...", "");

  const dataUrl = canvas.toDataURL("image/png");
  try {
    const res = await fetch("/api/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        label,
        image: dataUrl,
      }),
    });

    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.status !== "ok") {
      throw new Error(body.message || "Server error, please try again.");
    }

    setStatus("Sample saved, thank you! You can draw another one.", "success");
    clearCanvas();
  } catch (err) {
    console.error(err);
    setStatus("Failed to send sample. Check your connection and try again.", "error");
  } finally {
    submitBtn.disabled = false;
    clearBtn.disabled = false;
  }
}

// Mouse events
canvas.addEventListener("mousedown", startDrawing);
canvas.addEventListener("mousemove", draw);
canvas.addEventListener("mouseup", stopDrawing);
canvas.addEventListener("mouseleave", stopDrawing);

// Touch events
canvas.addEventListener("touchstart", startDrawing, { passive: false });
canvas.addEventListener("touchmove", draw, { passive: false });
canvas.addEventListener("touchend", stopDrawing, { passive: false });
canvas.addEventListener("touchcancel", stopDrawing, { passive: false });

clearBtn.addEventListener("click", clearCanvas);
submitBtn.addEventListener("click", submitSample);

// Initialize
initCanvas();


