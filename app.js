"use strict";

const pageParameters = new URLSearchParams(window.location.search);
const HOMEPAGE_MODE = pageParameters.get("mode") === "homepage";

if (HOMEPAGE_MODE) {
  document.documentElement.classList.add("homepage-mode");
  document.body.classList.add("homepage-mode");
}

const DEFAULT_ARTICLE_SECONDS = 30;
const DEFAULT_EDITORIAL_SECONDS = 18;
const DEFAULT_EDITORIAL_EVERY = 8;
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
  allArticles: [],
  articles: [],
  editorialScreens: [],
  topics: [],
  selectedTopic: "",
  topicSelectionOpen: true,
  items: [],
  currentIndex: 0,
  paused: false,
  remainingMs: DEFAULT_ARTICLE_SECONDS * 1000,
  lastTick: performance.now(),
  animationFrame: null,
  transitionToken: 0,
  transitioning: false,
  articleSeconds: DEFAULT_ARTICLE_SECONDS,
  editorialSeconds: DEFAULT_EDITORIAL_SECONDS,
  editorialEvery: DEFAULT_EDITORIAL_EVERY
};

const imageCache = new Map();
const stage = document.getElementById("stage");
const image = document.getElementById("article-image");
const imageStatus = document.getElementById("image-status");
const boundaryBadge = document.getElementById("boundary-badge");
const articleMeta = document.getElementById("article-meta");
const articleTitle = document.getElementById("article-title");
const articleSummary = document.getElementById("article-summary");
const articleSource = document.getElementById("article-source");
const articleConnection = document.getElementById("article-connection");
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
const topicButton = document.getElementById("topic-button");
const topicSelector = document.getElementById("topic-selector");
const topicOptions = document.getElementById("topic-options");

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

function isEditorial(item) {
  return item?.type === "editorial";
}

function currentItem() {
  return state.items[state.currentIndex] || null;
}

function itemDurationSeconds(item = currentItem()) {
  // Die Homepage-Vorschau wechselt bewusst schneller als der Infoscreen.
  // Das normale Z-PANEL behält weiterhin die Zeiten aus news.json.
  if (HOMEPAGE_MODE) {
    return isEditorial(item) ? 11 : 14;
  }

  const explicit = Number(item?.durationSeconds);
  if (Number.isFinite(explicit) && explicit >= 5) return explicit;
  return isEditorial(item) ? state.editorialSeconds : state.articleSeconds;
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
        if (typeof tester.decode === "function") await tester.decode();
      } catch {
        // Das Bild ist geladen; ein Decode-Fehler blockiert nicht.
      }
      resolve(path);
    };
    tester.onerror = () => resolve(null);
    tester.src = path;
  });
}

