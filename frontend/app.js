const navButtons = document.querySelectorAll(".nav-btn");
const pages = document.querySelectorAll(".page");

function showPage(pageName) {
  pages.forEach((page) => {
    page.classList.toggle("active", page.id === `page-${pageName}`);
  });
  navButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === pageName);
  });

  if (pageName === "satellite" && map) {
    setTimeout(() => map.invalidateSize(), 0);
  }
}

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => showPage(btn.dataset.page));
});

document.getElementById("go-to-satellite").addEventListener("click", () => {
  showPage("satellite");
});

document.getElementById("go-to-photo").addEventListener("click", () => {
    showPage("photo");
});


const map = L.map("map").setView([42.032, -93.6175], 14);

L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    attribution: "Tiles &copy; Esri",
    maxZoom: 19,
  }
).addTo(map);

const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
  draw: {
    polygon: {
      shapeOptions: {
        color: "#e63946",
        weight: 3,
        fillColor: "#e63946",
        fillOpacity: 0.08,
      },
    },
    marker: false,
    polyline: false,
    circle: false,
    circlemarker: false,
    rectangle: false,
  },
  edit: {
    featureGroup: drawnItems,
  },
});
map.addControl(drawControl);

map.on(L.Draw.Event.CREATED, function (event) {
  const layer = event.layer;
  drawnItems.clearLayers();
  drawnItems.addLayer(layer);

  const hint = document.getElementById("draw-hint");
  if (hint) hint.classList.add("hidden");

  showLoadingState(layer);

  const latlngs = layer.getLatLngs()[0];
  const coordinates = latlngs.map((point) => [point.lng, point.lat]);
  coordinates.push(coordinates[0]);

  fetchNDVI(coordinates, layer);
});


let loadingLayer = null;
let loadingInterval = null;
let spinnerMarker = null;

