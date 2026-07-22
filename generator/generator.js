"use strict";

/*
  Z-PANEL – BRUCHLAST-Kurvengenerator
  generator.js

  Funktionen:
  - Metadaten erfassen
  - Messwerte verwalten
  - Quellen verwalten
  - Belastungswerte berechnen
  - Diagramm zeichnen
  - Tooltips anzeigen
  - Daten im Browser speichern
  - JSON importieren und exportieren
  - Diagramm als PNG speichern
*/


// ============================================================
// 1. Grundeinstellungen
// ============================================================

const STORAGE_KEY = "z-panel-generator-dataset-v1";

const state = {
  dataset: {
    id: "",
    title: "",
    shortTitle: "",
    planetaryBoundary: "",
    description: "",
    unit: "",
    burdenDirection: "increasing",

    normalization: {
      lowerValue: 0,
      upperValue: 100
    },

    values: []
  },

  sources: [],

  review: {
    status: "draft",
    createdBy: "",
    createdAt: "",
    reviewedBy: "",
    reviewedAt: "",
    version: "0.1"
  }
};


// Punkte des Diagramms für die Maus-Erkennung
let chartPoints = [];


// ============================================================
// 2. HTML-Elemente
// ============================================================

const elements = {
  datasetTitle: document.getElementById("dataset-title"),
  datasetShortTitle: document.getElementById("dataset-short-title"),
  datasetDescription: document.getElementById("dataset-description"),
  planetaryBoundary: document.getElementById("planetary-boundary"),
  datasetUnit: document.getElementById("dataset-unit"),
  burdenDirection: document.getElementById("burden-direction"),

  lowerReference: document.getElementById("lower-reference"),
  upperReference: document.getElementById("upper-reference"),

  valuesTableBody: document.getElementById("values-table-body"),
  addValueButton: document.getElementById("add-value-button"),

  sourceShortName: document.getElementById("source-short-name"),
  sourceInstitution: document.getElementById("source-institution"),
  sourceTitle: document.getElementById("source-title"),
  sourceUrl: document.getElementById("source-url"),
  sourceAccessed: document.getElementById("source-accessed"),
  sourceLocation: document.getElementById("source-location"),
  sourceNote: document.getElementById("source-note"),

  addSourceButton: document.getElementById("add-source-button"),
  sourceList: document.getElementById("source-list"),

  saveButton: document.getElementById("save-button"),
  loadButton: document.getElementById("load-button"),
  exportButton: document.getElementById("export-button"),
  importFile: document.getElementById("import-file"),
  exampleButton: document.getElementById("example-button"),
  resetButton: document.getElementById("reset-button"),

  downloadChartButton: document.getElementById("download-chart-button"),

  chartTitle: document.getElementById("chart-title"),
  chartSubtitle: document.getElementById("chart-subtitle"),
  chartCanvas: document.getElementById("chart-canvas"),
  chartTooltip: document.getElementById("chart-tooltip"),

  jsonPreview: document.getElementById("json-preview"),
  statusMessage: document.getElementById("status-message")
};


const chartContext = elements.chartCanvas.getContext("2d");


// ============================================================
// 3. Hilfsfunktionen
// ============================================================

function createIdFromTitle(title) {
  return String(title || "")
    .toLowerCase()
    .trim()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}


function createSourceId() {
  const existingNumbers = state.sources
    .map((source) => {
      const match = String(source.id || "").match(/^Q(\d+)$/i);
      return match ? Number(match[1]) : 0;
    });

  const highestNumber =
    existingNumbers.length > 0
      ? Math.max(...existingNumbers)
      : 0;

  return `Q${String(highestNumber + 1).padStart(3, "0")}`;
}


function getToday() {
  return new Date().toISOString().slice(0, 10);
}


function parseNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const normalizedValue = String(value)
    .trim()
    .replace(",", ".");

  const number = Number(normalizedValue);

  return Number.isFinite(number)
    ? number
    : null;
}


function formatNumber(value, maximumDigits = 2) {
  if (!Number.isFinite(value)) {
    return "–";
  }

  return new Intl.NumberFormat("de-DE", {
    maximumFractionDigits: maximumDigits
  }).format(value);
}


function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


function setStatus(message, type = "success") {
  elements.statusMessage.textContent = message;
  elements.statusMessage.className = `status ${type}`;

  window.clearTimeout(setStatus.timeoutId);

  setStatus.timeoutId = window.setTimeout(() => {
    elements.statusMessage.textContent = "";
    elements.statusMessage.className = "status";
  }, 5000);
}


function getSourceById(sourceId) {
  return state.sources.find(
    (source) => source.id === sourceId
  );
}


