"use strict";

const ROTATION_SECONDS = 30;

const boundaryNames = {
  KL: "Klimawandel",
  BD: "Integrität der Biosphäre",
  LN: "Landnutzungswandel",
  FW: "Süßwasser",
  NP: "Stickstoff und Phosphor",
  OA: "Ozeanversauerung",
  OZ: "Stratosphärisches Ozon",
  AE: "Atmosphärische Aerosole",
  NS: "Neue Substanzen"
};

const state = {
  articles: [],
  currentIndex: 0,
  paused: false,
  remainingMs: ROTATION_SECONDS * 1000,
  lastTick: performance.now(),
  animationFrame: null
};

const stage = document.getElementById("stage");
const image = document.getElementById("article-image");
const imageStatus = document.getElementById("image-status");
const boundaryBadge = document.getElementById("boundary-badge");
const articleMeta = document.getElementById("article-meta");
const articleTitle = document.getElementById("article-title");
const articleSummary = document.getElementById("article-summary");
const articleCounter = document.getElementById("article-counter");
const countdownLabel = document.getElementById("countdown-label");
const progressBar = document.getElementById("progress-bar");
const pauseButton = document.getElementById("pause-button");
const pauseIcon = document.getElementById("pause-icon");
const pauseLabel = document.getElementById("pause-label");
const nextButton = document.getElementById("next-button");
const readMoreButton = document.getElementById("read-more-button");
const fullscreenButton = document.getElementById("fullscreen-button");
const dialog = document.getElementById("article-dialog");
const dialogContent = document.getElementById("dialog-content");
const dialogClose = document.getElementById("dialog-close");

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit",
    month: "long",
    year: "numeric"
  }).format(date);
}

function currentArticle() {
  return state.articles[state.currentIndex] || null;
}

function candidateImagePaths(article) {
  const candidates = [];

  if (article.imageFile) candidates.push(article.imageFile);
  if (article.imageUrl) candidates.push(article.imageUrl);

  if (article.imageId) {
    const id = article.imageId;
    candidates.push(
      `assets/images/${id}.webp`,
      `assets/images/${id}.jpg`,
      `assets/images/${id}.jpeg`,
      `assets/images/${id}.png`
    );
  }

  return [...new Set(candidates.filter(Boolean))];
}

function loadFirstWorkingImage(article) {
  const paths = candidateImagePaths(article);
  const alt = article.imageMetadata?.altText || article.title || "";

  image.hidden = true;
  image.removeAttribute("src");
  image.alt = alt;
  imageStatus.hidden = false;

  if (!paths.length) {
    imageStatus.textContent =
      "Für diesen Beitrag ist noch kein Bildpfad hinterlegt.";
    return;
  }

  let index = 0;

  const tryNext = () => {
    if (index >= paths.length) {
      image.hidden = true;
      imageStatus.hidden = false;
      imageStatus.innerHTML =
        `Bild nicht gefunden.<br><small>Erwartet wurde zum Beispiel: assets/images/${escapeHtml(article.imageId || "BILD-ID")}.jpg</small>`;
      return;
    }

    const path = paths[index++];
    const tester = new Image();

    tester.onload = () => {
      image.src = path;
      image.alt = alt;
      image.hidden = false;
      imageStatus.hidden = true;
    };

    tester.onerror = tryNext;
    tester.src = path;
  };

  tryNext();
}

function renderArticle({ animate = true } = {}) {
  const article = currentArticle();
  if (!article) return;

  const update = () => {
    const boundary =
      boundaryNames[article.planetaryBoundary] ||
      article.planetaryBoundary ||
      "ZUSTAND";

    boundaryBadge.textContent = boundary;
    articleMeta.textContent = [boundary, formatDate(article.publicationDate)]
      .filter(Boolean)
      .join(" · ");
    articleTitle.textContent = article.title || "Ohne Titel";
    articleSummary.textContent =
      article.summary || article.subtitle || "Keine Kurzbeschreibung vorhanden.";
    articleCounter.textContent =
      `${state.currentIndex + 1} / ${state.articles.length}`;

    loadFirstWorkingImage(article);

    state.remainingMs = ROTATION_SECONDS * 1000;
    state.lastTick = performance.now();
    updateTimerDisplay();
    stage.classList.remove("is-changing");
  };

  if (!animate) {
    update();
    return;
  }

  stage.classList.add("is-changing");
  window.setTimeout(update, 230);
}

function updateTimerDisplay() {
  const total = ROTATION_SECONDS * 1000;
  const remaining = Math.max(0, state.remainingMs);
  const seconds = Math.ceil(remaining / 1000);
  const min = String(Math.floor(seconds / 60)).padStart(2, "0");
  const sec = String(seconds % 60).padStart(2, "0");

  countdownLabel.textContent = state.paused
    ? `Pausiert bei ${min}:${sec}`
    : `Automatischer Wechsel in ${min}:${sec}`;

  progressBar.style.transform = `scaleX(${remaining / total})`;
}

function nextArticle() {
  if (!state.articles.length) return;
  state.currentIndex = (state.currentIndex + 1) % state.articles.length;
  renderArticle();
}