function showLoadingState(fieldLayer) {
  clearLoadingState();

  loadingLayer = L.geoJSON(fieldLayer.toGeoJSON(), {
    style: {
      stroke: false,
      fillColor: "#e63946",
      fillOpacity: 0.18,
    },
  }).addTo(map);

  let increasing = true;
  let opacity = 0.18;
  loadingInterval = setInterval(() => {
    opacity += increasing ? 0.02 : -0.02;
    if (opacity >= 0.32) increasing = false;
    if (opacity <= 0.12) increasing = true;
    loadingLayer.setStyle({ fillOpacity: opacity });
  }, 60);

  const center = fieldLayer.getBounds().getCenter();
  const spinnerIcon = L.divIcon({
    className: "spinner-icon-wrapper",
    html: '<div class="spinner"></div>',
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
  spinnerMarker = L.marker(center, {
    icon: spinnerIcon,
    interactive: false,
  }).addTo(map);
}

function clearLoadingState() {
  if (loadingInterval) {
    clearInterval(loadingInterval);
    loadingInterval = null;
  }
  if (loadingLayer) {
    map.removeLayer(loadingLayer);
    loadingLayer = null;
  }
  if (spinnerMarker) {
    map.removeLayer(spinnerMarker);
    spinnerMarker = null;
  }
}

const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");

searchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = searchInput.value.trim();
  if (!query) return;

  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
      query
    )}&limit=1`;
    const response = await fetch(url);
    const results = await response.json();

    if (results.length === 0) {
      alert("Couldn't find that location. Try a different search.");
      return;
    }

    const { lat, lon } = results[0];
    map.setView([parseFloat(lat), parseFloat(lon)], 14);
  } catch (error) {
    console.error("Geocoding failed:", error);
    alert("Search failed — check your connection and try again.");
  }
});

async function fetchNDVI(coordinates, fieldLayer) {
  try {
    const response = await fetch("http://127.0.0.1:8000/fields/ndvi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ coordinates }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Request failed");
    }

    const data = await response.json();
    clearLoadingState();
    renderHeatmap(data, fieldLayer);
    renderResults(data);
  } catch (error) {
    clearLoadingState();
    console.error("Failed to fetch NDVI:", error);
    alert("Couldn't fetch satellite data: " + error.message);
  }
}

let heatmapLayer = null;

function renderHeatmap(data, fieldLayer) {
  if (heatmapLayer) {
    map.removeLayer(heatmapLayer);
  }
  heatmapLayer = L.layerGroup();

  const bounds = fieldLayer.getBounds();
  const south = bounds.getSouth();
  const north = bounds.getNorth();
  const west = bounds.getWest();
  const east = bounds.getEast();

  const grid = data.ndvi_grid;
  const numRows = grid.length;
  const numCols = grid[0].length;

  const cellHeight = (north - south) / numRows;
  const cellWidth = (east - west) / numCols;

  for (let row = 0; row < numRows; row++) {
    for (let col = 0; col < numCols; col++) {
      const value = grid[row][col];
      if (value === null) continue;

      const cellNorth = north - row * cellHeight;
      const cellSouth = cellNorth - cellHeight;
      const cellWest = west + col * cellWidth;
      const cellEast = cellWest + cellWidth;

      const rect = L.rectangle(
        [
          [cellSouth, cellWest],
          [cellNorth, cellEast],
        ],
        {
          stroke: false,
          fillColor: ndviToColor(value),
          fillOpacity: 0.7,
        }
      );
      heatmapLayer.addLayer(rect);
    }
  }

  heatmapLayer.addTo(map);
}

function ndviToColor(value) {
  const clamped = Math.max(0, Math.min(0.8, value));
  const t = clamped / 0.8;

  let r, g, b;
  if (t < 0.5) {
    const localT = t / 0.5;
    r = 200;
    g = Math.round(60 + localT * 140);
    b = 40;
  } else {
    const localT = (t - 0.5) / 0.5;
    r = Math.round(200 - localT * 160);
    g = Math.round(200 + localT * 20);
    b = 40;
  }
  return `rgb(${r}, ${g}, ${b})`;
}


(function renderHeroSwatchGrid() {
  const container = document.getElementById("hero-grid");
  if (!container) return;

  const rows = 5;
  const cols = 6;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const centerDist =
        Math.abs(row - rows / 2) / rows + Math.abs(col - cols / 2) / cols;
      const base = 0.65 - centerDist * 0.5;
      const noise = Math.sin(row * 12.9 + col * 7.3) * 0.13;
      const value = Math.max(0.05, Math.min(0.75, base + noise));

      const swatch = document.createElement("div");
      swatch.style.background = ndviToColor(value);
      container.appendChild(swatch);
    }
  }
})();

const resultsPanel = document.getElementById("results-panel");
const scoreCircle = document.getElementById("score-circle");
const resultsSentence = document.getElementById("results-sentence");
const resultsMeta = document.getElementById("results-meta");

function ndviToHealthScore(ndviMean) {
  const clamped = Math.max(0, Math.min(0.85, ndviMean));
  return Math.round((clamped / 0.85) * 100);
}

function scoreToColor(score) {
  if (score >= 70) return "#2d6a4f";
  if (score >= 40) return "#d4a017";
  return "#c1440e";
}

function summarySentence(score, ndviMean) {
  if (score >= 75) {
    return "This field shows strong, healthy vegetation across most of the area.";
  } else if (score >= 50) {
    return "This field shows moderate vegetation health, with some weaker zones.";
  } else if (score >= 25) {
    return "This field shows signs of stress or sparse vegetation in much of the area.";
  } else {
    return "This field shows mostly bare soil or significant vegetation stress.";
  }
}

function renderResults(data) {
  const score = ndviToHealthScore(data.ndvi_mean);

  scoreCircle.textContent = score;
  scoreCircle.style.background = scoreToColor(score);
  resultsSentence.textContent = summarySentence(score, data.ndvi_mean);
  resultsMeta.textContent = `Satellite pass: ${formatDate(data.scene_date)} · Cloud cover: ${data.cloud_cover.toFixed(1)}%`;

  resultsPanel.classList.remove("hidden");

  const legend = document.getElementById("score-legend");
  if (legend) legend.classList.remove("hidden");
}

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

const uploadZone = document.getElementById("upload-zone");
const photoInput = document.getElementById("photo-input");
const uploadPrompt = document.getElementById("upload-prompt");
const photoPreview = document.getElementById("photo-preview");
const photoLoading = document.getElementById("photo-loading");
const photoResultsPanel = document.getElementById("photo-results");
const photoScoreCircle = document.getElementById("photo-score-circle");
const photoResultsSentence = document.getElementById("photo-results-sentence");
const photoResultsMeta = document.getElementById("photo-results-meta");
const photoScoreLegend = document.getElementById("photo-score-legend");

if (uploadZone) {
  uploadZone.addEventListener("click", () => photoInput.click());

  photoInput.addEventListener("change", () => {
    const file = photoInput.files[0];
    if (file) handlePhotoUpload(file);
  });

  uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });

  uploadZone.addEventListener("dragleave", () => {
    uploadZone.classList.remove("dragover");
  });

  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) handlePhotoUpload(file);
  });
}

function handlePhotoUpload(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please upload an image file (JPG or PNG).");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    photoPreview.src = e.target.result;
    photoPreview.classList.remove("hidden");
    uploadPrompt.classList.add("hidden");
  };
  reader.readAsDataURL(file);

  photoLoading.classList.remove("hidden");
  photoResultsPanel.classList.add("hidden");
  photoScoreLegend.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", file);

  fetch("http://127.0.0.1:8000/photos/analyze", {
    method: "POST",
    body: formData,
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Request failed");
      }
      return response.json();
    })
    .then((data) => {
      photoLoading.classList.add("hidden");
      renderPhotoResults(data);
    })
    .catch((error) => {
      photoLoading.classList.add("hidden");
      console.error("Failed to analyze photo:", error);
      alert("Couldn't analyze photo: " + error.message);
    });
}

function photoScoreToColor(score) {
  if (score >= 70) return "#2d6a4f";
  if (score >= 40) return "#d4a017";
  return "#c1440e";
}

function renderPhotoResults(data) {
  if (data.health_score === null || data.health_score === undefined) {
    photoResultsSentence.textContent =
      data.summary || "No plant was clearly visible in this photo.";
    photoScoreCircle.textContent = "--";
    photoScoreCircle.style.background = "#6b7a6e";
    photoResultsMeta.textContent = "";
    photoResultsPanel.classList.remove("hidden");
    return;
  }

  const score = Math.round(data.health_score);
  photoScoreCircle.textContent = score;
  photoScoreCircle.style.background = photoScoreToColor(score);
  photoResultsSentence.textContent = data.summary;

  if (data.issues_detected && data.issues_detected.length > 0) {
    photoResultsMeta.textContent = `Detected: ${data.issues_detected.join(", ")}`;
  } else {
    photoResultsMeta.textContent = "No specific issues detected";
  }

  photoResultsPanel.classList.remove("hidden");
  photoScoreLegend.classList.remove("hidden");
}

photoResultsPanel.classList.remove("hidden")