function calculateBurden(value) {
  const originalValue = parseNumber(value);
  const lowerValue = parseNumber(
    state.dataset.normalization.lowerValue
  );
  const upperValue = parseNumber(
    state.dataset.normalization.upperValue
  );

  if (
    originalValue === null ||
    lowerValue === null ||
    upperValue === null ||
    lowerValue === upperValue
  ) {
    return null;
  }

  let burden;

  if (state.dataset.burdenDirection === "decreasing") {
    burden =
      ((upperValue - originalValue) /
        (upperValue - lowerValue)) *
      100;
  } else {
    burden =
      ((originalValue - lowerValue) /
        (upperValue - lowerValue)) *
      100;
  }

  return burden;
}


function normalizeMeasurement(measurement) {
  return {
    year: parseNumber(measurement.year),
    value: parseNumber(measurement.value),
    sourceIds: Array.isArray(measurement.sourceIds)
      ? measurement.sourceIds.filter(Boolean)
      : measurement.sourceId
        ? [measurement.sourceId]
        : [],
    note: String(measurement.note || "")
  };
}


function getValidMeasurements() {
  return state.dataset.values
    .map(normalizeMeasurement)
    .filter(
      (measurement) =>
        measurement.year !== null &&
        measurement.value !== null
    )
    .sort((a, b) => a.year - b.year);
}


function getExportData() {
  return {
    format: "z-panel-dataset",
    schemaVersion: 1,

    dataset: {
      ...state.dataset,

      normalization: {
        ...state.dataset.normalization
      },

      values: state.dataset.values.map(
        normalizeMeasurement
      )
    },

    sources: state.sources.map((source) => ({
      ...source
    })),

    review: {
      ...state.review
    }
  };
}


// ============================================================
// 4. Metadaten
// ============================================================

function readMetadataFromForm() {
  state.dataset.title =
    elements.datasetTitle.value.trim();

  state.dataset.shortTitle =
    elements.datasetShortTitle.value.trim();

  state.dataset.description =
    elements.datasetDescription.value.trim();

  state.dataset.planetaryBoundary =
    elements.planetaryBoundary.value;

  state.dataset.unit =
    elements.datasetUnit.value.trim();

  state.dataset.burdenDirection =
    elements.burdenDirection.value;

  state.dataset.normalization.lowerValue =
    parseNumber(elements.lowerReference.value);

  state.dataset.normalization.upperValue =
    parseNumber(elements.upperReference.value);

  state.dataset.id =
    state.dataset.id ||
    createIdFromTitle(state.dataset.title);

renderMeasurements();
drawChart();
updateJsonPreview();
}


function writeMetadataToForm() {
  elements.datasetTitle.value =
    state.dataset.title || "";

  elements.datasetShortTitle.value =
    state.dataset.shortTitle || "";

  elements.datasetDescription.value =
    state.dataset.description || "";

  elements.planetaryBoundary.value =
    state.dataset.planetaryBoundary || "";

  elements.datasetUnit.value =
    state.dataset.unit || "";

  elements.burdenDirection.value =
    state.dataset.burdenDirection || "increasing";

  elements.lowerReference.value =
    state.dataset.normalization.lowerValue ?? "";

  elements.upperReference.value =
    state.dataset.normalization.upperValue ?? "";
}


// ============================================================
// 5. Messwerttabelle
// ============================================================

function addMeasurement(measurement = {}) {
  state.dataset.values.push({
    year: measurement.year ?? "",
    value: measurement.value ?? "",
    sourceIds: Array.isArray(measurement.sourceIds)
      ? [...measurement.sourceIds]
      : [],
    note: measurement.note || ""
  });

  renderMeasurements();
  drawChart();
  updateJsonPreview();
}


function removeMeasurement(index) {
  state.dataset.values.splice(index, 1);

  renderMeasurements();
  drawChart();
  updateJsonPreview();
}


function updateMeasurement(index, field, value) {
  const measurement = state.dataset.values[index];

  if (!measurement) {
    return;
  }

  if (field === "sourceId") {
    measurement.sourceIds = value
      ? [value]
      : [];
  } else {
    measurement[field] = value;
  }

  renderMeasurements();
  drawChart();
  updateJsonPreview();
}


function createSourceOptions(selectedSourceId = "") {
  const emptyOption =
    '<option value="">Keine Quelle</option>';

  const sourceOptions = state.sources
    .map((source) => {
      const selected =
        source.id === selectedSourceId
          ? " selected"
          : "";

      const label =
        `${source.id} – ${source.shortName || source.title || "Quelle"}`;

      return `
        <option value="${escapeHtml(source.id)}"${selected}>
          ${escapeHtml(label)}
        </option>
      `;
    })
    .join("");

  return emptyOption + sourceOptions;
}


