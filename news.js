"use strict";

const elements = {
  card: document.getElementById("news-card"),
  visual: document.getElementById("news-visual"),
  image: document.getElementById("news-image"),
  category: document.getElementById("news-category"),
  date: document.getElementById("news-date"),
  title: document.getElementById("news-title"),
  summary: document.getElementById("news-summary"),
  highlight: document.getElementById("news-highlight"),
  sourceLink: document.getElementById("news-source-link"),
  sourceName: document.getElementById("news-source-name"),
  counter: document.getElementById("news-counter"),
  progressBar: document.getElementById("progress-bar"),
  pauseButton: document.getElementById("pause-button"),
  errorMessage: document.getElementById("error-message")
};

let items = [];
let currentIndex = 0;
let displaySeconds = 12;
let timerId = null;
let animation = null;
let paused = false;

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value + "T12:00:00");
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("de-DE").format(date);
}

function stopPlayback() {
  clearTimeout(timerId);
  timerId = null;
  if (animation) animation.cancel();
}

function scheduleNext() {
  stopPlayback();
  if (paused || items.length <= 1) return;

  animation = elements.progressBar.animate(
    [{ width: "0%" }, { width: "100%" }],
    { duration: displaySeconds * 1000, easing: "linear", fill: "forwards" }
  );

  timerId = setTimeout(() => {
    currentIndex = (currentIndex + 1) % items.length;
    render();
  }, displaySeconds * 1000);
}

function render() {
  const item = items[currentIndex];
  if (!item) return;

  elements.card.classList.remove("is-changing");
  void elements.card.offsetWidth;
  elements.card.classList.add("is-changing");

  if (item.imageUrl) {
    elements.visual.hidden = false;
    elements.card.classList.remove("no-image");
    elements.image.src = item.imageUrl;
    elements.image.alt = item.imageAlt || "";
  } else {
    elements.visual.hidden = true;
    elements.card.classList.add("no-image");
    elements.image.removeAttribute("src");
  }

  elements.category.textContent = item.category || "ZUSTAND";
  elements.date.textContent = formatDate(item.date);
  elements.title.textContent = item.title || "Ohne Überschrift";
  elements.summary.textContent = item.summary || "";

  if (item.highlight) {
    elements.highlight.textContent = item.highlight;
    elements.highlight.hidden = false;
  } else {
    elements.highlight.hidden = true;
  }

  elements.sourceName.textContent = item.sourceName || "Quelle nicht angegeben";

  if (item.sourceUrl) {
    elements.sourceLink.href = item.sourceUrl;
  } else {
    elements.sourceLink.removeAttribute("href");
  }

  elements.counter.textContent = `${currentIndex + 1} / ${items.length}`;
  scheduleNext();
}

async function start() {
  try {
    const response = await fetch("news.json", { cache: "no-store" });
    if (!response.ok) throw new Error("news.json konnte nicht geladen werden.");

    const data = await response.json();
    displaySeconds = Number(data.settings?.displaySeconds) || 12;
    items = (data.items || []).filter(item => item.active !== false);

    if (!items.length) throw new Error("Keine aktiven Meldungen vorhanden.");

    render();
  } catch (error) {
    console.error(error);
    elements.errorMessage.hidden = false;
    elements.errorMessage.textContent =
      "Das News-Panel konnte nicht gestartet werden. Bitte news.json prüfen.";
  }
}

elements.pauseButton.addEventListener("click", () => {
  paused = !paused;
  elements.pauseButton.textContent = paused ? "Weiter" : "Pause";
  paused ? stopPlayback() : scheduleNext();
});

start();
