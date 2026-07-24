"use strict";

const ROTATION_SECONDS = 30;
const TRANSITION_MS = 360;

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
  animationFrame: null,
  transitionToken: 0,
  transitioning: false
};

const imageCache = new Map();

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

function articleCacheKey(article) {
  return String(article?.id || article?.imageId || article?.title || "");
}

function testImagePath(path) {
  return new Promise((resolve) => {
    const tester = new Image();
    tester.decoding = "async";
    tester.onload = async () => {
      try {
        if (typeof tester.decode === "function") {
          await tester.decode();
        }
      } catch {
        // Das Bild ist bereits geladen; ein Decode-Fehler blockiert nicht.
      }
      resolve(path);
    };
    tester.onerror = () => resolve(null);
    tester.src = path;
  });
}

async function resolveArticleImage(article) {
  const key = articleCacheKey(article);

  if (imageCache.has(key)) {
    return imageCache.get(key);
  }

  const promise = (async () => {
    for (const path of candidateImagePaths(article)) {
      const workingPath = await testImagePath(path);
      if (workingPath) return workingPath;
    }
    return null;
  })();

  imageCache.set(key, promise);
  return promise;
}

function preloadArticle(article) {
  if (!article) return;
  void resolveArticleImage(article);
}

function preloadNeighbours() {
  const length = state.articles.length;
  if (length < 2) return;

  preloadArticle(state.articles[(state.currentIndex + 1) % length]);
  preloadArticle(state.articles[(state.currentIndex + 2) % length]);
  preloadArticle(state.articles[(state.currentIndex - 1 + length) % length]);
}

async function showArticleImage(article, token) {
  const alt = article.imageMetadata?.altText || article.title || "";
  const resolvedPath = await resolveArticleImage(article);

  if (token !== state.transitionToken) return;

  image.alt = alt;

  if (!resolvedPath) {
    image.hidden = true;
    image.removeAttribute("src");
    imageStatus.hidden = false;
    imageStatus.textContent = article.imageId
      ? `Bild nicht gefunden. Erwartet wurde zum Beispiel: assets/images/${article.imageId}.jpg`
      : "Für diesen Beitrag ist noch kein Bildpfad hinterlegt.";
    return;
  }

  if (image.src !== new URL(resolvedPath, document.baseURI).href) {
    image.src = resolvedPath;
  }

  image.hidden = false;
  imageStatus.hidden = true;
}

function updateArticleText(article) {
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
}

async function renderArticle({ animate = true } = {}) {
  const article = currentArticle();
  if (!article || state.transitioning) return;

  state.transitioning = true;
  const token = ++state.transitionToken;

  try {
    // Das Bild wird vor dem sichtbaren Wechsel geladen und dekodiert.
    const imagePromise = resolveArticleImage(article);

    if (animate) {
      stage.classList.add("is-changing");
      await new Promise((resolve) =>
        window.setTimeout(resolve, TRANSITION_MS / 2)
      );
    }

    if (token !== state.transitionToken) return;

    updateArticleText(article);
    await imagePromise;
    await showArticleImage(article, token);

    if (token !== state.transitionToken) return;

    state.remainingMs = ROTATION_SECONDS * 1000;
    state.lastTick = performance.now();
    updateTimerDisplay();

    requestAnimationFrame(() => {
      if (token === state.transitionToken) {
        stage.classList.remove("is-changing");
      }
    });

    preloadNeighbours();
  } finally {
    state.transitioning = false;
  }
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
  if (!state.articles.length || state.transitioning) return;
  state.currentIndex = (state.currentIndex + 1) % state.articles.length;
  void renderArticle();
}

function previousArticle() {
  if (!state.articles.length || state.transitioning) return;
  state.currentIndex =
    (state.currentIndex - 1 + state.articles.length) % state.articles.length;
  void renderArticle();
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

    if (state.remainingMs <= 0 && !state.transitioning) {
      // Sofort zurücksetzen: Sonst würde requestAnimationFrame während des
      // asynchronen Bildwechsels in jedem Frame erneut nextArticle() starten.
      state.remainingMs = ROTATION_SECONDS * 1000;
      nextArticle();
    }
  }

  updateTimerDisplay();
  state.animationFrame = requestAnimationFrame(tick);
}

