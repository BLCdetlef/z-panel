#!/usr/bin/env python3
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

NEW_APP_JS = '"use strict";\n\nconst ROTATION_SECONDS = 30;\nconst TRANSITION_MS = 360;\n\nconst boundaryNames = {\n  KL: "Klimawandel",\n  BD: "Integrität der Biosphäre",\n  LN: "Landnutzungswandel",\n  FW: "Süßwasser",\n  NP: "Stickstoff und Phosphor",\n  OA: "Ozeanversauerung",\n  OZ: "Stratosphärisches Ozon",\n  AE: "Atmosphärische Aerosole",\n  NS: "Neue Substanzen"\n};\n\nconst state = {\n  articles: [],\n  currentIndex: 0,\n  paused: false,\n  remainingMs: ROTATION_SECONDS * 1000,\n  lastTick: performance.now(),\n  animationFrame: null,\n  transitionToken: 0\n};\n\nconst imageCache = new Map();\n\nconst stage = document.getElementById("stage");\nconst image = document.getElementById("article-image");\nconst imageStatus = document.getElementById("image-status");\nconst boundaryBadge = document.getElementById("boundary-badge");\nconst articleMeta = document.getElementById("article-meta");\nconst articleTitle = document.getElementById("article-title");\nconst articleSummary = document.getElementById("article-summary");\nconst articleCounter = document.getElementById("article-counter");\nconst countdownLabel = document.getElementById("countdown-label");\nconst progressBar = document.getElementById("progress-bar");\nconst pauseButton = document.getElementById("pause-button");\nconst pauseIcon = document.getElementById("pause-icon");\nconst pauseLabel = document.getElementById("pause-label");\nconst nextButton = document.getElementById("next-button");\nconst readMoreButton = document.getElementById("read-more-button");\nconst fullscreenButton = document.getElementById("fullscreen-button");\nconst dialog = document.getElementById("article-dialog");\nconst dialogContent = document.getElementById("dialog-content");\nconst dialogClose = document.getElementById("dialog-close");\n\nfunction escapeHtml(value) {\n  return String(value ?? "")\n    .replace(/&/g, "&amp;")\n    .replace(/</g, "&lt;")\n    .replace(/>/g, "&gt;")\n    .replace(/"/g, "&quot;")\n    .replace(/\'/g, "&#039;");\n}\n\nfunction formatDate(value) {\n  if (!value) return "";\n  const date = new Date(`${value}T00:00:00`);\n  if (Number.isNaN(date.getTime())) return value;\n\n  return new Intl.DateTimeFormat("de-DE", {\n    day: "2-digit",\n    month: "long",\n    year: "numeric"\n  }).format(date);\n}\n\nfunction currentArticle() {\n  return state.articles[state.currentIndex] || null;\n}\n\nfunction candidateImagePaths(article) {\n  const candidates = [];\n\n  if (article.imageFile) candidates.push(article.imageFile);\n  if (article.imageUrl) candidates.push(article.imageUrl);\n\n  if (article.imageId) {\n    const id = article.imageId;\n    candidates.push(\n      `assets/images/${id}.webp`,\n      `assets/images/${id}.jpg`,\n      `assets/images/${id}.jpeg`,\n      `assets/images/${id}.png`\n    );\n  }\n\n  return [...new Set(candidates.filter(Boolean))];\n}\n\nfunction articleCacheKey(article) {\n  return String(article?.id || article?.imageId || article?.title || "");\n}\n\nfunction testImagePath(path) {\n  return new Promise((resolve) => {\n    const tester = new Image();\n    tester.decoding = "async";\n    tester.onload = async () => {\n      try {\n        if (typeof tester.decode === "function") {\n          await tester.decode();\n        }\n      } catch {\n        // Das Bild ist bereits geladen; ein Decode-Fehler blockiert nicht.\n      }\n      resolve(path);\n    };\n    tester.onerror = () => resolve(null);\n    tester.src = path;\n  });\n}\n\nasync function resolveArticleImage(article) {\n  const key = articleCacheKey(article);\n\n  if (imageCache.has(key)) {\n    return imageCache.get(key);\n  }\n\n  const promise = (async () => {\n    for (const path of candidateImagePaths(article)) {\n      const workingPath = await testImagePath(path);\n      if (workingPath) return workingPath;\n    }\n    return null;\n  })();\n\n  imageCache.set(key, promise);\n  return promise;\n}\n\nfunction preloadArticle(article) {\n  if (!article) return;\n  void resolveArticleImage(article);\n}\n\nfunction preloadNeighbours() {\n  const length = state.articles.length;\n  if (length < 2) return;\n\n  preloadArticle(state.articles[(state.currentIndex + 1) % length]);\n  preloadArticle(state.articles[(state.currentIndex + 2) % length]);\n  preloadArticle(state.articles[(state.currentIndex - 1 + length) % length]);\n}\n\nasync function showArticleImage(article, token) {\n  const alt = article.imageMetadata?.altText || article.title || "";\n  const resolvedPath = await resolveArticleImage(article);\n\n  if (token !== state.transitionToken) return;\n\n  image.alt = alt;\n\n  if (!resolvedPath) {\n    image.hidden = true;\n    image.removeAttribute("src");\n    imageStatus.hidden = false;\n    imageStatus.textContent = article.imageId\n      ? `Bild nicht gefunden. Erwartet wurde zum Beispiel: assets/images/${article.imageId}.jpg`\n      : "Für diesen Beitrag ist noch kein Bildpfad hinterlegt.";\n    return;\n  }\n\n  if (image.src !== new URL(resolvedPath, document.baseURI).href) {\n    image.src = resolvedPath;\n  }\n\n  image.hidden = false;\n  imageStatus.hidden = true;\n}\n\nfunction updateArticleText(article) {\n  const boundary =\n    boundaryNames[article.planetaryBoundary] ||\n    article.planetaryBoundary ||\n    "ZUSTAND";\n\n  boundaryBadge.textContent = boundary;\n  articleMeta.textContent = [boundary, formatDate(article.publicationDate)]\n    .filter(Boolean)\n    .join(" · ");\n  articleTitle.textContent = article.title || "Ohne Titel";\n  articleSummary.textContent =\n    article.summary || article.subtitle || "Keine Kurzbeschreibung vorhanden.";\n  articleCounter.textContent =\n    `${state.currentIndex + 1} / ${state.articles.length}`;\n}\n\nasync function renderArticle({ animate = true } = {}) {\n  const article = currentArticle();\n  if (!article) return;\n\n  const token = ++state.transitionToken;\n\n  // Das Bild wird vor dem sichtbaren Wechsel geladen und dekodiert.\n  const imagePromise = resolveArticleImage(article);\n\n  if (animate) {\n    stage.classList.add("is-changing");\n    await new Promise((resolve) =>\n      window.setTimeout(resolve, TRANSITION_MS / 2)\n    );\n  }\n\n  if (token !== state.transitionToken) return;\n\n  updateArticleText(article);\n  await imagePromise;\n  await showArticleImage(article, token);\n\n  if (token !== state.transitionToken) return;\n\n  state.remainingMs = ROTATION_SECONDS * 1000;\n  state.lastTick = performance.now();\n  updateTimerDisplay();\n\n  requestAnimationFrame(() => {\n    if (token === state.transitionToken) {\n      stage.classList.remove("is-changing");\n    }\n  });\n\n  preloadNeighbours();\n}\n\nfunction updateTimerDisplay() {\n  const total = ROTATION_SECONDS * 1000;\n  const remaining = Math.max(0, state.remainingMs);\n  const seconds = Math.ceil(remaining / 1000);\n  const min = String(Math.floor(seconds / 60)).padStart(2, "0");\n  const sec = String(seconds % 60).padStart(2, "0");\n\n  countdownLabel.textContent = state.paused\n    ? `Pausiert bei ${min}:${sec}`\n    : `Automatischer Wechsel in ${min}:${sec}`;\n\n  progressBar.style.transform = `scaleX(${remaining / total})`;\n}\n\nfunction nextArticle() {\n  if (!state.articles.length) return;\n  state.currentIndex = (state.currentIndex + 1) % state.articles.length;\n  void renderArticle();\n}\n\nfunction previousArticle() {\n  if (!state.articles.length) return;\n  state.currentIndex =\n    (state.currentIndex - 1 + state.articles.length) % state.articles.length;\n  void renderArticle();\n}\n\nfunction togglePause(forceState = null) {\n  state.paused = forceState === null ? !state.paused : forceState;\n  pauseButton.setAttribute("aria-pressed", String(state.paused));\n  pauseIcon.textContent = state.paused ? "▶" : "⏸";\n  pauseLabel.textContent = state.paused ? "Weiter" : "Pause";\n  state.lastTick = performance.now();\n  updateTimerDisplay();\n}\n\nfunction tick(now) {\n  const elapsed = now - state.lastTick;\n  state.lastTick = now;\n\n  if (!state.paused && state.articles.length > 1 && !dialog.open) {\n    state.remainingMs -= elapsed;\n    if (state.remainingMs <= 0) nextArticle();\n  }\n\n  updateTimerDisplay();\n  state.animationFrame = requestAnimationFrame(tick);\n}\n\nfunction splitText(text) {\n  const parts = String(text || "")\n    .split(/\\n{2,}/)\n    .map((part) => part.trim())\n    .filter(Boolean);\n\n  return parts\n    .map((part, index) => {\n      const headingLike =\n        index > 0 && part.length < 95 && !/[.!?]$/.test(part);\n\n      return headingLike\n        ? `<h3>${escapeHtml(part)}</h3>`\n        : `<p>${escapeHtml(part).replace(/\\n/g, "<br>")}</p>`;\n    })\n    .join("");\n}\n\nfunction openArticle() {\n  const article = currentArticle();\n  if (!article) return;\n\n  const boundary =\n    boundaryNames[article.planetaryBoundary] ||\n    article.planetaryBoundary ||\n    "ZUSTAND";\n\n  const sections = (article.article || [])\n    .map((section) => {\n      const heading = section.heading\n        ? `<h3>${escapeHtml(section.heading)}</h3>`\n        : "";\n      return `${heading}${splitText(section.text)}`;\n    })\n    .join("");\n\n  const sourceName =\n    article.sourceTitle ||\n    article.sourceId ||\n    (() => {\n      try {\n        return article.sourceUrl\n          ? new URL(article.sourceUrl).hostname.replace(/^www\\./, "")\n          : "Keine Quellenangabe";\n      } catch {\n        return "Originalquelle";\n      }\n    })();\n\n  const sourceMarkup = article.sourceUrl\n    ? `<a href="${escapeHtml(article.sourceUrl)}" target="_blank" rel="noopener noreferrer">Originalquelle öffnen →</a>`\n    : "";\n\n  const resolvedImage = image.hidden ? "" : image.getAttribute("src");\n  const imageMarkup = resolvedImage\n    ? `<img class="dialog-image" src="${escapeHtml(resolvedImage)}" alt="${escapeHtml(image.alt)}">`\n    : "";\n\n  dialogContent.innerHTML = `\n    <div class="dialog-meta">${escapeHtml(boundary)} · ${escapeHtml(formatDate(article.publicationDate))}</div>\n    <h2 class="dialog-title">${escapeHtml(article.title)}</h2>\n    ${article.subtitle ? `<div class="dialog-subtitle">${escapeHtml(article.subtitle)}</div>` : ""}\n    ${imageMarkup}\n    <div class="article-text">\n      ${sections || `<p>${escapeHtml(article.summary || "")}</p>`}\n    </div>\n    <div class="source-box">\n      <strong>Quelle</strong><br>\n      ${escapeHtml(sourceName)}<br>\n      ${sourceMarkup}\n    </div>\n  `;\n\n  dialog.showModal();\n}\n\nasync function toggleFullscreen() {\n  try {\n    if (!document.fullscreenElement) {\n      await document.documentElement.requestFullscreen();\n    } else {\n      await document.exitFullscreen();\n    }\n  } catch (error) {\n    console.error("Vollbild konnte nicht aktiviert werden:", error);\n  }\n}\n\nasync function loadNews() {\n  try {\n    const response = await fetch(`news.json?v=${Date.now()}`, {\n      cache: "no-store"\n    });\n\n    if (!response.ok) {\n      throw new Error(`HTTP ${response.status}`);\n    }\n\n    const data = await response.json();\n    state.articles = Array.isArray(data.articles) ? data.articles : [];\n\n    if (!state.articles.length) {\n      articleMeta.textContent = "Keine veröffentlichten Meldungen";\n      articleTitle.textContent = "Noch keine Artikel vorhanden";\n      articleSummary.textContent =\n        "Sobald news.json Beiträge enthält, erscheinen sie automatisch hier.";\n      articleCounter.textContent = "0 / 0";\n      imageStatus.textContent = "Keine Meldungen";\n\n      [pauseButton, nextButton, readMoreButton].forEach((button) => {\n        button.disabled = true;\n      });\n      return;\n    }\n\n    // Vor dem ersten Rendern werden das erste und das nächste Bild vorbereitet.\n    preloadArticle(state.articles[0]);\n    preloadArticle(state.articles[1]);\n\n    await renderArticle({ animate: false });\n    state.animationFrame = requestAnimationFrame(tick);\n  } catch (error) {\n    console.error(error);\n    articleMeta.textContent = "Fehler beim Laden";\n    articleTitle.textContent = "news.json konnte nicht gelesen werden";\n    articleSummary.textContent =\n      "Bitte prüfen, ob news.json im selben Ordner wie index.html liegt.";\n    articleCounter.textContent = "0 / 0";\n    imageStatus.textContent = "Keine Daten";\n\n    [pauseButton, nextButton, readMoreButton].forEach((button) => {\n      button.disabled = true;\n    });\n  }\n}\n\npauseButton.addEventListener("click", () => togglePause());\nnextButton.addEventListener("click", nextArticle);\nreadMoreButton.addEventListener("click", openArticle);\nfullscreenButton.addEventListener("click", toggleFullscreen);\ndialogClose.addEventListener("click", () => dialog.close());\n\ndialog.addEventListener("click", (event) => {\n  if (event.target === dialog) dialog.close();\n});\n\ndocument.addEventListener("keydown", (event) => {\n  if (dialog.open) {\n    if (event.key === "Escape") dialog.close();\n    return;\n  }\n\n  if (event.key === "ArrowRight") {\n    event.preventDefault();\n    nextArticle();\n  } else if (event.key === "ArrowLeft") {\n    event.preventDefault();\n    previousArticle();\n  } else if (event.code === "Space") {\n    event.preventDefault();\n    togglePause();\n  } else if (event.key.toLowerCase() === "f") {\n    void toggleFullscreen();\n  }\n});\n\ndocument.addEventListener("visibilitychange", () => {\n  state.lastTick = performance.now();\n});\n\nvoid loadNews();\n'

