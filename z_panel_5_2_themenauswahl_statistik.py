#!/usr/bin/env python3
from __future__ import annotations

"""Z-PANEL 5.2 – Themenauswahl und optionale anonyme Ereignisse."""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

HTML_MARKER = "<!-- Z-PANEL 5.2 THEMENAUSWAHL -->"
JS_MARKER = "/* Z-PANEL 5.2 THEMENAUSWAHL UND STATISTIK */"
CSS_START = "/* Z-PANEL 5.2 THEMENAUSWAHL START */"
CSS_END = "/* Z-PANEL 5.2 THEMENAUSWAHL ENDE */"

HTML = r'''
  <!-- Z-PANEL 5.2 THEMENAUSWAHL -->
  <dialog id="topic-dialog" class="topic-dialog">
    <form id="topic-form" method="dialog" class="topic-panel">
      <div class="topic-kicker">ZUSTAND · Themenauswahl</div>
      <h2>Was interessiert dich?</h2>
      <p>Wähle Themen aus. Die vorhandene Abspielfolge bleibt erhalten.</p>
      <div id="topic-options" class="topic-options"></div>
      <div class="topic-actions">
        <button id="topic-all-button" type="button">Alle Themen</button>
        <button id="topic-start-button" type="submit">Infoscreen starten →</button>
      </div>
    </form>
  </dialog>
'''

JS = r'''
/* Z-PANEL 5.2 THEMENAUSWAHL UND STATISTIK */
const zustandTopicSelection = {
  allArticles: [],
  selectedIds: new Set(),
  analytics: { endpoint: "", siteId: "zustand-infoscreen" },
  sessionId: ""
};

function zustandRandomId() {
  try {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
  } catch {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

async function zustandLoadAnalyticsConfig() {
  try {
    const response = await fetch(`analytics-config.json?v=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) return;
    const config = await response.json();
    zustandTopicSelection.analytics.endpoint = String(config.endpoint || "").trim();
    zustandTopicSelection.analytics.siteId = String(config.siteId || "zustand-infoscreen").trim();
  } catch {}
}

function zustandTrack(event, details = {}) {
  const endpoint = zustandTopicSelection.analytics.endpoint;
  if (!endpoint) return;
  if (!zustandTopicSelection.sessionId) {
    zustandTopicSelection.sessionId = zustandRandomId();
  }
  const body = JSON.stringify({
    event,
    siteId: zustandTopicSelection.analytics.siteId,
    sessionId: zustandTopicSelection.sessionId,
    timestamp: new Date().toISOString(),
    ...details
  });
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
    } else {
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
        mode: "cors"
      }).catch(() => {});
    }
  } catch {}
}

function zustandApplySelection() {
  const selected = zustandTopicSelection.selectedIds;
  if (!selected.size) {
    state.articles = [...zustandTopicSelection.allArticles];
  } else {
    const allowed = new Set();
    for (const article of zustandTopicSelection.allArticles) {
      const id = String(article.id || "");
      const explainerId = String(article.explainerId || "");
      if (selected.has(id) || selected.has(explainerId)) allowed.add(id);
    }
    state.articles = zustandTopicSelection.allArticles.filter(article =>
      allowed.has(String(article.id || ""))
    );
  }
  state.items = buildRotation(state.articles, state.editorialScreens, state.editorialEvery);
  state.currentIndex = 0;
  state.remainingMs = itemDurationSeconds(state.items[0]) * 1000;
}

function zustandShowTopicDialog() {
  const dialog = document.getElementById("topic-dialog");
  const options = document.getElementById("topic-options");
  const form = document.getElementById("topic-form");
  const allButton = document.getElementById("topic-all-button");

  const explainers = zustandTopicSelection.allArticles.filter(article =>
    String(article.contentType || "").trim().toLowerCase() === "explainer"
  );

  options.innerHTML = "";
  for (const explainer of explainers) {
    const id = String(explainer.id || "");
    if (!id) continue;
    const wrapper = document.createElement("label");
    wrapper.className = "topic-option";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = id;
    const text = document.createElement("span");
    text.textContent = String(explainer.selectionLabel || explainer.title || id).trim();
    wrapper.append(input, text);
    options.appendChild(wrapper);
  }

  allButton.addEventListener("click", () => {
    options.querySelectorAll('input[type="checkbox"]').forEach(input => input.checked = false);
  }, { once: true });

  form.addEventListener("submit", event => {
    event.preventDefault();
    zustandTopicSelection.selectedIds = new Set(
      Array.from(options.querySelectorAll('input[type="checkbox"]:checked')).map(input => input.value)
    );
    zustandApplySelection();
    zustandTrack("topic_selection_started", {
      topicIds: Array.from(zustandTopicSelection.selectedIds),
      topicCount: zustandTopicSelection.selectedIds.size,
      articleCount: state.articles.length
    });
    dialog.close();
    preloadItem(state.items[0]);
    preloadItem(state.items[1]);
    void renderItem({ animate: false });
    state.animationFrame = requestAnimationFrame(tick);
  }, { once: true });

  zustandTrack("screen_opened", { availableTopicCount: explainers.length });
  dialog.showModal();
}
'''