function renderMeasurements() {
  elements.valuesTableBody.innerHTML = "";

  if (state.dataset.values.length === 0) {
    const emptyRow = document.createElement("tr");

    emptyRow.innerHTML = `
      <td colspan="5">
        Noch keine Messwerte vorhanden.
      </td>
    `;

    elements.valuesTableBody.appendChild(emptyRow);
    return;
  }

  state.dataset.values.forEach(
    (measurement, index) => {
      const row = document.createElement("tr");

      const burden =
        calculateBurden(measurement.value);

      const selectedSourceId =
        measurement.sourceIds?.[0] || "";

      row.innerHTML = `
        <td>
          <input
            type="number"
            step="1"
            class="measurement-year"
            value="${escapeHtml(measurement.year)}"
            aria-label="Jahr"
          >
        </td>

        <td>
          <input
            type="number"
            step="any"
            class="measurement-value"
            value="${escapeHtml(measurement.value)}"
            aria-label="Originalwert"
          >
        </td>

        <td>
          <select
            class="measurement-source"
            aria-label="Quelle"
          >
            ${createSourceOptions(selectedSourceId)}
          </select>
        </td>

        <td class="percentage">
          ${
            burden === null
              ? "–"
              : `${formatNumber(burden, 1)} %`
          }
        </td>

        <td>
          <button
            type="button"
            class="danger small remove-measurement"
          >
            Löschen
          </button>
        </td>
      `;

      row
        .querySelector(".measurement-year")
        .addEventListener("input", (event) => {
          updateMeasurement(
            index,
            "year",
            event.target.value
          );
        });

      row
        .querySelector(".measurement-value")
        .addEventListener("input", (event) => {
          updateMeasurement(
            index,
            "value",
            event.target.value
          );
        });

      row
        .querySelector(".measurement-source")
        .addEventListener("change", (event) => {
          updateMeasurement(
            index,
            "sourceId",
            event.target.value
          );
        });

      row
        .querySelector(".remove-measurement")
        .addEventListener("click", () => {
          removeMeasurement(index);
        });

      elements.valuesTableBody.appendChild(row);
    }
  );
}


// ============================================================
// 6. Quellenverwaltung
// ============================================================

function clearSourceForm() {
  elements.sourceShortName.value = "";
  elements.sourceInstitution.value = "";
  elements.sourceTitle.value = "";
  elements.sourceUrl.value = "";
  elements.sourceAccessed.value = getToday();
  elements.sourceLocation.value = "";
  elements.sourceNote.value = "";
}


function addSource() {
  const shortName =
    elements.sourceShortName.value.trim();

  const institution =
    elements.sourceInstitution.value.trim();

  const title =
    elements.sourceTitle.value.trim();

  const url =
    elements.sourceUrl.value.trim();

  const accessed =
    elements.sourceAccessed.value;

  const location =
    elements.sourceLocation.value.trim();

  const note =
    elements.sourceNote.value.trim();

  if (!shortName && !title) {
    setStatus(
      "Bitte mindestens einen Kurznamen oder einen Quellentitel eingeben.",
      "error"
    );

    return;
  }

  state.sources.push({
    id: createSourceId(),
    shortName,
    institution,
    title,
    publicationYear: "",
    url,
    dataset: location,
    accessed,
    license: "",
    note
  });

  clearSourceForm();
  renderSources();
  renderMeasurements();
  updateJsonPreview();

  setStatus("Quelle wurde gespeichert.");
}


function removeSource(sourceId) {
  const sourceIsUsed = state.dataset.values.some(
    (measurement) =>
      measurement.sourceIds?.includes(sourceId)
  );

  if (sourceIsUsed) {
    const confirmed = window.confirm(
      "Diese Quelle wird mindestens einem Messwert zugeordnet. " +
      "Soll sie trotzdem gelöscht werden?"
    );

    if (!confirmed) {
      return;
    }
  }

  state.sources = state.sources.filter(
    (source) => source.id !== sourceId
  );

  state.dataset.values.forEach((measurement) => {
    measurement.sourceIds =
      measurement.sourceIds?.filter(
        (id) => id !== sourceId
      ) || [];
  });

  renderSources();
  renderMeasurements();
  drawChart();
  updateJsonPreview();

  setStatus("Quelle wurde gelöscht.");
}


