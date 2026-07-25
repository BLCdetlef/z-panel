#!/usr/bin/env python3
from __future__ import annotations

"""Installiert Z-PANEL 5.0 und News Studio 5.6.

Die Datei direkt in den Z-PANEL-Projektordner legen und starten.
Vor jeder Änderung wird eine Sicherung angelegt.
"""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_JS = '"use strict";\n\nconst DEFAULT_ARTICLE_SECONDS = 30;\nconst DEFAULT_EDITORIAL_SECONDS = 18;\nconst DEFAULT_EDITORIAL_EVERY = 8;\nconst TRANSITION_MS = 360;\n\nconst boundaryNames = {\n  KL: "Klimawandel",\n  BD: "Integrität der Biosphäre",\n  LN: "Landnutzungswandel",\n  FW: "Süßwasser",\n  NP: "Stickstoff und Phosphor",\n  OA: "Ozeanversauerung",\n  OZ: "Stratosphärisches Ozon",\n  AE: "Atmosphärische Aerosole",\n  NS: "Neue Substanzen"\n};\n\nconst state = {\n  articles: [],\n  editorialScreens: [],\n  items: [],\n  currentIndex: 0,\n  paused: false,\n  remainingMs: DEFAULT_ARTICLE_SECONDS * 1000,\n  lastTick: performance.now(),\n  animationFrame: null,\n  transitionToken: 0,\n  transitioning: false,\n  articleSeconds: DEFAULT_ARTICLE_SECONDS,\n  editorialSeconds: DEFAULT_EDITORIAL_SECONDS,\n  editorialEvery: DEFAULT_EDITORIAL_EVERY\n};\n\nconst imageCache = new Map();\nconst stage = document.getElementById("stage");\nconst image = document.getElementById("article-image");\nconst imageStatus = document.getElementById("image-status");\nconst boundaryBadge = document.getElementById("boundary-badge");\nconst articleMeta = document.getElementById("article-meta");\nconst articleTitle = document.getElementById("article-title");\nconst articleSummary = document.getElementById("article-summary");\nconst articleSource = document.getElementById("article-source");\nconst articleConnection = document.getElementById("article-connection");\nconst articleCounter = document.getElementById("article-counter");\nconst countdownLabel = document.getElementById("countdown-label");\nconst progressBar = document.getElementById("progress-bar");\nconst pauseButton = document.getElementById("pause-button");\nconst pauseIcon = document.getElementById("pause-icon");\nconst pauseLabel = document.getElementById("pause-label");\nconst nextButton = document.getElementById("next-button");\nconst readMoreButton = document.getElementById("read-more-button");\nconst fullscreenButton = document.getElementById("fullscreen-button");\nconst dialog = document.getElementById("article-dialog");\nconst dialogContent = document.getElementById("dialog-content");\nconst dialogClose = document.getElementById("dialog-close");\n\nfunction escapeHtml(value) {\n  return String(value ?? "")\n    .replace(/&/g, "&amp;")\n    .replace(/</g, "&lt;")\n    .replace(/>/g, "&gt;")\n    .replace(/"/g, "&quot;")\n    .replace(/\'/g, "&#039;");\n}\n\nfunction formatDate(value) {\n  if (!value) return "";\n  const date = new Date(`${value}T00:00:00`);\n  if (Number.isNaN(date.getTime())) return value;\n  return new Intl.DateTimeFormat("de-DE", {\n    day: "2-digit",\n    month: "long",\n    year: "numeric"\n  }).format(date);\n}\n\nfunction isEditorial(item) {\n  return item?.type === "editorial";\n}\n\nfunction currentItem() {\n  return state.items[state.currentIndex] || null;\n}\n\nfunction itemDurationSeconds(item = currentItem()) {\n  const explicit = Number(item?.durationSeconds);\n  if (Number.isFinite(explicit) && explicit >= 5) return explicit;\n  return isEditorial(item) ? state.editorialSeconds : state.articleSeconds;\n}\n\nfunction candidateImagePaths(article) {\n  const candidates = [];\n  if (article.imageFile) candidates.push(article.imageFile);\n  if (article.imageUrl) candidates.push(article.imageUrl);\n  if (article.imageId) {\n    const id = article.imageId;\n    candidates.push(\n      `assets/images/${id}.webp`,\n      `assets/images/${id}.jpg`,\n      `assets/images/${id}.jpeg`,\n      `assets/images/${id}.png`\n    );\n  }\n  return [...new Set(candidates.filter(Boolean))];\n}\n\nfunction articleCacheKey(article) {\n  return String(article?.id || article?.imageId || article?.title || "");\n}\n\nfunction testImagePath(path) {\n  return new Promise((resolve) => {\n    const tester = new Image();\n    tester.decoding = "async";\n    tester.onload = async () => {\n      try {\n        if (typeof tester.decode === "function") await tester.decode();\n      } catch {\n        // Das Bild ist geladen; ein Decode-Fehler blockiert nicht.\n      }\n      resolve(path);\n    };\n    tester.onerror = () => resolve(null);\n    tester.src = path;\n  });\n}\n\nasync function resolveArticleImage(article) {\n  if (isEditorial(article)) return null;\n  const key = articleCacheKey(article);\n  if (imageCache.has(key)) return imageCache.get(key);\n  const promise = (async () => {\n    for (const path of candidateImagePaths(article)) {\n      const workingPath = await testImagePath(path);\n      if (workingPath) return workingPath;\n    }\n    return null;\n  })();\n  imageCache.set(key, promise);\n  return promise;\n}\n\nfunction preloadItem(item) {\n  if (!item || isEditorial(item)) return;\n  void resolveArticleImage(item);\n}\n\nfunction preloadNeighbours() {\n  const length = state.items.length;\n  if (length < 2) return;\n  preloadItem(state.items[(state.currentIndex + 1) % length]);\n  preloadItem(state.items[(state.currentIndex + 2) % length]);\n  preloadItem(state.items[(state.currentIndex - 1 + length) % length]);\n}\n\nasync function showArticleImage(article, token) {\n  const alt = article.imageMetadata?.altText || article.title || "";\n  const resolvedPath = await resolveArticleImage(article);\n  if (token !== state.transitionToken) return;\n  image.alt = alt;\n  if (!resolvedPath) {\n    image.hidden = true;\n    image.removeAttribute("src");\n    imageStatus.hidden = false;\n    imageStatus.textContent = article.imageId\n      ? `Bild nicht gefunden. Erwartet wurde zum Beispiel: assets/images/${article.imageId}.jpg`\n      : "Für diesen Beitrag ist noch kein Bildpfad hinterlegt.";\n    return;\n  }\n  if (image.src !== new URL(resolvedPath, document.baseURI).href) {\n    image.src = resolvedPath;\n  }\n  image.hidden = false;\n  imageStatus.hidden = true;\n}\n\nconst sourceHostNames = {\n  "pik-potsdam.de": "Potsdam-Institut für Klimafolgenforschung (PIK)",\n  "umweltbundesamt.de": "Umweltbundesamt (UBA)",\n  "climate.copernicus.eu": "Copernicus Climate Change Service",\n  "marine.copernicus.eu": "Copernicus Marine Service",\n  "awi.de": "Alfred-Wegener-Institut (AWI)",\n  "geomar.de": "GEOMAR Helmholtz-Zentrum für Ozeanforschung Kiel",\n  "bfn.de": "Bundesamt für Naturschutz (BfN)",\n  "thuenen.de": "Thünen-Institut",\n  "eea.europa.eu": "Europäische Umweltagentur (EEA)",\n  "wmo.int": "Weltorganisation für Meteorologie (WMO)",\n  "unep.org": "Umweltprogramm der Vereinten Nationen (UNEP)"\n};\n\nfunction sourceName(article) {\n  if (article.sourceTitle) return article.sourceTitle;\n  if (article.sourceId) return article.sourceId;\n  try {\n    if (!article.sourceUrl) return "";\n    const host = new URL(article.sourceUrl).hostname.replace(/^www\\./, "");\n    const matchedDomain = Object.keys(sourceHostNames).find(\n      (domain) => host === domain || host.endsWith(`.${domain}`)\n    );\n    return matchedDomain ? sourceHostNames[matchedDomain] : host;\n  } catch {\n    return "";\n  }\n}\n\nfunction sourceLine(article) {\n  const name = sourceName(article);\n  const sourceType = String(article.sourceType || "").trim();\n  if (!name && !sourceType) return "";\n  return [sourceType, name].filter(Boolean).join(" · ");\n}\n\nfunction updateCounter(item) {\n  if (isEditorial(item)) {\n    articleCounter.textContent = item.label || "Redaktion";\n    return;\n  }\n  const number = Number(item._articleNumber) || 1;\n  articleCounter.textContent = `${number} / ${state.articles.length}`;\n}\n\nfunction updateArticleText(article) {\n  stage.classList.remove("is-editorial");\n  const boundary =\n    boundaryNames[article.planetaryBoundary] ||\n    article.planetaryBoundary ||\n    "ZUSTAND";\n  boundaryBadge.textContent = boundary;\n  articleMeta.textContent = [boundary, formatDate(article.publicationDate)]\n    .filter(Boolean)\n    .join(" · ");\n  articleTitle.textContent = article.title || "Ohne Titel";\n  articleSummary.textContent =\n    article.summary || article.subtitle || "Keine Kurzbeschreibung vorhanden.";\n\n  const source = sourceLine(article);\n  articleSource.textContent = source ? `Quelle: ${source}` : "";\n  articleSource.hidden = !source;\n\n  const connection = String(\n    article.screenConnection || article.editorial?.screenConnection || ""\n  ).trim();\n  articleConnection.textContent = connection\n    ? `Was zusammenhängt: ${connection}`\n    : "";\n  articleConnection.hidden = !connection;\n\n  readMoreButton.hidden = false;\n  readMoreButton.disabled = false;\n  nextButton.textContent = "Nächster Artikel →";\n  updateCounter(article);\n}\n\nfunction updateEditorialText(screen) {\n  stage.classList.add("is-editorial");\n  boundaryBadge.textContent = screen.label || "Redaktion";\n  articleMeta.textContent = screen.kicker || "ZUSTAND · Redaktion";\n  articleTitle.textContent = screen.title || "Wofür ZUSTAND steht";\n  articleSummary.textContent = screen.text || screen.summary || "";\n  articleSource.textContent = "";\n  articleSource.hidden = true;\n  articleConnection.textContent = "";\n  articleConnection.hidden = true;\n  readMoreButton.hidden = true;\n  readMoreButton.disabled = true;\n  nextButton.textContent = "Nächste Meldung →";\n  updateCounter(screen);\n\n  image.hidden = true;\n  image.removeAttribute("src");\n  imageStatus.hidden = false;\n  imageStatus.textContent = screen.visualLabel || "ZUSTAND";\n}\n\nasync function renderItem({ animate = true } = {}) {\n  const item = currentItem();\n  if (!item || state.transitioning) return;\n  state.transitioning = true;\n  const token = ++state.transitionToken;\n\n  try {\n    const imagePromise = isEditorial(item)\n      ? Promise.resolve(null)\n      : resolveArticleImage(item);\n\n    if (animate) {\n      stage.classList.add("is-changing");\n      await new Promise((resolve) =>\n        window.setTimeout(resolve, TRANSITION_MS / 2)\n      );\n    }\n    if (token !== state.transitionToken) return;\n\n    if (isEditorial(item)) {\n      updateEditorialText(item);\n    } else {\n      updateArticleText(item);\n      await imagePromise;\n      await showArticleImage(item, token);\n    }\n    if (token !== state.transitionToken) return;\n\n    state.remainingMs = itemDurationSeconds(item) * 1000;\n    state.lastTick = performance.now();\n    updateTimerDisplay();\n    requestAnimationFrame(() => {\n      if (token === state.transitionToken) stage.classList.remove("is-changing");\n    });\n    preloadNeighbours();\n  } finally {\n    state.transitioning = false;\n  }\n}\n\nfunction updateTimerDisplay() {\n  const total = Math.max(1, itemDurationSeconds() * 1000);\n  const remaining = Math.max(0, state.remainingMs);\n  const seconds = Math.ceil(remaining / 1000);\n  const min = String(Math.floor(seconds / 60)).padStart(2, "0");\n  const sec = String(seconds % 60).padStart(2, "0");\n  countdownLabel.textContent = state.paused\n    ? `Pausiert bei ${min}:${sec}`\n    : `Automatischer Wechsel in ${min}:${sec}`;\n  progressBar.style.transform = `scaleX(${Math.min(1, remaining / total)})`;\n}\n\nfunction nextItem() {\n  if (!state.items.length || state.transitioning) return;\n  state.currentIndex = (state.currentIndex + 1) % state.items.length;\n  void renderItem();\n}\n\nfunction previousItem() {\n  if (!state.items.length || state.transitioning) return;\n  state.currentIndex =\n    (state.currentIndex - 1 + state.items.length) % state.items.length;\n  void renderItem();\n}\n\nfunction togglePause(forceState = null) {\n  state.paused = forceState === null ? !state.paused : forceState;\n  pauseButton.setAttribute("aria-pressed", String(state.paused));\n  pauseIcon.textContent = state.paused ? "▶" : "⏸";\n  pauseLabel.textContent = state.paused ? "Weiter" : "Pause";\n  state.lastTick = performance.now();\n  updateTimerDisplay();\n}\n\nfunction tick(now) {\n  const elapsed = now - state.lastTick;\n  state.lastTick = now;\n  if (!state.paused && state.items.length > 1 && !dialog.open) {\n    state.remainingMs -= elapsed;\n    if (state.remainingMs <= 0 && !state.transitioning) {\n      state.remainingMs = itemDurationSeconds() * 1000;\n      nextItem();\n    }\n  }\n  updateTimerDisplay();\n  state.animationFrame = requestAnimationFrame(tick);\n}\n\nfunction splitText(text) {\n  const parts = String(text || "")\n    .split(/\\n{2,}/)\n    .map((part) => part.trim())\n    .filter(Boolean);\n  return parts\n    .map((part, index) => {\n      const headingLike = index > 0 && part.length < 95 && !/[.!?]$/.test(part);\n      return headingLike\n        ? `<h3>${escapeHtml(part)}</h3>`\n        : `<p>${escapeHtml(part).replace(/\\n/g, "<br>")}</p>`;\n    })\n    .join("");\n}\n\nfunction openArticle() {\n  const article = currentItem();\n  if (!article || isEditorial(article)) return;\n  const boundary =\n    boundaryNames[article.planetaryBoundary] ||\n    article.planetaryBoundary ||\n    "ZUSTAND";\n  const sections = (article.article || [])\n    .map((section) => {\n      const heading = section.heading\n        ? `<h3>${escapeHtml(section.heading)}</h3>`\n        : "";\n      return `${heading}${splitText(section.text)}`;\n    })\n    .join("");\n  const name = sourceName(article) || "Keine Quellenangabe";\n  const sourceMarkup = article.sourceUrl\n    ? `<a href="${escapeHtml(article.sourceUrl)}" target="_blank" rel="noopener noreferrer">Originalquelle öffnen →</a>`\n    : "";\n  const resolvedImage = image.hidden ? "" : image.getAttribute("src");\n  const imageMarkup = resolvedImage\n    ? `<img class="dialog-image" src="${escapeHtml(resolvedImage)}" alt="${escapeHtml(image.alt)}">`\n    : "";\n  dialogContent.innerHTML = `\n    <div class="dialog-meta">${escapeHtml(boundary)} · ${escapeHtml(formatDate(article.publicationDate))}</div>\n    <h2 class="dialog-title">${escapeHtml(article.title)}</h2>\n    ${article.subtitle ? `<div class="dialog-subtitle">${escapeHtml(article.subtitle)}</div>` : ""}\n    ${imageMarkup}\n    <div class="article-text">\n      ${sections || `<p>${escapeHtml(article.summary || "")}</p>`}\n    </div>\n    <div class="source-box">\n      <strong>Quelle</strong><br>\n      ${escapeHtml(name)}<br>\n      ${sourceMarkup}\n    </div>\n  `;\n  dialog.showModal();\n}\n\nasync function toggleFullscreen() {\n  try {\n    if (!document.fullscreenElement) {\n      await document.documentElement.requestFullscreen();\n    } else {\n      await document.exitFullscreen();\n    }\n  } catch (error) {\n    console.error("Vollbild konnte nicht aktiviert werden:", error);\n  }\n}\n\nfunction normalizePositiveInteger(value, fallback, minimum = 1) {\n  const number = Number(value);\n  return Number.isFinite(number) && number >= minimum\n    ? Math.round(number)\n    : fallback;\n}\n\nfunction buildRotation(articles, editorialScreens, editorialEvery) {\n  const news = articles.map((article, index) => ({\n    ...article,\n    type: article.type === "editorial" ? "article" : (article.type || "article"),\n    _articleNumber: index + 1\n  }));\n  const screens = editorialScreens\n    .filter((screen) => screen && screen.enabled !== false)\n    .map((screen) => ({ ...screen, type: "editorial" }));\n\n  if (!news.length) return screens;\n  if (!screens.length) return news;\n\n  const interval = Math.max(1, editorialEvery);\n  const newsNeeded = interval * screens.length;\n  const rounds = Math.max(1, Math.ceil(newsNeeded / news.length));\n  const items = [];\n  let screenIndex = 0;\n  let newsSinceEditorial = 0;\n\n  for (let round = 0; round < rounds; round += 1) {\n    for (const article of news) {\n      items.push({ ...article });\n      newsSinceEditorial += 1;\n      if (newsSinceEditorial >= interval && screenIndex < screens.length) {\n        items.push(screens[screenIndex]);\n        screenIndex += 1;\n        newsSinceEditorial = 0;\n      }\n    }\n  }\n\n  while (screenIndex < screens.length) {\n    for (const article of news) {\n      items.push({ ...article });\n      newsSinceEditorial += 1;\n      if (newsSinceEditorial >= interval) break;\n    }\n    items.push(screens[screenIndex]);\n    screenIndex += 1;\n    newsSinceEditorial = 0;\n  }\n\n  return items;\n}\n\nfunction showLoadError(title, summary) {\n  articleMeta.textContent = "Fehler beim Laden";\n  articleTitle.textContent = title;\n  articleSummary.textContent = summary;\n  articleCounter.textContent = "0 / 0";\n  imageStatus.textContent = "Keine Daten";\n  articleSource.hidden = true;\n  articleConnection.hidden = true;\n  [pauseButton, nextButton, readMoreButton].forEach((button) => {\n    button.disabled = true;\n  });\n}\n\nasync function loadNews() {\n  try {\n    const response = await fetch(`news.json?v=${Date.now()}`, { cache: "no-store" });\n    if (!response.ok) throw new Error(`HTTP ${response.status}`);\n    const data = await response.json();\n    const rotation = data.rotation || {};\n    state.articleSeconds = normalizePositiveInteger(\n      rotation.articleSeconds,\n      DEFAULT_ARTICLE_SECONDS,\n      5\n    );\n    state.editorialSeconds = normalizePositiveInteger(\n      rotation.editorialSeconds,\n      DEFAULT_EDITORIAL_SECONDS,\n      5\n    );\n    state.editorialEvery = normalizePositiveInteger(\n      rotation.editorialEvery,\n      DEFAULT_EDITORIAL_EVERY,\n      1\n    );\n    state.articles = Array.isArray(data.articles) ? data.articles : [];\n    state.editorialScreens = Array.isArray(data.editorialScreens)\n      ? data.editorialScreens\n      : [];\n    state.items = buildRotation(\n      state.articles,\n      state.editorialScreens,\n      state.editorialEvery\n    );\n\n    if (!state.items.length) {\n      showLoadError(\n        "Noch keine Inhalte vorhanden",\n        "Sobald news.json Beiträge oder redaktionelle Screens enthält, erscheinen sie automatisch hier."\n      );\n      return;\n    }\n\n    preloadItem(state.items[0]);\n    preloadItem(state.items[1]);\n    state.remainingMs = itemDurationSeconds(state.items[0]) * 1000;\n    await renderItem({ animate: false });\n    state.animationFrame = requestAnimationFrame(tick);\n  } catch (error) {\n    console.error(error);\n    showLoadError(\n      "news.json konnte nicht gelesen werden",\n      "Bitte prüfen, ob news.json im selben Ordner wie index.html liegt."\n    );\n  }\n}\n\npauseButton.addEventListener("click", () => togglePause());\nnextButton.addEventListener("click", nextItem);\nreadMoreButton.addEventListener("click", openArticle);\nfullscreenButton.addEventListener("click", toggleFullscreen);\ndialogClose.addEventListener("click", () => dialog.close());\n\ndialog.addEventListener("click", (event) => {\n  if (event.target === dialog) dialog.close();\n});\n\ndocument.addEventListener("keydown", (event) => {\n  if (dialog.open) {\n    if (event.key === "Escape") dialog.close();\n    return;\n  }\n  if (event.key === "ArrowRight") {\n    event.preventDefault();\n    nextItem();\n  } else if (event.key === "ArrowLeft") {\n    event.preventDefault();\n    previousItem();\n  } else if (event.code === "Space") {\n    event.preventDefault();\n    togglePause();\n  } else if (event.key.toLowerCase() === "f") {\n    void toggleFullscreen();\n  }\n});\n\ndocument.addEventListener("visibilitychange", () => {\n  state.lastTick = performance.now();\n});\n\nvoid loadNews();\n'
CSS_PATCH = '/* Z-PANEL 5.0 – größere Lesbarkeit, sichtbare Quelle und redaktionelle Zwischenscreens */\n[hidden] {\n  display: none !important;\n}\n\n.story h1 {\n  margin-bottom: 20px;\n  font-size: clamp(2.25rem, 3.55vw, 4.75rem);\n  line-height: 1.03;\n}\n\n.article-summary {\n  max-width: 42em;\n  font-size: clamp(1.2rem, 1.78vw, 1.92rem);\n  line-height: 1.43;\n  white-space: pre-line;\n}\n\n.article-source {\n  margin-top: 20px;\n  color: var(--muted);\n  font-size: clamp(.9rem, 1.05vw, 1.08rem);\n  line-height: 1.4;\n  font-weight: 720;\n}\n\n.article-connection {\n  margin-top: 13px;\n  padding-left: 15px;\n  border-left: 3px solid rgba(240, 211, 61, .72);\n  color: #dfe4df;\n  font-size: clamp(.92rem, 1.08vw, 1.13rem);\n  line-height: 1.45;\n}\n\n.story-actions {\n  margin-top: clamp(22px, 3vh, 38px);\n}\n\n.stage.is-editorial {\n  grid-template-columns: 38% 62%;\n}\n\n.stage.is-editorial .visual {\n  display: grid;\n  place-items: center;\n  background:\n    radial-gradient(circle at 30% 25%, rgba(240, 211, 61, .24), transparent 33%),\n    linear-gradient(145deg, #1d2b24, #0b110e 72%);\n}\n\n.stage.is-editorial .visual::before {\n  content: "Z";\n  position: absolute;\n  z-index: 1;\n  color: var(--accent);\n  font-size: clamp(10rem, 21vw, 24rem);\n  line-height: 1;\n  font-weight: 950;\n  opacity: .18;\n}\n\n.stage.is-editorial .visual-shade {\n  background:\n    linear-gradient(90deg, transparent 55%, rgba(11,17,14,.55)),\n    linear-gradient(0deg, rgba(11,17,14,.35), transparent 38%);\n}\n\n.stage.is-editorial .image-status {\n  position: relative;\n  inset: auto;\n  z-index: 2;\n  padding: 30px;\n  color: white;\n  font-size: clamp(1.8rem, 3.1vw, 3.7rem);\n  line-height: 1;\n  letter-spacing: .16em;\n  text-transform: uppercase;\n  font-weight: 950;\n}\n\n.stage.is-editorial .story {\n  background:\n    linear-gradient(135deg, rgba(240, 211, 61, .07), transparent 42%),\n    var(--panel);\n}\n\n.stage.is-editorial h1 {\n  max-width: 19ch;\n  font-size: clamp(2.5rem, 4.2vw, 5.3rem);\n}\n\n.stage.is-editorial .article-summary {\n  max-width: 48em;\n  font-size: clamp(1.15rem, 1.52vw, 1.68rem);\n  line-height: 1.48;\n}\n\n.stage.is-editorial .story-actions {\n  margin-top: 24px;\n}\n\n@media (max-width: 1050px) {\n  .stage.is-editorial {\n    grid-template-columns: 1fr;\n  }\n\n  .stage.is-editorial .visual {\n    min-height: 24vh;\n  }\n}\n\n@media (max-width: 650px) {\n  .article-summary {\n    font-size: 1.12rem;\n  }\n\n  .article-source,\n  .article-connection {\n    font-size: .94rem;\n  }\n\n  .stage.is-editorial .article-summary {\n    font-size: 1.05rem;\n  }\n}\n'
STUDIO_56 = '#!/usr/bin/env python3\nfrom __future__ import annotations\n\n"""ZUSTAND News Studio 5.6 – redaktionelle Zwischenscreens.\n\nBenötigt im selben Ordner:\n- news_studio_5_5_2.py\n- dessen bisherige Basisdateien\n\nVersion 5.6 nutzt die bereits vorhandenen Felder „Leitbild“ und\n„Redaktionskodex“. Beim erfolgreichen Erzeugen von news.json werden daraus\nredaktionelle Zwischenscreens. Es entstehen keine doppelten Texteingaben.\n"""\n\nimport importlib.util\nimport json\nimport sys\nfrom datetime import datetime, timezone\nfrom pathlib import Path\nfrom typing import Any\n\nSCRIPT_DIR = Path(__file__).resolve().parent\nBASE_SCRIPT = SCRIPT_DIR / "news_studio_5_5_2.py"\nif not BASE_SCRIPT.exists():\n    raise SystemExit(\n        "news_studio_5_5_2.py wurde nicht gefunden.\\n"\n        "Lege News Studio 5.6 in denselben Ordner wie Version 5.5.2."\n    )\n\nspec = importlib.util.spec_from_file_location("news_studio_5_5_2_base", BASE_SCRIPT)\nif spec is None or spec.loader is None:\n    raise SystemExit("News Studio 5.5.2 konnte nicht geladen werden.")\nbase56 = importlib.util.module_from_spec(spec)\nsys.modules[spec.name] = base56\nspec.loader.exec_module(base56)\n\nPROJECT_ROOT = Path(getattr(base56, "PROJECT_ROOT", SCRIPT_DIR))\nbase_app = getattr(base56, "base_app", None)\nOUTPUT = Path(getattr(base_app, "OUTPUT", PROJECT_ROOT / "news.json"))\n\nARTICLE_SECONDS = 30\nEDITORIAL_SECONDS = 18\nEDITORIAL_EVERY = 8\n\n\ndef now_iso() -> str:\n    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")\n\n\ndef clean_one_line(value: object, limit: int = 120) -> str:\n    text = " ".join(str(value or "").split())\n    return text[:limit].rstrip()\n\n\ndef infer_source_title(value: object) -> str:\n    """Gewinnt aus dem vorhandenen Quellenfeld eine knappe Herausgeberzeile."""\n    lines = [line.strip(" •\\t") for line in str(value or "").splitlines()]\n    for line in lines:\n        if not line or line.lower().startswith(("http://", "https://", "url:")):\n            continue\n        lowered = line.lower()\n        for prefix in ("herausgeber:", "institution:", "quelle:"):\n            if lowered.startswith(prefix):\n                return clean_one_line(line[len(prefix):], 100)\n    for line in lines:\n        if line and "http://" not in line.lower() and "https://" not in line.lower():\n            return clean_one_line(line, 100)\n    return ""\n\n\ndef build_editorial_screens(editorial_data: dict[str, Any]) -> list[dict[str, Any]]:\n    guide = editorial_data.get("guide", {})\n    if not isinstance(guide, dict):\n        guide = {}\n\n    mission = str(guide.get("mission", "") or "").strip()\n    code = str(guide.get("code", "") or "").strip()\n    screens: list[dict[str, Any]] = []\n\n    if mission:\n        screens.append(\n            {\n                "id": "redaktion_leitbild",\n                "type": "editorial",\n                "editorialType": "mission",\n                "label": "Leitbild",\n                "kicker": "ZUSTAND · Wofür wir arbeiten",\n                "title": "Wofür ZUSTAND steht",\n                "text": mission,\n                "visualLabel": "Leitbild",\n                "durationSeconds": EDITORIAL_SECONDS,\n                "enabled": True,\n            }\n        )\n\n    if code:\n        screens.append(\n            {\n                "id": "redaktion_kodex",\n                "type": "editorial",\n                "editorialType": "code",\n                "label": "Redaktionskodex",\n                "kicker": "ZUSTAND · So arbeiten wir",\n                "title": "Unser Redaktionskodex",\n                "text": code,\n                "visualLabel": "Kodex",\n                "durationSeconds": 24,\n                "enabled": True,\n            }\n        )\n\n    return screens\n\n\ndef augment_news_payload(\n    payload: dict[str, Any], editorial_data: dict[str, Any]\n) -> dict[str, Any]:\n    articles = payload.get("articles", [])\n    article_editorial = editorial_data.get("articles", {})\n    if not isinstance(article_editorial, dict):\n        article_editorial = {}\n\n    if isinstance(articles, list):\n        for article in articles:\n            if not isinstance(article, dict):\n                continue\n            article_id = str(article.get("id", "") or "").strip()\n            details = article_editorial.get(article_id, {})\n            if not isinstance(details, dict):\n                continue\n\n            source_type = clean_one_line(details.get("sourceType"), 90)\n            connection = str(details.get("screenConnection", "") or "").strip()\n            source_title = infer_source_title(details.get("sources"))\n\n            if source_type:\n                article["sourceType"] = source_type\n            else:\n                article.pop("sourceType", None)\n\n            if connection:\n                article["screenConnection"] = connection\n            else:\n                article.pop("screenConnection", None)\n\n            if source_title and not str(article.get("sourceTitle", "") or "").strip():\n                article["sourceTitle"] = source_title\n\n    screens = build_editorial_screens(editorial_data)\n    payload["contentSchema"] = 2\n    payload["rotation"] = {\n        "articleSeconds": ARTICLE_SECONDS,\n        "editorialSeconds": EDITORIAL_SECONDS,\n        "editorialEvery": EDITORIAL_EVERY,\n    }\n    payload["editorialScreenCount"] = len(screens)\n    payload["editorialScreens"] = screens\n    payload["editorialGeneratedAt"] = now_iso()\n    return payload\n\n\ndef augment_news_json(editorial_data: dict[str, Any]) -> tuple[bool, str]:\n    if not OUTPUT.exists():\n        return False, "news.json wurde nicht gefunden."\n    try:\n        payload = json.loads(OUTPUT.read_text(encoding="utf-8-sig"))\n        if not isinstance(payload, dict):\n            raise ValueError("news.json enthält kein JSON-Objekt.")\n        augment_news_payload(payload, editorial_data)\n        temp = OUTPUT.with_suffix(".json.tmp")\n        temp.write_text(\n            json.dumps(payload, ensure_ascii=False, indent=2) + "\\n",\n            encoding="utf-8",\n        )\n        temp.replace(OUTPUT)\n        count = len(payload.get("editorialScreens", []))\n        return True, f"{count} redaktionelle Zwischenscreen(s) ergänzt."\n    except (OSError, json.JSONDecodeError, ValueError) as exc:\n        return False, f"Redaktionelle Screens konnten nicht ergänzt werden: {exc}"\n\n\nclass NewsStudio56(base56.NewsStudio552):\n    def __init__(self):\n        super().__init__()\n        self.title("ZUSTAND News Studio 5.6")\n        self._replace_widget_text(\n            "ZUSTAND News Studio 5.5.2", "ZUSTAND News Studio 5.6"\n        )\n        self._replace_widget_text(\n            (\n                "Hier werden Leitbild, Redaktionsregeln und die Zusammenhänge hinter "\n                "den Meldungen dauerhaft festgehalten. Die Angaben bleiben lokal und "\n                "werden noch nicht automatisch auf dem Infoscreen veröffentlicht."\n            ),\n            (\n                "Hier werden Leitbild, Redaktionsregeln und die Zusammenhänge hinter "\n                "den Meldungen dauerhaft festgehalten. Leitbild und Redaktionskodex "\n                "werden beim Erzeugen von news.json automatisch als ruhige "\n                "Zwischenscreens veröffentlicht."\n            ),\n        )\n        self.status_var.set(\n            "News Studio 5.6 bereit │ Leitbild und Redaktionskodex werden in news.json übernommen"\n        )\n\n    def run_generator(self):\n        before = OUTPUT.read_bytes() if OUTPUT.exists() else None\n        super().run_generator()\n        after = OUTPUT.read_bytes() if OUTPUT.exists() else None\n\n        # Bei einem Generatorfehler bleibt die bestehende news.json unverändert.\n        if after is None or after == before:\n            return\n\n        # Neueste Eingaben aus dem Reiter Redaktion übernehmen, auch wenn direkt\n        # vor dem Veröffentlichen noch nicht zu einem anderen Reiter gewechselt wurde.\n        if hasattr(self, "editorial_guide_widgets"):\n            for key, widget in self.editorial_guide_widgets.items():\n                self.editorial_data.setdefault("guide", {})[key] = widget.get(\n                    "1.0", "end"\n                ).strip()\n            self.editorial_data["updatedAt"] = now_iso()\n            base56.write_editorial_file(self.editorial_data)\n\n        success, message = augment_news_json(self.editorial_data)\n        self.status_var.set(\n            f"news.json erzeugt │ {message}" if success else message\n        )\n        if hasattr(self, "generator_log"):\n            try:\n                self.generator_log.configure(state="normal")\n                self.generator_log.insert(\n                    "end",\n                    "\\n\\nREDAKTIONELLE ZWISCHENSCREENS\\n"\n                    + ("✓ " if success else "⚠ ")\n                    + message,\n                )\n                self.generator_log.configure(state="disabled")\n                self.generator_log.see("end")\n            except Exception:\n                pass\n\n\nif __name__ == "__main__":\n    app = NewsStudio56()\n    app.mainloop()\n'