CSS_ADDITION = r"""
/* Z-Panel 4.0: flüssigere, GPU-gestützte Artikelübergänge */
.stage {
  will-change: opacity, transform;
  backface-visibility: hidden;
  transform: translate3d(0, 0, 0);
  transition:
    opacity 360ms ease,
    transform 360ms ease;
}

.stage.is-changing {
  opacity: 0;
  transform: translate3d(0, 6px, 0);
}

.article-image {
  display: block;
  will-change: opacity;
  backface-visibility: hidden;
}

@media (prefers-reduced-motion: reduce) {
  .stage,
  .stage.is-changing {
    transition: none;
    transform: none;
  }
}
"""

def find_project_root(start: Path) -> Path:
    candidates = [start, *start.parents]
    for candidate in candidates:
        if (
            (candidate / "index.html").is_file()
            and (candidate / "app.js").is_file()
            and (candidate / "styles.css").is_file()
        ):
            return candidate
    raise FileNotFoundError(
        "Kein Z-Panel-Projektordner gefunden. Lege dieses Skript bitte "
        "in den Ordner mit index.html, app.js und styles.css."
    )

def backup(path: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_dir / path.name)

def update_index(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    import re

    replacement = "<title>ZUSTAND Infoscreen</title>"
    if re.search(r"<title>.*?</title>", content, flags=re.I | re.S):
        content = re.sub(
            r"<title>.*?</title>",
            replacement,
            content,
            count=1,
            flags=re.I | re.S,
        )
    else:
        content = content.replace("</head>", f"  {replacement}\n</head>", 1)

    path.write_text(content, encoding="utf-8")

def update_styles(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    marker = "/* Z-Panel 4.0: flüssigere, GPU-gestützte Artikelübergänge */"
    if marker not in content:
        content = content.rstrip() + "\n\n" + CSS_ADDITION.strip() + "\n"
        path.write_text(content, encoding="utf-8")

def main() -> None:
    root = find_project_root(Path(__file__).resolve().parent)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = root / f"backup_vor_z_panel_4_0_{timestamp}"

    files = [
        root / "index.html",
        root / "app.js",
        root / "styles.css",
    ]
    for file in files:
        backup(file, backup_dir)

    update_index(root / "index.html")
    (root / "app.js").write_text(NEW_APP_JS, encoding="utf-8")
    update_styles(root / "styles.css")

    print("Z-Panel 4.0 wurde vorbereitet.")
    print(f"Projektordner: {root}")
    print(f"Sicherung: {backup_dir}")
    print("")
    print("Geändert:")
    print("- Browser-Titel: ZUSTAND Infoscreen")
    print("- nächstes und übernächstes Artikelbild werden vorgeladen")
    print("- Bilder werden vor dem Wechsel dekodiert")
    print("- der sichtbare Wechsel beginnt erst, wenn das Bild bereit ist")
    print("- schnelle Klicks können keine alten Bildladevorgänge mehr einblenden")
    print("- GPU-freundlicher Übergang")
    print("")
    print("Jetzt GitHub Desktop öffnen, Änderungen prüfen, committen und pushen.")

if __name__ == "__main__":
    main()