function renderSources() {
  elements.sourceList.innerHTML = "";

  if (state.sources.length === 0) {
    elements.sourceList.innerHTML = `
      <div class="source-card">
        Noch keine Quellen angelegt.
      </div>
    `;

    return;
  }

  state.sources.forEach((source) => {
    const sourceCard = document.createElement("div");

    sourceCard.className = "source-card";

    const sourceLink = source.url
      ? `
        <p>
          <a
            href="${escapeHtml(source.url)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Quelle öffnen
          </a>
        </p>
      `
      : "";

    sourceCard.innerHTML = `
      <strong>
        ${escapeHtml(source.id)} –
        ${escapeHtml(source.shortName || source.title)}
      </strong>

      ${
        source.institution
          ? `<p>${escapeHtml(source.institution)}</p>`
          : ""
      }

      ${
        source.title
          ? `<p>${escapeHtml(source.title)}</p>`
          : ""
      }

      ${
        source.dataset
          ? `<p>Fundstelle: ${escapeHtml(source.dataset)}</p>`
          : ""
      }

      ${
        source.accessed
          ? `<p>Abrufdatum: ${escapeHtml(source.accessed)}</p>`
          : ""
      }

      ${sourceLink}

      <button
        type="button"
        class="danger small remove-source"
      >
        Quelle löschen
      </button>
    `;

    sourceCard
      .querySelector(".remove-source")
      .addEventListener("click", () => {
        removeSource(source.id);
      });

    elements.sourceList.appendChild(sourceCard);
  });
}


// ============================================================
// 7. Diagramm
// ============================================================

function resizeCanvas() {
  const rectangle =
    elements.chartCanvas.getBoundingClientRect();

  const devicePixelRatio =
    window.devicePixelRatio || 1;

  const displayWidth =
    Math.max(300, Math.floor(rectangle.width));

  const displayHeight =
    Math.max(300, Math.floor(rectangle.height));

  elements.chartCanvas.width =
    displayWidth * devicePixelRatio;

  elements.chartCanvas.height =
    displayHeight * devicePixelRatio;

  chartContext.setTransform(
    devicePixelRatio,
    0,
    0,
    devicePixelRatio,
    0,
    0
  );

  return {
    width: displayWidth,
    height: displayHeight
  };
}


function drawEmptyChart(width, height, message) {
  chartContext.clearRect(0, 0, width, height);

  chartContext.fillStyle = "#ffffff";
  chartContext.fillRect(0, 0, width, height);

  chartContext.fillStyle = "#666666";
  chartContext.font = "16px Arial";
  chartContext.textAlign = "center";
  chartContext.textBaseline = "middle";

  chartContext.fillText(
    message,
    width / 2,
    height / 2
  );
}