function splitText(text) {
  const parts = String(text || "")
    .split(/\n{2,}/)
    .map((part) => part.trim())
    .filter(Boolean);

  return parts
    .map((part, index) => {
      const headingLike =
        index > 0 && part.length < 95 && !/[.!?]$/.test(part);

      return headingLike
        ? `<h3>${escapeHtml(part)}</h3>`
        : `<p>${escapeHtml(part).replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}

function openArticle() {
  const article = currentArticle();
  if (!article) return;

  const boundary =
    boundaryNames[article.planetaryBoundary] ||
    article.planetaryBoundary ||
    "ZUSTAND";

  const sections = (article.article || [])
    .map((section) => {
      const heading = section.heading
        ? `<h3>${escapeHtml(section.heading)}</h3>`
        : "";
      return `${heading}${splitText(section.text)}`;
    })
    .join("");

  const sourceName =
    article.sourceTitle ||
    article.sourceId ||
    (() => {
      try {
        return article.sourceUrl
          ? new URL(article.sourceUrl).hostname.replace(/^www\./, "")
          : "Keine Quellenangabe";
      } catch {
        return "Originalquelle";
      }
    })();

  const sourceMarkup = article.sourceUrl
    ? `<a href="${escapeHtml(article.sourceUrl)}" target="_blank" rel="noopener noreferrer">Originalquelle öffnen →</a>`
    : "";

  const resolvedImage = image.hidden ? "" : image.getAttribute("src");
  const imageMarkup = resolvedImage
    ? `<img class="dialog-image" src="${escapeHtml(resolvedImage)}" alt="${escapeHtml(image.alt)}">`
    : "";

  dialogContent.innerHTML = `
    <div class="dialog-meta">${escapeHtml(boundary)} · ${escapeHtml(formatDate(article.publicationDate))}</div>
    <h2 class="dialog-title">${escapeHtml(article.title)}</h2>
    ${article.subtitle ? `<div class="dialog-subtitle">${escapeHtml(article.subtitle)}</div>` : ""}
    ${imageMarkup}
    <div class="article-text">
      ${sections || `<p>${escapeHtml(article.summary || "")}</p>`}
    </div>
    <div class="source-box">
      <strong>Quelle</strong><br>
      ${escapeHtml(sourceName)}<br>
      ${sourceMarkup}
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
    const response = await fetch(`news.json?v=${Date.now()}`, {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    state.articles = Array.isArray(data.articles) ? data.articles : [];

    if (!state.articles.length) {
      articleMeta.textContent = "Keine veröffentlichten Meldungen";
      articleTitle.textContent = "Noch keine Artikel vorhanden";
      articleSummary.textContent =
        "Sobald news.json Beiträge enthält, erscheinen sie automatisch hier.";
      articleCounter.textContent = "0 / 0";
      imageStatus.textContent = "Keine Meldungen";

      [pauseButton, nextButton, readMoreButton].forEach((button) => {
        button.disabled = true;
      });
      return;
    }

    // Vor dem ersten Rendern werden das erste und das nächste Bild vorbereitet.
    preloadArticle(state.articles[0]);
    preloadArticle(state.articles[1]);

    await renderArticle({ animate: false });
    state.animationFrame = requestAnimationFrame(tick);
  } catch (error) {
    console.error(error);
    articleMeta.textContent = "Fehler beim Laden";
    articleTitle.textContent = "news.json konnte nicht gelesen werden";
    articleSummary.textContent =
      "Bitte prüfen, ob news.json im selben Ordner wie index.html liegt.";
    articleCounter.textContent = "0 / 0";
    imageStatus.textContent = "Keine Daten";

    [pauseButton, nextButton, readMoreButton].forEach((button) => {
      button.disabled = true;
    });
  }
}

pauseButton.addEventListener("click", () => togglePause());
nextButton.addEventListener("click", nextArticle);
readMoreButton.addEventListener("click", openArticle);
fullscreenButton.addEventListener("click", toggleFullscreen);
dialogClose.addEventListener("click", () => dialog.close());

dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

document.addEventListener("keydown", (event) => {
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
    void toggleFullscreen();
  }
});

document.addEventListener("visibilitychange", () => {
  state.lastTick = performance.now();
});

void loadNews();