function previousArticle() {
  if (!state.articles.length) return;
  state.currentIndex =
    (state.currentIndex - 1 + state.articles.length) % state.articles.length;
  renderArticle();
}

function togglePause(forceState = null) {
  state.paused = forceState === null ? !state.paused : forceState;
  pauseButton.setAttribute("aria-pressed", String(state.paused));
  pauseIcon.textContent = state.paused ? "▶" : "⏸";
  pauseLabel.textContent = state.paused ? "Weiter" : "Pause";
  state.lastTick = performance.now();
  updateTimerDisplay();
}

function tick(now) {
  const elapsed = now - state.lastTick;
  state.lastTick = now;

  if (!state.paused && state.articles.length > 1 && !dialog.open) {
    state.remainingMs -= elapsed;
    if (state.remainingMs <= 0) nextArticle();
  }

  updateTimerDisplay();
  state.animationFrame = requestAnimationFrame(tick);
}

function splitText(text) {
  const parts = String(text || "")
    .split(/\n{2,}/)
    .map(part => part.trim())
    .filter(Boolean);

  return parts.map((part, index) => {
    const headingLike =
      index > 0 &&
      part.length < 95 &&
      !/[.!?]$/.test(part);

    return headingLike
      ? `<h3>${escapeHtml(part)}</h3>`
      : `<p>${escapeHtml(part).replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

function openArticle() {
  const article = currentArticle();
  if (!article) return;

  const boundary =
    boundaryNames[article.planetaryBoundary] ||
    article.planetaryBoundary ||
    "ZUSTAND";

  const sections = (article.article || []).map(section => {
    const heading = section.heading
      ? `<h3>${escapeHtml(section.heading)}</h3>`
      : "";
    return `${heading}${splitText(section.text)}`;
  }).join("");

  const paths = candidateImagePaths(article);
  const imageMarkup = paths.length
    ? `<img class="dialog-image" src="${escapeHtml(paths[0])}"
         alt="${escapeHtml(article.imageMetadata?.altText || article.title || "")}"
         onerror="this.style.display='none'">`
    : "";

  dialogContent.innerHTML = `
    <div class="dialog-meta">
      ${escapeHtml(boundary)} · ${escapeHtml(formatDate(article.publicationDate))}
    </div>
    <h2 class="dialog-title">${escapeHtml(article.title)}</h2>
    ${article.subtitle
      ? `<p class="dialog-subtitle">${escapeHtml(article.subtitle)}</p>`
      : ""}
    ${imageMarkup}
    <div class="article-text">
      ${sections || `<p>${escapeHtml(article.summary || "")}</p>`}
    </div>
    <div class="source-box">
      <strong>Quelle</strong><br>
      ${escapeHtml(article.sourceTitle || article.sourceId || "Keine Quellenangabe")}<br>
      ${article.sourceUrl
        ? `<a href="${escapeHtml(article.sourceUrl)}" target="_blank" rel="noopener noreferrer">Originalquelle öffnen →</a>`
        : ""}
    </div>
  `;

  dialog.showModal();
}

async function toggleFullscreen() {
  try {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    } else {
      await document.exitFullscreen();
    }
  } catch (error) {
    console.error("Vollbild konnte nicht aktiviert werden:", error);
  }
}

async function loadNews() {
  try {
    const response = await fetch("news.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    state.articles = Array.isArray(data.articles) ? data.articles : [];

    if (!state.articles.length) {
      articleMeta.textContent = "Keine veröffentlichten Meldungen";
      articleTitle.textContent = "Noch keine Artikel vorhanden";
      articleSummary.textContent =
        "Sobald news.json Beiträge enthält, erscheinen sie automatisch hier.";
      articleCounter.textContent = "0 / 0";
      imageStatus.textContent = "Keine Meldungen";
      [pauseButton, nextButton, readMoreButton].forEach(button => button.disabled = true);
      return;
    }

    renderArticle({ animate: false });
    state.animationFrame = requestAnimationFrame(tick);
  } catch (error) {
    console.error(error);
    articleMeta.textContent = "Fehler beim Laden";
    articleTitle.textContent = "news.json konnte nicht gelesen werden";
    articleSummary.textContent =
      "Bitte prüfen, ob news.json im selben Ordner wie index.html liegt.";
    articleCounter.textContent = "0 / 0";
    imageStatus.textContent = "Keine Daten";
    [pauseButton, nextButton, readMoreButton].forEach(button => button.disabled = true);
  }
}

pauseButton.addEventListener("click", () => togglePause());
nextButton.addEventListener("click", nextArticle);
readMoreButton.addEventListener("click", openArticle);
fullscreenButton.addEventListener("click", toggleFullscreen);
dialogClose.addEventListener("click", () => dialog.close());

dialog.addEventListener("click", event => {
  if (event.target === dialog) dialog.close();
});

document.addEventListener("keydown", event => {
  if (dialog.open) {
    if (event.key === "Escape") dialog.close();
    return;
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();
    nextArticle();
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    previousArticle();
  } else if (event.code === "Space") {
    event.preventDefault();
    togglePause();
  } else if (event.key.toLowerCase() === "f") {
    toggleFullscreen();
  }
});

document.addEventListener("visibilitychange", () => {
  state.lastTick = performance.now();
});

loadNews();