CSS_START = "/* BEGIN Z-PANEL 5.0 */"
CSS_END = "/* END Z-PANEL 5.0 */"

DEFAULT_GUIDE = {
    "mission": (
        "ZUSTAND macht den Zustand unserer natürlichen Lebensgrundlagen sichtbar "
        "und verständlich. Grundlage sind wissenschaftliche Primärquellen, "
        "transparente Recherche, nachvollziehbare Zusammenhänge und der Dialog "
        "mit Forschenden. ZUSTAND möchte Orientierung geben, nicht polarisieren."
    ),
    "code": (
        "1. Wir bevorzugen wissenschaftliche Primärquellen.\n"
        "2. Wir unterscheiden Messdaten, Studien, Berichte und Meinungen.\n"
        "3. Wir zeigen Zusammenhänge statt isolierter Ereignisse.\n"
        "4. Wir machen Unsicherheiten sichtbar.\n"
        "5. Wir erklären Fachbegriffe verständlich.\n"
        "6. Wir suchen den Dialog mit Autorinnen und Autoren.\n"
        "7. Wir korrigieren Fehler offen.\n"
        "8. Wir kennzeichnen Quellen transparent.\n"
        "9. Wir vermeiden unnötige Zuspitzung.\n"
        "10. Wir befähigen Menschen, sich selbst ein Urteil zu bilden."
    ),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (
            (candidate / "index.html").is_file()
            and (candidate / "app.js").is_file()
            and (candidate / "styles.css").is_file()
        ):
            return candidate
    raise FileNotFoundError(
        "Kein Z-PANEL-Projektordner gefunden. Lege dieses Skript in den Ordner "
        "mit index.html, app.js und styles.css."
    )


def backup_files(root: Path, paths: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = root / "backups" / f"vor_z_panel_5_0_{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.exists():
            relative = path.relative_to(root) if path.is_relative_to(root) else Path(path.name)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    return target


def patch_index(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    if 'id="article-source"' not in content:
        pattern = re.compile(
            r'(<p id="article-summary" class="article-summary">.*?</p>)',
            re.S,
        )
        replacement = (
            r'\1\n'
            '        <div id="article-source" class="article-source" hidden></div>\n'
            '        <div id="article-connection" class="article-connection" hidden></div>'
        )
        content, count = pattern.subn(replacement, content, count=1)
        if count != 1:
            raise RuntimeError("Der Kurztextbereich in index.html wurde nicht gefunden.")
    path.write_text(content, encoding="utf-8")


def patch_styles(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    block = f"{CSS_START}\n{CSS_PATCH.rstrip()}\n{CSS_END}"
    pattern = re.compile(
        re.escape(CSS_START) + r".*?" + re.escape(CSS_END),
        re.S,
    )
    if pattern.search(content):
        content = pattern.sub(block, content, count=1)
    else:
        content = content.rstrip() + "\n\n" + block + "\n"
    path.write_text(content, encoding="utf-8")


def read_editorial(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                guide = data.setdefault("guide", {})
                for key, value in DEFAULT_GUIDE.items():
                    guide.setdefault(key, value)
                data.setdefault("articles", {})
                return data
        except (OSError, json.JSONDecodeError):
            pass
    data = {"version": 1, "guide": dict(DEFAULT_GUIDE), "articles": {}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def clean_one_line(value: object, limit: int = 120) -> str:
    return " ".join(str(value or "").split())[:limit].rstrip()


def infer_source_title(value: object) -> str:
    lines = [line.strip(" •\t") for line in str(value or "").splitlines()]
    for line in lines:
        if not line or line.lower().startswith(("http://", "https://", "url:")):
            continue
        lowered = line.lower()
        for prefix in ("herausgeber:", "institution:", "quelle:"):
            if lowered.startswith(prefix):
                return clean_one_line(line[len(prefix):], 100)
    for line in lines:
        if line and "http://" not in line.lower() and "https://" not in line.lower():
            return clean_one_line(line, 100)
    return ""


def build_screens(editorial: dict[str, Any]) -> list[dict[str, Any]]:
    guide = editorial.get("guide", {})
    mission = str(guide.get("mission", "") or "").strip()
    code = str(guide.get("code", "") or "").strip()
    screens: list[dict[str, Any]] = []
    if mission:
        screens.append({
            "id": "redaktion_leitbild",
            "type": "editorial",
            "editorialType": "mission",
            "label": "Leitbild",
            "kicker": "ZUSTAND · Wofür wir arbeiten",
            "title": "Wofür ZUSTAND steht",
            "text": mission,
            "visualLabel": "Leitbild",
            "durationSeconds": 18,
            "enabled": True,
        })
    if code:
        screens.append({
            "id": "redaktion_kodex",
            "type": "editorial",
            "editorialType": "code",
            "label": "Redaktionskodex",
            "kicker": "ZUSTAND · So arbeiten wir",
            "title": "Unser Redaktionskodex",
            "text": code,
            "visualLabel": "Kodex",
            "durationSeconds": 24,
            "enabled": True,
        })
    return screens


def augment_news(news_path: Path, editorial: dict[str, Any]) -> int:
    if not news_path.exists():
        return 0
    payload = json.loads(news_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("news.json enthält kein JSON-Objekt.")
    article_editorial = editorial.get("articles", {})
    if not isinstance(article_editorial, dict):
        article_editorial = {}
    articles = payload.get("articles", [])
    if isinstance(articles, list):
        for article in articles:
            if not isinstance(article, dict):
                continue
            details = article_editorial.get(str(article.get("id", "")), {})
            if not isinstance(details, dict):
                continue
            source_type = clean_one_line(details.get("sourceType"), 90)
            connection = str(details.get("screenConnection", "") or "").strip()
            source_title = infer_source_title(details.get("sources"))
            if source_type:
                article["sourceType"] = source_type
            if connection:
                article["screenConnection"] = connection
            if source_title and not str(article.get("sourceTitle", "") or "").strip():
                article["sourceTitle"] = source_title
    screens = build_screens(editorial)
    payload["contentSchema"] = 2
    payload["rotation"] = {
        "articleSeconds": 30,
        "editorialSeconds": 18,
        "editorialEvery": 8,
    }
    payload["editorialScreenCount"] = len(screens)
    payload["editorialScreens"] = screens
    payload["editorialGeneratedAt"] = now_iso()
    news_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(screens)


def main() -> None:
    root = find_project_root(Path(__file__).resolve().parent)
    index_path = root / "index.html"
    app_path = root / "app.js"
    styles_path = root / "styles.css"
    news_path = root / "news.json"
    editorial_path = root / "newsredaktion" / "redaktion" / "redaktion.json"
    studio_path = Path(__file__).resolve().parent / "news_studio_5_6.py"

    backup = backup_files(
        root,
        [index_path, app_path, styles_path, news_path, editorial_path, studio_path],
    )
    patch_index(index_path)
    app_path.write_text(APP_JS, encoding="utf-8")
    patch_styles(styles_path)
    studio_path.write_text(STUDIO_56, encoding="utf-8")
    editorial = read_editorial(editorial_path)
    screen_count = augment_news(news_path, editorial)

    print("Z-PANEL 5.0 und News Studio 5.6 wurden vorbereitet.")
    print(f"Projektordner: {root}")
    print(f"Sicherung: {backup}")
    print("")
    print("Geändert:")
    print("- app.js: Meldungen und redaktionelle Zwischenscreens in einer Rotation")
    print("- index.html: sichtbare Quellen- und Zusammenhangszeile")
    print("- styles.css: größere Kurztexte und eigenes ruhiges Editorial-Layout")
    print("- news_studio_5_6.py: Leitbild und Kodex werden beim Veröffentlichen übernommen")
    if news_path.exists():
        print(f"- news.json: {screen_count} redaktionelle Zwischenscreen(s) ergänzt")
    else:
        print("- news.json fehlt noch; sie wird beim nächsten Veröffentlichen ergänzt")
    print("")
    print("Als Nächstes:")
    print("1. news_studio_5_6.py starten.")
    print("2. Unter Redaktion Leitbild und Kodex prüfen und speichern.")
    print("3. news.json erneut erzeugen.")
    print("4. Lokal testen, dann in GitHub Desktop committen und pushen.")


if __name__ == "__main__":
    main()