function drawChart() {
  const { width, height } = resizeCanvas();

  chartPoints = [];

  const measurements = getValidMeasurements();

  const lowerReference =
    parseNumber(
      state.dataset.normalization.lowerValue
    );

  const upperReference =
    parseNumber(
      state.dataset.normalization.upperValue
    );

  elements.chartTitle.textContent =
    state.dataset.title || "Diagramm";

  if (measurements.length === 0) {
    elements.chartSubtitle.textContent =
      "Noch keine Messwerte vorhanden.";

    drawEmptyChart(
      width,
      height,
      "Bitte Messwerte eingeben."
    );

    return;
  }

  if (
    lowerReference === null ||
    upperReference === null ||
    lowerReference === upperReference
  ) {
    elements.chartSubtitle.textContent =
      "Bitte gültige Bezugswerte eingeben.";

    drawEmptyChart(
      width,
      height,
      "Die Bezugswerte sind unvollständig."
    );

    return;
  }

  const chartData = measurements
    .map((measurement) => ({
      ...measurement,
      burden: calculateBurden(measurement.value)
    }))
    .filter((measurement) =>
      Number.isFinite(measurement.burden)
    );

  if (chartData.length === 0) {
    drawEmptyChart(
      width,
      height,
      "Keine darstellbaren Messwerte vorhanden."
    );

    return;
  }

  const unitText =
    state.dataset.unit
      ? `Originalwerte in ${state.dataset.unit}`
      : "Originalwerte";

  elements.chartSubtitle.textContent =
    `${unitText} · Belastung in Prozent`;

  const padding = {
    top: 55,
    right: 40,
    bottom: 70,
    left: 75
  };

  const chartWidth =
    width - padding.left - padding.right;

  const chartHeight =
    height - padding.top - padding.bottom;

  const years = chartData.map(
    (measurement) => measurement.year
  );

  let minimumYear = Math.min(...years);
  let maximumYear = Math.max(...years);

  if (minimumYear === maximumYear) {
    minimumYear -= 1;
    maximumYear += 1;
  }

  const burdenValues = chartData.map(
    (measurement) => measurement.burden
  );

  let minimumBurden = Math.min(
    0,
    ...burdenValues
  );

  let maximumBurden = Math.max(
    100,
    ...burdenValues
  );

  const burdenRange =
    maximumBurden - minimumBurden || 100;

  minimumBurden =
    Math.floor(minimumBurden / 10) * 10;

  maximumBurden =
    Math.ceil(maximumBurden / 10) * 10;

  const xPosition = (year) =>
    padding.left +
    ((year - minimumYear) /
      (maximumYear - minimumYear)) *
      chartWidth;

  const yPosition = (burden) =>
    padding.top +
    chartHeight -
    ((burden - minimumBurden) /
      (maximumBurden - minimumBurden)) *
      chartHeight;


  // Hintergrund
  chartContext.clearRect(0, 0, width, height);

  chartContext.fillStyle = "#ffffff";
  chartContext.fillRect(0, 0, width, height);


  // Raster und Y-Achse
  chartContext.font = "13px Arial";
  chartContext.textAlign = "right";
  chartContext.textBaseline = "middle";

  const yStep =
    maximumBurden - minimumBurden <= 100
      ? 10
      : 20;

  for (
    let burden = minimumBurden;
    burden <= maximumBurden;
    burden += yStep
  ) {
    const y = yPosition(burden);

    chartContext.beginPath();
    chartContext.strokeStyle =
      burden === 100
        ? "#b42318"
        : "#dddddd";

    chartContext.lineWidth =
      burden === 100
        ? 2
        : 1;

    chartContext.moveTo(padding.left, y);
    chartContext.lineTo(
      width - padding.right,
      y
    );

    chartContext.stroke();

    chartContext.fillStyle = "#444444";

    chartContext.fillText(
      `${formatNumber(burden, 0)} %`,
      padding.left - 10,
      y
    );
  }


  // X-Achse
  chartContext.beginPath();
  chartContext.strokeStyle = "#333333";
  chartContext.lineWidth = 1.5;

  chartContext.moveTo(
    padding.left,
    padding.top + chartHeight
  );

  chartContext.lineTo(
    width - padding.right,
    padding.top + chartHeight
  );

  chartContext.stroke();


  // Jahresbeschriftungen
  const maximumYearLabels =
    width < 700
      ? 5
      : 8;

  const yearSpan =
    maximumYear - minimumYear;

  const roughYearStep =
    yearSpan / maximumYearLabels;

  const possibleSteps = [
    1,
    2,
    5,
    10,
    20,
    25,
    50,
    100
  ];

  const yearStep =
    possibleSteps.find(
      (step) => step >= roughYearStep
    ) || Math.ceil(roughYearStep / 100) * 100;

  const firstYearLabel =
    Math.ceil(minimumYear / yearStep) *
    yearStep;

  chartContext.textAlign = "center";
  chartContext.textBaseline = "top";
  chartContext.fillStyle = "#444444";

  for (
    let year = firstYearLabel;
    year <= maximumYear;
    year += yearStep
  ) {
    const x = xPosition(year);

    chartContext.beginPath();
    chartContext.strokeStyle = "#eeeeee";
    chartContext.lineWidth = 1;

    chartContext.moveTo(x, padding.top);
    chartContext.lineTo(
      x,
      padding.top + chartHeight
    );

    chartContext.stroke();

    chartContext.fillText(
      String(Math.round(year)),
      x,
      padding.top + chartHeight + 12
    );
  }


  // Achsenbeschriftung
  chartContext.save();

  chartContext.translate(
    20,
    padding.top + chartHeight / 2
  );

  chartContext.rotate(-Math.PI / 2);

  chartContext.textAlign = "center";
  chartContext.textBaseline = "middle";
  chartContext.fillStyle = "#333333";
  chartContext.font = "bold 14px Arial";

  chartContext.fillText(
    "Belastung",
    0,
    0
  );

  chartContext.restore();


  // Verbindungslinie
  chartContext.beginPath();
  chartContext.strokeStyle = "#202020";
  chartContext.lineWidth = 3;
  chartContext.lineJoin = "round";
  chartContext.lineCap = "round";

  chartData.forEach((measurement, index) => {
    const x = xPosition(measurement.year);
    const y = yPosition(measurement.burden);

    if (index === 0) {
      chartContext.moveTo(x, y);
    } else {
      chartContext.lineTo(x, y);
    }
  });

  chartContext.stroke();


  // Messpunkte und Beschriftungen
  const averagePointDistance =
    chartData.length > 1
      ? chartWidth / (chartData.length - 1)
      : chartWidth;

  const showValueLabels =
    averagePointDistance >= 70 &&
    chartData.length <= 15;

  chartData.forEach((measurement) => {
    const x = xPosition(measurement.year);
    const y = yPosition(measurement.burden);

    chartContext.beginPath();
    chartContext.fillStyle = "#f2c500";
    chartContext.strokeStyle = "#202020";
    chartContext.lineWidth = 2;

    chartContext.arc(
      x,
      y,
      6,
      0,
      Math.PI * 2
    );

    chartContext.fill();
    chartContext.stroke();

    chartPoints.push({
      x,
      y,
      radius: 12,
      measurement
    });

    if (showValueLabels) {
      const valueLabel =
        `${formatNumber(measurement.value)}${state.dataset.unit ? ` ${state.dataset.unit}` : ""}`;

      chartContext.font = "12px Arial";
      chartContext.textAlign = "center";
      chartContext.textBaseline = "bottom";

      const textWidth =
        chartContext.measureText(valueLabel).width;

      chartContext.fillStyle =
        "rgba(255, 255, 255, 0.88)";

      chartContext.fillRect(
        x - textWidth / 2 - 4,
        y - 28,
        textWidth + 8,
        18
      );

      chartContext.fillStyle = "#202020";

      chartContext.fillText(
        valueLabel,
        x,
        y - 12
      );
    }
  });
}