CSS = r'''
/* Z-PANEL 5.2 THEMENAUSWAHL START */
.topic-dialog {
  width: min(92vw, 720px);
  max-height: 88vh;
  border: 0;
  border-radius: 20px;
  padding: 0;
  color: #f5f5f0;
  background: #17201d;
  box-shadow: 0 30px 90px rgba(0, 0, 0, .5);
}
.topic-dialog::backdrop {
  background: rgba(4, 8, 7, .78);
  backdrop-filter: blur(6px);
}
.topic-panel { padding: clamp(22px, 5vw, 42px); }
.topic-kicker {
  margin-bottom: 8px;
  font-size: .78rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  opacity: .72;
}
.topic-panel h2 { margin: 0 0 8px; font-size: clamp(1.8rem, 5vw, 3rem); }
.topic-panel p { margin: 0 0 24px; line-height: 1.55; opacity: .82; }
.topic-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 10px;
}
.topic-option {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 10px 13px;
  border: 1px solid rgba(255, 255, 255, .13);
  border-radius: 12px;
  background: rgba(255, 255, 255, .045);
  cursor: pointer;
}
.topic-option:has(input:checked) {
  border-color: rgba(102, 196, 171, .8);
  background: rgba(75, 163, 150, .18);
}
.topic-option input { width: 19px; height: 19px; }
.topic-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 26px;
}
.topic-actions button {
  min-height: 44px;
  padding: 10px 16px;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
}
#topic-start-button { font-weight: 700; }
@media (max-width: 560px) {
  .topic-actions { flex-direction: column-reverse; }
  .topic-actions button { width: 100%; }
}
/* Z-PANEL 5.2 THEMENAUSWAHL ENDE */
'''


def find_root(start):
    for candidate in (start, *start.parents):
        if all((candidate / name).is_file() for name in ("index.html", "app.js", "styles.css")):
            return candidate
    raise FileNotFoundError("Kein Z-PANEL-Projektordner gefunden.")


def backup(project, files):
    target = project / "backups" / ("vor_z_panel_5_2_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    target.mkdir(parents=True, exist_ok=True)
    for file in files:
        if file.exists():
            shutil.copy2(file, target / file.name)
    return target


def patch_index(path):
    content = path.read_text(encoding="utf-8")
    if HTML_MARKER in content:
        return False
    content = content.replace("</body>", HTML + "\n</body>", 1)
    path.write_text(content, encoding="utf-8")
    return True


def patch_styles(path):
    content = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(CSS_START) + r".*?" + re.escape(CSS_END), re.S)
    updated = pattern.sub(CSS.strip(), content, count=1) if pattern.search(content) else content.rstrip() + "\n\n" + CSS.strip() + "\n"
    path.write_text(updated, encoding="utf-8")
    return updated != content


def patch_app(path):
    content = path.read_text(encoding="utf-8")
    if JS_MARKER in content:
        return False
    content = JS.strip() + "\n\n" + content

    old = "    state.articles = Array.isArray(data.articles) ? data.articles : [];"
    new = "    zustandTopicSelection.allArticles = Array.isArray(data.articles) ? data.articles : [];\n    state.articles = [...zustandTopicSelection.allArticles];"
    if old not in content:
        raise RuntimeError("Artikelübernahme in loadNews() nicht gefunden.")
    content = content.replace(old, new, 1)

    old_start = (
        "    preloadItem(state.items[0]);\n"
        "    preloadItem(state.items[1]);\n"
        "    state.remainingMs = itemDurationSeconds(state.items[0]) * 1000;\n"
        "    await renderItem({ animate: false });\n"
        "    state.animationFrame = requestAnimationFrame(tick);"
    )
    if old_start not in content:
        raise RuntimeError("Start der Rotation in loadNews() nicht gefunden.")
    content = content.replace(
        old_start,
        "    await zustandLoadAnalyticsConfig();\n    zustandShowTopicDialog();",
        1
    )

    marker = "function openArticle() {\n"
    if marker in content:
        content = content.replace(
            marker,
            marker +
            "  const trackedArticle = currentItem();\n"
            "  if (trackedArticle && !isEditorial(trackedArticle)) {\n"
            "    zustandTrack(\"article_opened\", {\n"
            "      articleId: String(trackedArticle.id || \"\"),\n"
            "      explainerId: String(trackedArticle.explainerId || \"\")\n"
            "    });\n"
            "  }\n",
            1
        )

    path.write_text(content, encoding="utf-8")
    return True


def main():
    project = find_root(Path(__file__).resolve().parent)
    index = project / "index.html"
    app = project / "app.js"
    styles = project / "styles.css"
    config = project / "analytics-config.json"
    saved = backup(project, [index, app, styles, config])

    patch_index(index)
    patch_app(app)
    patch_styles(styles)

    if not config.exists():
        config.write_text(json.dumps({
            "endpoint": "",
            "siteId": "zustand-infoscreen",
            "privacy": {
                "storesIp": False,
                "usesCookies": False,
                "sessionScope": "page-load"
            }
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Z-PANEL 5.2 vorbereitet.")
    print("Sicherung:", saved)
    print("Themenauswahl ist aktiv.")
    print("Statistik wird erst mit einem Endpoint in analytics-config.json versendet.")


if __name__ == "__main__":
    main()