async function resolveArticleImage(article) {
  if (isEditorial(article)) return null;
  const key = articleCacheKey(article);
  if (imageCache.has(key)) return imageCache.get(key);
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

function preloadItem(item) {
  if (!item || isEditorial(item)) return;
  void resolveArticleImage(item);
}

function preloadNeighbours() {
  const length = state.items.length;
  if (length < 2) return;
  preloadItem(state.items[(state.currentIndex + 1) % length]);
  preloadItem(state.items[(state.currentIndex + 2) % length]);
  preloadItem(state.items[(state.currentIndex - 1 + length) % length]);
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

const sourceHostNames = {
  "pik-potsdam.de": "Potsdam-Institut für Klimafolgenforschung (PIK)",
  "umweltbundesamt.de": "Umweltbundesamt (UBA)",
  "climate.copernicus.eu": "Copernicus Climate Change Service",
  "marine.copernicus.eu": "Copernicus Marine Service",
  "awi.de": "Alfred-Wegener-Institut (AWI)",
  "geomar.de": "GEOMAR Helmholtz-Zentrum für Ozeanforschung Kiel",
  "bfn.de": "Bundesamt für Naturschutz (BfN)",
  "thuenen.de": "Thünen-Institut",
  "eea.europa.eu": "Europäische Umweltagentur (EEA)",
  "wmo.int": "Weltorganisation für Meteorologie (WMO)",
  "unep.org": "Umweltprogramm der Vereinten Nationen (UNEP)"
};

function sourceName(article) {
  if (article.sourceTitle) return article.sourceTitle;
  if (article.sourceId) return article.sourceId;
  try {
    if (!article.sourceUrl) return "";
    const host = new URL(article.sourceUrl).hostname.replace(/^www\./, "");
    const matchedDomain = Object.keys(sourceHostNames).find(
      (domain) => host === domain || host.endsWith(`.${domain}`)
    );
    return matchedDomain ? sourceHostNames[matchedDomain] : host;
  } catch {
    return "";
  }
}

function sourceLine(article) {
  const name = sourceName(article);
  const sourceType = String(article.sourceType || "").trim();
  if (!name && !sourceType) return "";
  return [sourceType, name].filter(Boolean).join(" · ");
}

function updateCounter(item) {
  if (isEditorial(item)) {
    articleCounter.textContent = item.label || "Redaktion";
    return;
  }
  const number = Number(item._articleNumber) || 1;
  articleCounter.textContent = `${number} / ${state.articles.length}`;
}

function updateArticleText(article) {
  /* Z-PANEL 5.1: Beitragstypen und Grundlagenrubrik */
  stage.classList.remove("is-editorial", "is-explainer", "is-solution");
  const contentType = String(article.contentType || "news").trim();
  stage.classList.toggle("is-explainer", contentType === "explainer");
  stage.classList.toggle("is-solution", contentType === "solution");
  const boundary = contentType === "explainer"
    ? (article.displayLabel || "NATUR VERSTEHEN")
    : (
        boundaryNames[article.planetaryBoundary] ||
        article.planetaryBoundary ||
        "ZUSTAND"
      );
  boundaryBadge.textContent = boundary;
  articleMeta.textContent = [boundary, formatDate(article.publicationDate)]
    .filter(Boolean)
    .join(" · ");
  articleTitle.textContent = article.title || "Ohne Titel";
  articleSummary.textContent =
    article.summary || article.subtitle || "Keine Kurzbeschreibung vorhanden.";

  const source = sourceLine(article);
  articleSource.textContent = source ? `Quelle: ${source}` : "";
  articleSource.hidden = !source;

  const connection = String(
    article.screenConnection || article.editorial?.screenConnection || ""
  ).trim();
  articleConnection.textContent = connection
    ? `Was zusammenhängt: ${connection}`
    : "";
  articleConnection.hidden = !connection;

  readMoreButton.hidden = false;
  readMoreButton.disabled = false;
  nextButton.textContent = "Nächster Artikel →";
  updateCounter(article);
}

function updateEditorialText(screen) {
  stage.classList.add("is-editorial");
  boundaryBadge.textContent = screen.label || "Redaktion";
  articleMeta.textContent = screen.kicker || "ZUSTAND · Redaktion";
  articleTitle.textContent = screen.title || "Wofür ZUSTAND steht";
  articleSummary.textContent = screen.text || screen.summary || "";
  articleSource.textContent = "";
  articleSource.hidden = true;
  articleConnection.textContent = "";
  articleConnection.hidden = true;
  readMoreButton.hidden = true;
  readMoreButton.disabled = true;
  nextButton.textContent = "Nächste Meldung →";
  updateCounter(screen);

  image.hidden = true;
  image.removeAttribute("src");
  imageStatus.hidden = false;
  imageStatus.textContent = screen.visualLabel || "ZUSTAND";
}

async function renderItem({ animate = true } = {}) {
  const item = currentItem();
  if (!item || state.transitioning) return;
  state.transitioning = true;
  const token = ++state.transitionToken;

  try {
    const imagePromise = isEditorial(item)
      ? Promise.resolve(null)
      : resolveArticleImage(item);

    if (animate) {
      stage.classList.add("is-changing");
      await new Promise((resolve) =>
        window.setTimeout(resolve, TRANSITION_MS / 2)
      );
    }
    if (token !== state.transitionToken) return;

    if (isEditorial(item)) {
      updateEditorialText(item);
    } else {
      updateArticleText(item);
      await imagePromise;
      await showArticleImage(item, token);
    }
    if (token !== state.transitionToken) return;

    state.remainingMs = itemDurationSeconds(item) * 1000;
    state.lastTick = performance.now();
    updateTimerDisplay();
    requestAnimationFrame(() => {
      if (token === state.transitionToken) stage.classList.remove("is-changing");
    });
    preloadNeighbours();
  } finally {
    state.transitioning = false;
  }
}

function updateTimerDisplay() {
  const total = Math.max(1, itemDurationSeconds() * 1000);
  const remaining = Math.max(0, state.remainingMs);
  const seconds = Math.ceil(remaining / 1000);
  const min = String(Math.floor(seconds / 60)).padStart(2, "0");
  const sec = String(seconds % 60).padStart(2, "0");
  countdownLabel.textContent = state.paused
    ? `Pausiert bei ${min}:${sec}`
    : `Automatischer Wechsel in ${min}:${sec}`;
  progressBar.style.transform = `scaleX(${Math.min(1, remaining / total)})`;
}

function nextItem() {
  if (!state.items.length || state.transitioning) return;
  state.currentIndex = (state.currentIndex + 1) % state.items.length;
  void renderItem();
}

function previousItem() {
  if (!state.items.length || state.transitioning) return;
  state.currentIndex =
    (state.currentIndex - 1 + state.items.length) % state.items.length;
  void renderItem();
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
  if (
    !state.paused
    && !state.topicSelectionOpen
    && state.items.length > 1
    && !dialog.open
  ) {
    state.remainingMs -= elapsed;
    if (state.remainingMs <= 0 && !state.transitioning) {
      state.remainingMs = itemDurationSeconds() * 1000;
      nextItem();
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
      const headingLike = index > 0 && part.length < 95 && !/[.!?]$/.test(part);
      return headingLike
        ? `<h3>${escapeHtml(part)}</h3>`
        : `<p>${escapeHtml(part).replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}

function openArticle() {
  const article = currentItem();
  if (!article || isEditorial(article)) return;
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
  const name = sourceName(article) || "Keine Quellenangabe";
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
      ${escapeHtml(name)}<br>
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

function normalizePositiveInteger(value, fallback, minimum = 1) {
  const number = Number(value);
  return Number.isFinite(number) && number >= minimum
    ? Math.round(number)
    : fallback;
}

function buildRotation(articles, editorialScreens, editorialEvery) {
  const news = articles.map((article, index) => ({
    ...article,
    type: article.type === "editorial" ? "article" : (article.type || "article"),
    _articleNumber: index + 1
  }));
  const screens = editorialScreens
    .filter((screen) => screen && screen.enabled !== false)
    .map((screen) => ({ ...screen, type: "editorial" }));

  if (!news.length) return screens;
  if (!screens.length) return news;

  const interval = Math.max(1, editorialEvery);
  const newsNeeded = interval * screens.length;
  const rounds = Math.max(1, Math.ceil(newsNeeded / news.length));
  const items = [];
  let screenIndex = 0;
  let newsSinceEditorial = 0;

  for (let round = 0; round < rounds; round += 1) {
    for (const article of news) {
      items.push({ ...article });
      newsSinceEditorial += 1;
      if (newsSinceEditorial >= interval && screenIndex < screens.length) {
        items.push(screens[screenIndex]);
        screenIndex += 1;
        newsSinceEditorial = 0;
      }
    }
  }

  while (screenIndex < screens.length) {
    for (const article of news) {
      items.push({ ...article });
      newsSinceEditorial += 1;
      if (newsSinceEditorial >= interval) break;
    }
    items.push(screens[screenIndex]);
    screenIndex += 1;
    newsSinceEditorial = 0;
  }

  return items;
}


function normalizeTopicLabel(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function topicCompareKey(value) {
  return normalizeTopicLabel(value).toLocaleLowerCase("de-DE");
}

function prepareTopicModel(articles) {
  const explainerTopics = new Map();

  for (const article of articles) {
    if (article?.contentType !== "explainer") continue;
    const identifier = String(article.id || "").trim();
    const label = normalizeTopicLabel(
      article.topic || article.selectionLabel || article.title
    );
    if (identifier && label) explainerTopics.set(identifier, label);
  }

  const topics = new Map();
  for (const article of articles) {
    let label = normalizeTopicLabel(article.topic);
    if (!label && article?.contentType === "explainer") {
      label = explainerTopics.get(String(article.id || "").trim())
        || normalizeTopicLabel(article.title);
    }
    if (!label) {
      label = explainerTopics.get(String(article.explainerId || "").trim()) || "";
    }

    article._topicLabel = label;
    if (!label) continue;

    const key = topicCompareKey(label);
    if (!topics.has(key)) {
      topics.set(key, { label, articleCount: 0, explainerCount: 0 });
    }
    const entry = topics.get(key);
    entry.articleCount += 1;
    if (article.contentType === "explainer") entry.explainerCount += 1;
  }

  return [...topics.values()];
}

function makeTopicOption(label, count, { all = false } = {}) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `topic-option${all ? " is-all" : ""}`;

  const labelElement = document.createElement("span");
  labelElement.className = "topic-option-label";
  labelElement.textContent = label;

  const countElement = document.createElement("span");
  countElement.className = "topic-option-count";
  countElement.textContent = String(count);
  countElement.setAttribute(
    "aria-label",
    `${count} ${count === 1 ? "Beitrag" : "Beiträge"}`
  );

  button.append(labelElement, countElement);
  return button;
}

function renderTopicOptions() {
  topicOptions.replaceChildren();

  const allButton = makeTopicOption(
    "Alle Themen",
    state.allArticles.length,
    { all: true }
  );
  allButton.addEventListener("click", () => selectTopic(""));
  topicOptions.appendChild(allButton);

  for (const topic of state.topics) {
    const button = makeTopicOption(topic.label, topic.articleCount);
    button.addEventListener("click", () => selectTopic(topic.label));
    topicOptions.appendChild(button);
  }
}

function showTopicSelector() {
  state.topicSelectionOpen = true;
  topicSelector.hidden = false;
  togglePause(true);
  window.setTimeout(() => {
    topicOptions.querySelector("button")?.focus();
  }, 0);
}

function hideTopicSelector({ resume = true } = {}) {
  state.topicSelectionOpen = false;
  topicSelector.hidden = true;
  if (resume) togglePause(false);
}

function filteredArticles(topicLabel) {
  const key = topicCompareKey(topicLabel);
  if (!key) return [...state.allArticles];
  return state.allArticles.filter(
    (article) => topicCompareKey(article._topicLabel) === key
  );
}

async function selectTopic(topicLabel) {
  const normalized = normalizeTopicLabel(topicLabel);
  const selectedArticles = filteredArticles(normalized);
  if (!selectedArticles.length && normalized) return;

  state.selectedTopic = normalized;
  state.articles = selectedArticles;
  state.currentIndex = 0;

  // Leitbild, Kodex und unzugeordnete Meldungen gehören zur Gesamtauswahl.
  const editorialScreens = normalized ? [] : state.editorialScreens;
  state.items = buildRotation(
    state.articles,
    editorialScreens,
    state.editorialEvery
  );

  if (!state.items.length) {
    showLoadError(
      "Für dieses Thema gibt es noch keine Beiträge",
      "Bitte wählen Sie ein anderes Thema oder erzeugen Sie news.json im Studio neu."
    );
    return;
  }

  topicButton.hidden = HOMEPAGE_MODE;
  topicButton.textContent = normalized ? `Thema: ${normalized}` : "Alle Themen";
  topicButton.title = normalized
    ? `Aktuelles Thema: ${normalized}. Klicken zum Wechseln.`
    : "Alle Themen. Klicken zum Wechseln.";

  hideTopicSelector({ resume: true });
  preloadItem(state.items[0]);
  preloadItem(state.items[1]);
  state.remainingMs = itemDurationSeconds(state.items[0]) * 1000;
  await renderItem({ animate: false });
}

function showLoadError(title, summary) {
  articleMeta.textContent = "Fehler beim Laden";
  articleTitle.textContent = title;
  articleSummary.textContent = summary;
  articleCounter.textContent = "0 / 0";
  imageStatus.textContent = "Keine Daten";
  articleSource.hidden = true;
  articleConnection.hidden = true;
  [pauseButton, nextButton, readMoreButton, topicButton].forEach((button) => {
    button.disabled = true;
  });
}

async function loadNews() {
  try {
    const response = await fetch(`news.json?v=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const rotation = data.rotation || {};
    state.articleSeconds = normalizePositiveInteger(
      rotation.articleSeconds,
      DEFAULT_ARTICLE_SECONDS,
      5
    );
    state.editorialSeconds = normalizePositiveInteger(
      rotation.editorialSeconds,
      DEFAULT_EDITORIAL_SECONDS,
      5
    );
    state.editorialEvery = normalizePositiveInteger(
      rotation.editorialEvery,
      DEFAULT_EDITORIAL_EVERY,
      1
    );
    state.allArticles = Array.isArray(data.articles) ? data.articles : [];
    state.editorialScreens = Array.isArray(data.editorialScreens)
      ? data.editorialScreens
      : [];
    state.topics = prepareTopicModel(state.allArticles);

    if (!state.allArticles.length && !state.editorialScreens.length) {
      showLoadError(
        "Noch keine Inhalte vorhanden",
        "Sobald news.json Beiträge oder redaktionelle Screens enthält, erscheinen sie automatisch hier."
      );
      return;
    }

    state.animationFrame = requestAnimationFrame(tick);

    if (HOMEPAGE_MODE) {
      await selectTopic("");
    } else if (state.topics.length) {
      renderTopicOptions();
      showTopicSelector();
    } else {
      await selectTopic("");
    }
  } catch (error) {
    console.error(error);
    showLoadError(
      "news.json konnte nicht gelesen werden",
      "Bitte prüfen, ob news.json im selben Ordner wie index.html liegt."
    );
  }
}

pauseButton.addEventListener("click", () => togglePause());
nextButton.addEventListener("click", nextItem);
readMoreButton.addEventListener("click", openArticle);
fullscreenButton.addEventListener("click", toggleFullscreen);
topicButton.addEventListener("click", showTopicSelector);
dialogClose.addEventListener("click", () => dialog.close());

dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

document.addEventListener("keydown", (event) => {
  if (state.topicSelectionOpen) {
    if (event.key === "Escape" && state.items.length) {
      event.preventDefault();
      hideTopicSelector({ resume: true });
    }
    return;
  }
  if (dialog.open) {
    if (event.key === "Escape") dialog.close();
    return;
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    nextItem();
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    previousItem();
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