// ============================================================
// 8. Diagramm-Tooltip
// ============================================================

function findChartPoint(mouseX, mouseY) {
  return chartPoints.find((point) => {
    const deltaX = mouseX - point.x;
    const deltaY = mouseY - point.y;

    const distance =
      Math.sqrt(
        deltaX * deltaX +
        deltaY * deltaY
      );

    return distance <= point.radius;
  });
}


function showTooltip(event, point) {
  const measurement = point.measurement;

  const sourceId =
    measurement.sourceIds?.[0] || "";

  const source =
    getSourceById(sourceId);

  const sourceText = source
    ? `${source.id} – ${source.shortName || source.title}`
    : "Keine Quelle zugeordnet";

  elements.chartTooltip.innerHTML = `
    <strong>${escapeHtml(measurement.year)}</strong><br>
    Originalwert:
    ${escapeHtml(formatNumber(measurement.value))}
    ${escapeHtml(state.dataset.unit)}<br>
    Belastung:
    ${escapeHtml(formatNumber(measurement.burden, 1))} %<br>
    Quelle:
    ${escapeHtml(sourceText)}
    ${
      measurement.note
        ? `<br>Anmerkung: ${escapeHtml(measurement.note)}`
        : ""
    }
  `;

  elements.chartTooltip.style.display = "block";

  const tooltipWidth =
    elements.chartTooltip.offsetWidth;

  const tooltipHeight =
    elements.chartTooltip.offsetHeight;

  let left = event.clientX + 14;
  let top = event.clientY + 14;

  if (
    left + tooltipWidth >
    window.innerWidth - 10
  ) {
    left =
      event.clientX -
      tooltipWidth -
      14;
  }

  if (
    top + tooltipHeight >
    window.innerHeight - 10
  ) {
    top =
      event.clientY -
      tooltipHeight -
      14;
  }

  elements.chartTooltip.style.left =
    `${left}px`;

  elements.chartTooltip.style.top =
    `${top}px`;
}


function hideTooltip() {
  elements.chartTooltip.style.display = "none";
}


function handleCanvasMouseMove(event) {
  const rectangle =
    elements.chartCanvas.getBoundingClientRect();

  const mouseX =
    event.clientX - rectangle.left;

  const mouseY =
    event.clientY - rectangle.top;

  const point =
    findChartPoint(mouseX, mouseY);

  if (point) {
    elements.chartCanvas.style.cursor = "pointer";
    showTooltip(event, point);
  } else {
    elements.chartCanvas.style.cursor = "default";
    hideTooltip();
  }
}


// ============================================================
// 9. JSON-Vorschau
// ============================================================

function updateJsonPreview() {
  const exportData = getExportData();

  elements.jsonPreview.textContent =
    JSON.stringify(exportData, null, 2);
}


// ============================================================
// 10. Browser-Speicherung
// ============================================================

function saveToBrowser() {
  try {
    const exportData = getExportData();

    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(exportData)
    );

    setStatus(
      "Die Messreihe wurde im Browser gespeichert."
    );
  } catch (error) {
    console.error(error);

    setStatus(
      "Die Daten konnten nicht gespeichert werden.",
      "error"
    );
  }
}


function loadFromBrowser() {
  try {
    const savedData =
      localStorage.getItem(STORAGE_KEY);

    if (!savedData) {
      setStatus(
        "Im Browser wurden noch keine Daten gespeichert.",
        "error"
      );

      return;
    }

    const parsedData =
      JSON.parse(savedData);

    loadDataObject(parsedData);

    setStatus(
      "Die gespeicherten Daten wurden geladen."
    );
  } catch (error) {
    console.error(error);

    setStatus(
      "Die gespeicherten Daten konnten nicht gelesen werden.",
      "error"
    );
  }
}


// ============================================================
// 11. JSON-Import und -Export
// ============================================================

function downloadTextFile(
  content,
  fileName,
  mimeType
) {
  const blob = new Blob(
    [content],
    { type: mimeType }
  );

  const url =
    URL.createObjectURL(blob);

  const link =
    document.createElement("a");

  link.href = url;
  link.download = fileName;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
}


