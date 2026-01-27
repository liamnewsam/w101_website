const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
let drawing = false;


// ------------------ INITIAL BLACK BACKGROUND ------------------
function resetCanvas() {
  ctx.fillStyle = "black";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}
resetCanvas();


function resizeCanvasForHiDPI() {
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;

  // Resizing clears the canvas — unavoidable
  canvas.width = rect.width * scale;
  canvas.height = rect.height * scale;

  // Reset scale
  ctx.scale(scale, scale);

  // Redraw the background
  resetCanvas()
}

resizeCanvasForHiDPI();
window.addEventListener("resize", resizeCanvasForHiDPI);


// ------------------ POSITION HELPERS ------------------
function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  if (e.touches) {
    return {
      x: (e.touches[0].clientX - rect.left) * scaleX,
      y: (e.touches[0].clientY - rect.top) * scaleY
    };
  }

  return {
    x: e.offsetX * scaleX,
    y: e.offsetY * scaleY
  };
}

// ------------------ DRAWING EVENTS ------------------
function startDraw(e) {
  e.preventDefault();
  drawing = true;

  const { x, y } = getPos(e);
  ctx.beginPath();
  ctx.moveTo(x, y);
}

function moveDraw(e) {
  if (!drawing) return;

  const { x, y } = getPos(e);

  ctx.lineWidth = 40;
  ctx.lineCap = "round";
  ctx.strokeStyle = "white";

  ctx.lineTo(x, y);
  ctx.stroke();
}

function endDraw() {
  drawing = false;
}

canvas.addEventListener('mousedown', startDraw);
canvas.addEventListener('mousemove', moveDraw);
canvas.addEventListener('mouseup', endDraw);
canvas.addEventListener('mouseleave', endDraw);

canvas.addEventListener('touchstart', startDraw, { passive: false });
canvas.addEventListener('touchmove', moveDraw, { passive: false });
canvas.addEventListener('touchend', endDraw);
canvas.addEventListener('touchcancel', endDraw);

// ------------------ ERASE BUTTON ------------------
document.getElementById('erase').addEventListener('click', resetCanvas);

// ------------------ PREDICT BUTTON ------------------
document.getElementById('predict').addEventListener('click', async () => {
  // Downscale to 280x280 for backend
  const small = document.createElement('canvas');
  small.width = 280;
  small.height = 280;
  const sctx = small.getContext('2d');

  sctx.drawImage(canvas, 0, 0, 280, 280);

  const dataUrl = small.toDataURL('image/png');

  const response = await fetch(
    'http://0.0.0.0:5000/digit-predict',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: dataUrl })
    }
  );

  const result = await response.json();
  
  console.log(result)
  const probs = result.probabilities;

  const predDigit = probs.indexOf(Math.max(...probs));
  document.getElementById('result').innerText = `Prediction: ${predDigit}`;

  updateChart(probs);
});


// ------------------ Draw Function ------------------

function initializeChart() {
  const tbody = document.querySelector("#prob-chart tbody");
  tbody.innerHTML = "";

  for (let i = 0; i < 10; i++) {
    const tr = document.createElement("tr");

    const th = document.createElement("th");
    th.scope = "row";
    th.textContent = i;

    const td = document.createElement("td");
    td.dataset.index = i;
    td.style.setProperty("--size", 0);

    tr.appendChild(th);
    tr.appendChild(td);
    tbody.appendChild(tr);

    const valueSpan = document.createElement("span");
    valueSpan.className = "bar-value";
    valueSpan.textContent = "0";

    td.appendChild(valueSpan);
  }
}

initializeChart();


function updateChart(probabilities) {
  // Find the index of the highest probability
  const maxVal = Math.max(...probabilities);
  const maxIndex = probabilities.indexOf(maxVal);

  probabilities.forEach((p, i) => {
    const td = document.querySelector(`#prob-chart td[data-index="${i}"]`);

    // Normalize so the largest bar = 1.0
    //const normalized = p / maxVal;

    // Update bar size
    td.style.setProperty("--size", p);

    const span = td.querySelector(".bar-value");
    span.textContent = p.toFixed(3);

    // Highlight (remove previous highlights)
    td.classList.toggle("highlight", i === maxIndex);
  });
}
