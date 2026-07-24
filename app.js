"use strict";

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
  boundary: "",
  search: ""
};

const grid = document.getElementById("news-grid");
const statusMessage = document.getElementById("status-message");
const filterBox = document.getElementById("boundary-filters");
const searchInput = document.getElementById("search-input");
const clearFilter = document.getElementById("clear-filter");
const dialog = document.getElementById("article-dialog");
const dialogBody = document.getElementById("dialog-body");

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
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit", month: "long", year: "numeric"
  }).format(date);
}

function renderFilters() {
  const counts = {};
  state.articles.forEach(article => {
    counts[article.planetaryBoundary] = (counts[article.planetaryBoundary] || 0) + 1;
  });

  filterBox.innerHTML = Object.entries(boundaryNames).map(([code, label]) => `
    <button class="boundary-button ${state.boundary === code ? "active" : ""}"
      type="button" data-boundary="${code}">
      <strong>${escapeHtml(label)}</strong>
      <span>${counts[code] || 0} Beitrag/Beiträge · ${code}</span>
    </button>
  `).join("");

  filterBox.querySelectorAll("[data-boundary]").forEach(button => {
    button.addEventListener("click", () => {
      state.boundary = button.dataset.boundary;
      renderFilters();
      renderArticles();
      document.getElementById("meldungen").scrollIntoView({ behavior: "smooth" });
    });
  });
}

function matchingArticles() {
  const query = state.search.toLocaleLowerCase("de");
  return state.articles.filter(article => {
    const boundaryOk = !state.boundary || article.planetaryBoundary === state.boundary;
    const haystack = [
      article.title, article.subtitle, article.summary,
      ...(article.keywords || []), boundaryNames[article.planetaryBoundary]
    ].join(" ").toLocaleLowerCase("de");
    return boundaryOk && (!query || haystack.includes(query));
  });
}

function articleImage(article, className = "news-card-image") {
  if (!article.imageFile) {
    return `<div class="image-placeholder">Bild folgt<br>${escapeHtml(article.imageId || "")}</div>`;
  }
  const alt = article.imageMetadata?.altText || article.title;
  return `<img class="${className}" src="${encodeURI(article.imageFile)}"
    alt="${escapeHtml(alt)}" loading="lazy">`;
}

function renderArticles() {
  const articles = matchingArticles();
  statusMessage.hidden = articles.length > 0;
  if (!articles.length) {
    statusMessage.textContent = "Zu dieser Auswahl wurden keine Meldungen gefunden.";
    grid.innerHTML = "";
    return;
  }

  grid.innerHTML = articles.map(article => `
    <article class="news-card">
      ${articleImage(article)}
      <div class="news-card-body">
        <div class="meta">${escapeHtml(boundaryNames[article.planetaryBoundary] || article.planetaryBoundary)}
          · ${escapeHtml(formatDate(article.publicationDate))}</div>
        <h3>${escapeHtml(article.title)}</h3>
        <p>${escapeHtml(article.summary)}</p>
        <button class="card-button" type="button" data-id="${escapeHtml(article.id)}">
          Artikel lesen
        </button>
      </div>
    </article>
  `).join("");

  grid.querySelectorAll("[data-id]").forEach(button => {
    button.addEventListener("click", () => openArticle(button.dataset.id));
  });
}

function splitText(text) {
  const parts = String(text || "").split(/\n{2,}/).map(part => part.trim()).filter(Boolean);
  return parts.map((part, index) => {
    const looksLikeHeading =
      part.length < 90 &&
      !/[.!?]$/.test(part) &&
      index > 0;
    return looksLikeHeading
      ? `<h3>${escapeHtml(part)}</h3>`
      : `<p>${escapeHtml(part).replace(/\n/g, "<br>")}</p>`;
  }).join("");
}

function openArticle(id) {
  const article = state.articles.find(item => item.id === id);
  if (!article) return;

  const sections = (article.article || []).map(section => {
    const heading = section.heading ? `<h3>${escapeHtml(section.heading)}</h3>` : "";
    return `${heading}${splitText(section.text)}`;
  }).join("");

  dialogBody.innerHTML = `
    <div class="meta">${escapeHtml(boundaryNames[article.planetaryBoundary] || article.planetaryBoundary)}
      · ${escapeHtml(formatDate(article.publicationDate))}</div>
    <h2>${escapeHtml(article.title)}</h2>
    ${article.subtitle ? `<p class="intro">${escapeHtml(article.subtitle)}</p>` : ""}
    ${articleImage(article, "dialog-hero")}
    <div class="article-text">${sections}</div>
    <div class="source-box">
      <strong>Quelle</strong><br>
      ${escapeHtml(article.sourceTitle || article.sourceId || "")}<br>
      ${article.sourceUrl ? `<a href="${escapeHtml(article.sourceUrl)}" target="_blank" rel="noopener noreferrer">Originalquelle öffnen →</a>` : ""}
    </div>
  `;
  dialog.showModal();
}

async function loadNews() {
  try {
    const response = await fetch("news.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    state.articles = Array.isArray(data.articles) ? data.articles : [];
    document.getElementById("article-count").textContent = data.articleCount ?? state.articles.length;

    const generated = data.generatedAt ? new Date(data.generatedAt) : null;
    document.getElementById("generated-at").textContent = generated
      ? `Datenstand: ${new Intl.DateTimeFormat("de-DE", {
          day: "2-digit", month: "2-digit", year: "numeric",
          hour: "2-digit", minute: "2-digit"
        }).format(generated)} Uhr`
      : "Datenstand nicht angegeben";

    renderFilters();
    renderArticles();
  } catch (error) {
    console.error(error);
    statusMessage.hidden = false;
    statusMessage.innerHTML =
      "<strong>Die Meldungen konnten nicht geladen werden.</strong><br>" +
      "Bitte prüfen, ob die Datei <code>news.json</code> im selben Ordner wie die Startseite liegt.";
    document.getElementById("article-count").textContent = "0";
    document.getElementById("generated-at").textContent = "news.json nicht erreichbar";
  }
}

searchInput.addEventListener("input", event => {
  state.search = event.target.value.trim();
  renderArticles();
});

clearFilter.addEventListener("click", () => {
  state.boundary = "";
  state.search = "";
  searchInput.value = "";
  renderFilters();
  renderArticles();
});

document.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", event => {
  if (event.target === dialog) dialog.close();
});

loadNews();