function exportJson() {
  const exportData = getExportData();

  const baseName =
    exportData.dataset.id ||
    createIdFromTitle(exportData.dataset.title) ||
    "bruchlast-datensatz";

  downloadTextFile(
    JSON.stringify(exportData, null, 2),
    `${baseName}.json`,
    "application/json"
  );

  setStatus("JSON-Datei wurde erstellt.");
}


function loadDataObject(data) {
  if (!data || typeof data !== "object") {
    throw new Error(
      "Die Datei enthält keine gültigen Daten."
    );
  }

  const importedDataset =
    data.dataset || data;

  state.dataset = {
    id: importedDataset.id || "",
    title: importedDataset.title || "",
    shortTitle:
      importedDataset.shortTitle || "",
    planetaryBoundary:
      importedDataset.planetaryBoundary || "",
    description:
      importedDataset.description || "",
    unit: importedDataset.unit || "",
    burdenDirection:
      importedDataset.burdenDirection ||
      "increasing",

    normalization: {
      lowerValue:
        importedDataset.normalization
          ?.lowerValue ??
        importedDataset.lowerValue ??
        0,

      upperValue:
        importedDataset.normalization
          ?.upperValue ??
        importedDataset.upperValue ??
        100
    },

    values: Array.isArray(importedDataset.values)
      ? importedDataset.values.map(
          normalizeMeasurement
        )
      : []
  };

  state.sources = Array.isArray(data.sources)
    ? data.sources.map((source, index) => ({
        id:
          source.id ||
          `Q${String(index + 1).padStart(3, "0")}`,

        shortName:
          source.shortName || "",

        institution:
          source.institution || "",

        title:
          source.title || "",

        publicationYear:
          source.publicationYear || "",

        url:
          source.url || "",

        dataset:
          source.dataset ||
          source.location ||
          "",

        accessed:
          source.accessed || "",

        license:
          source.license || "",

        note:
          source.note || ""
      }))
    : [];

  state.review = {
    status:
      data.review?.status || "draft",

    createdBy:
      data.review?.createdBy || "",

    createdAt:
      data.review?.createdAt || "",

    reviewedBy:
      data.review?.reviewedBy || "",

    reviewedAt:
      data.review?.reviewedAt || "",

    version:
      data.review?.version || "0.1"
  };

  writeMetadataToForm();
  renderSources();
  renderMeasurements();
  drawChart();
  updateJsonPreview();
}


function importJsonFile(file) {
  if (!file) {
    return;
  }

  const reader = new FileReader();

  reader.addEventListener("load", () => {
    try {
      const parsedData =
        JSON.parse(reader.result);

      loadDataObject(parsedData);

      setStatus(
        "JSON-Datei wurde erfolgreich importiert."
      );
    } catch (error) {
      console.error(error);

      setStatus(
        "Die JSON-Datei ist ungültig oder nicht lesbar.",
        "error"
      );
    } finally {
      elements.importFile.value = "";
    }
  });

  reader.addEventListener("error", () => {
    setStatus(
      "Die Datei konnte nicht gelesen werden.",
      "error"
    );
  });

  reader.readAsText(file, "UTF-8");
}


// ============================================================
// 12. Beispieldatensatz
// ============================================================

function loadExampleData() {
  const confirmed =
    state.dataset.values.length === 0 ||
    window.confirm(
      "Die derzeit eingegebenen Daten werden durch den Beispieldatensatz ersetzt. Fortfahren?"
    );

  if (!confirmed) {
    return;
  }

  loadDataObject({
    format: "z-panel-dataset",
    schemaVersion: 1,

    dataset: {
      id: "co2-atmosphaere-mauna-loa",
      title:
        "Atmosphärische CO₂-Konzentration",
      shortTitle:
        "CO₂-Konzentration",
      planetaryBoundary:
        "Klimawandel",
      description:
        "Ausgewählte Jahresmittel der atmosphärischen CO₂-Konzentration am Mauna-Loa-Observatorium.",
      unit: "ppm",
      burdenDirection: "increasing",

      normalization: {
        lowerValue: 280,
        upperValue: 450
      },

      values: [
        {
          year: 1960,
          value: 316.91,
          sourceIds: ["Q001"],
          note: ""
        },
        {
          year: 1970,
          value: 325.68,
          sourceIds: ["Q001"],
          note: ""
        },
        {
          year: 1980,
          value: 338.76,
          sourceIds: ["Q001"],
          note: ""
        },
        {
          year: 1990,
          value: 354.45,
          sourceIds: ["Q001"],
          note: ""
        },
        {
          year: 2000,
          value: 369.71,
          sourceIds: ["Q001"],
          note: ""
        },
        {
          year: 2010,
          value: 390.1,
          sourceIds: ["Q001"],
          note: ""
        },
        {
          year: 2020,
          value: 414.24,
          sourceIds: ["Q001"],
          note: ""
        }
      ]
    },

    sources: [
      {
        id: "Q001",
        shortName: "NOAA CO₂",
        institution:
          "NOAA Global Monitoring Laboratory",
        title:
          "Trends in Atmospheric Carbon Dioxide",
        publicationYear: "",
        url:
          "https://gml.noaa.gov/ccgg/trends/",
        dataset:
          "Mauna Loa annual mean data",
        accessed: getToday(),
        license: "",
        note:
          "Beispieldatensatz für den Kurvengenerator."
      }
    ],

    review: {
      status: "draft",
      createdBy: "",
      createdAt: getToday(),
      reviewedBy: "",
      reviewedAt: "",
      version: "0.1"
    }
  });

  setStatus(
    "Der Beispieldatensatz wurde geladen."
  );
}


// ============================================================
// 13. Zurücksetzen
// ============================================================

function resetAllData() {
  const confirmed = window.confirm(
    "Sollen alle derzeit eingegebenen Daten gelöscht werden?"
  );

  if (!confirmed) {
    return;
  }

  state.dataset = {
    id: "",
    title: "",
    shortTitle: "",
    planetaryBoundary: "",
    description: "",
    unit: "",
    burdenDirection: "increasing",

    normalization: {
      lowerValue: 0,
      upperValue: 100
    },

    values: []
  };

  state.sources = [];

  state.review = {
    status: "draft",
    createdBy: "",
    createdAt: getToday(),
    reviewedBy: "",
    reviewedAt: "",
    version: "0.1"
  };

  localStorage.removeItem(STORAGE_KEY);

  writeMetadataToForm();
  clearSourceForm();
  renderSources();
  renderMeasurements();
  drawChart();
  updateJsonPreview();

  setStatus(
    "Alle Daten wurden zurückgesetzt."
  );
}


// ============================================================
// 14. PNG-Export
// ============================================================

function downloadChartAsPng() {
  drawChart();

  const baseName =
    state.dataset.id ||
    createIdFromTitle(state.dataset.title) ||
    "bruchlast-diagramm";

  const link =
    document.createElement("a");

  link.download = `${baseName}.png`;

  link.href =
    elements.chartCanvas.toDataURL(
      "image/png"
    );

  document.body.appendChild(link);
  link.click();
  link.remove();

  setStatus(
    "Das Diagramm wurde als PNG erstellt."
  );
}


// ============================================================
// 15. Oberfläche aktualisieren
// ============================================================

function updateInterface() {
  renderMeasurements();
  drawChart();
  updateJsonPreview();
}


// ============================================================
// 16. Ereignisse
// ============================================================

function registerEventListeners() {
  const metadataInputs = [
    elements.datasetTitle,
    elements.datasetShortTitle,
    elements.datasetDescription,
    elements.planetaryBoundary,
    elements.datasetUnit,
    elements.burdenDirection,
    elements.lowerReference,
    elements.upperReference
  ];

  metadataInputs.forEach((input) => {
    input.addEventListener(
      input.tagName === "SELECT"
        ? "change"
        : "input",
      readMetadataFromForm
    );
  });

  elements.addValueButton.addEventListener(
    "click",
    () => addMeasurement()
  );

  elements.addSourceButton.addEventListener(
    "click",
    addSource
  );

  elements.saveButton.addEventListener(
    "click",
    saveToBrowser
  );

  elements.loadButton.addEventListener(
    "click",
    loadFromBrowser
  );

  elements.exportButton.addEventListener(
    "click",
    exportJson
  );

  elements.importFile.addEventListener(
    "change",
    (event) => {
      importJsonFile(
        event.target.files?.[0]
      );
    }
  );

  elements.exampleButton.addEventListener(
    "click",
    loadExampleData
  );

  elements.resetButton.addEventListener(
    "click",
    resetAllData
  );

  elements.downloadChartButton.addEventListener(
    "click",
    downloadChartAsPng
  );

  elements.chartCanvas.addEventListener(
    "mousemove",
    handleCanvasMouseMove
  );

  elements.chartCanvas.addEventListener(
    "mouseleave",
    hideTooltip
  );

  window.addEventListener(
    "resize",
    drawChart
  );
}


// ============================================================
// 17. Start
// ============================================================

function initializeGenerator() {
  state.review.createdAt = getToday();

  writeMetadataToForm();
  clearSourceForm();
  renderSources();
  renderMeasurements();
  registerEventListeners();
  drawChart();
  updateJsonPreview();
}


initializeGenerator();
