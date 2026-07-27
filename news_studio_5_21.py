#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.21 – grafische Abspielfolge.

Baut auf News Studio 5.20 auf.

Neu:
- eigener Reiter „Abspielfolge“
- Themenblöcke aus News + zugehöriger Grundlage
- unverbundene News als frei positionierbare Einzelblöcke
- Reihenfolge der Blöcke und der News innerhalb einer Gruppe steuerbar
- Zuordnung einer News zu einer Grundlage direkt in der Oberfläche
- lineare Vorschau der tatsächlichen Bildschirmfolge
- manuelle Reihenfolge wird beim Erzeugen von news.json übernommen
"""

import importlib.util
import json
import sys
import traceback
import types
from pathlib import Path
from tkinter import messagebox
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_20.py"
PLAYBACK_CONFIG = SCRIPT_DIR / "newsredaktion" / "playback_config.json"


def _write_start_error(exc: BaseException) -> Path:
    path = SCRIPT_DIR / "news_studio_5_21_startfehler.txt"
    content = (
        "ZUSTAND News Studio 5.21 konnte nicht gestartet werden.\n\n"
        f"Fehlertyp: {type(exc).__name__}\n"
        f"Fehler: {exc}\n\n"
        "Technische Details:\n"
        + traceback.format_exc()
    )
    try:
        path.write_text(content, encoding="utf-8")
    except OSError:
        pass
    return path


if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_20.py wurde nicht gefunden.\n"
        "Lege News Studio 5.21 in denselben Ordner wie Version 5.20."
    )

try:
    spec = importlib.util.spec_from_file_location(
        "news_studio_5_20_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.20 konnte nicht geladen werden.")

    base521 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base521
    spec.loader.exec_module(base521)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.21 – Startfehler",
            "Die Versionskette konnte nicht geladen werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Fehlerbericht:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base521.tk
ttk = base521.ttk


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _normal(value: object) -> str:
    return _clean(value).casefold()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _iter_modules(root_module):
    seen: set[int] = set()
    stack = [root_module]
    while stack:
        module = stack.pop()
        if not isinstance(module, types.ModuleType):
            continue
        identity = id(module)
        if identity in seen:
            continue
        seen.add(identity)
        yield module
        for value in vars(module).values():
            if isinstance(value, types.ModuleType):
                name = str(getattr(value, "__name__", ""))
                if "news_studio" in name or name.endswith("_base"):
                    stack.append(value)


def _discover_output_path() -> Path:
    for module in _iter_modules(base521):
        candidate = getattr(module, "OUTPUT", None)
        if candidate:
            try:
                return Path(candidate)
            except TypeError:
                pass
    return SCRIPT_DIR / "news.json"


OUTPUT_PATH = _discover_output_path()


class NewsStudio521(base521.NewsStudio520):
    def __init__(self):
        self._playback_ready = False
        self._playback_records: dict[str, dict[str, Any]] = {}
        self._playback_config: dict[str, Any] = {}
        self._playback_item_meta: dict[str, dict[str, str]] = {}
        self._playback_explainer_label_to_id: dict[str, str] = {}
        self._playback_refreshing = False

        super().__init__()
        self.title("ZUSTAND News Studio 5.21")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.20",
            "ZUSTAND News Studio 5.21",
        )

        self.after_idle(self._install_playback_tab)
        self.status_var.set(
            "News Studio 5.21 bereit │ Abspielfolge wird eingerichtet"
        )

    # ------------------------------------------------------------------
    # Datenmodell
    # ------------------------------------------------------------------
    def _load_records(self) -> dict[str, dict[str, Any]]:
        raw = self._all_article_records()
        records: dict[str, dict[str, Any]] = {}

        for identifier, record in raw.items():
            path = Path(record["path"])
            article = _read_json(path) or {}
            content_type = _clean(
                record.get("contentType") or article.get("contentType") or "news"
            ).casefold()
            records[identifier] = {
                "id": identifier,
                "title": _clean(record.get("title") or article.get("title") or identifier),
                "contentType": content_type,
                "explainerId": _clean(
                    record.get("explainerId") or article.get("explainerId")
                ),
                "path": str(path),
                "article": article,
            }
        return records

    def _load_playback_config(self) -> dict[str, Any]:
        value = _read_json(PLAYBACK_CONFIG)
        if value is None:
            value = {}
        if not isinstance(value.get("blockOrder"), list):
            value["blockOrder"] = []
        if not isinstance(value.get("groupNewsOrder"), dict):
            value["groupNewsOrder"] = {}
        value["version"] = 1
        return value

    def _save_playback_config(self) -> None:
        self._playback_config["version"] = 1
        _write_json(PLAYBACK_CONFIG, self._playback_config)

    def _is_explainer(self, record: dict[str, Any]) -> bool:
        return record.get("contentType") == "explainer"

    def _valid_model(self) -> tuple[list[str], dict[str, list[str]]]:
        records = self._playback_records
        explainers = {
            identifier: record
            for identifier, record in records.items()
            if self._is_explainer(record)
        }
        news = {
            identifier: record
            for identifier, record in records.items()
            if not self._is_explainer(record)
        }

        grouped: dict[str, list[str]] = {identifier: [] for identifier in explainers}
        ungrouped: list[str] = []

        for identifier, record in news.items():
            target = record.get("explainerId", "")
            if target in explainers:
                grouped[target].append(identifier)
            else:
                ungrouped.append(identifier)

        stored_group_order = self._playback_config.get("groupNewsOrder", {})
        for explainer_id, news_ids in grouped.items():
            preferred = [
                identifier
                for identifier in stored_group_order.get(explainer_id, [])
                if identifier in news_ids
            ]
            remaining = sorted(
                [identifier for identifier in news_ids if identifier not in preferred],
                key=lambda identifier: (
                    records[identifier]["title"].casefold(),
                    identifier,
                ),
            )
            grouped[explainer_id] = preferred + remaining

        valid_blocks = {
            *(f"explainer:{identifier}" for identifier in explainers),
            *(f"news:{identifier}" for identifier in ungrouped),
        }

        order = [
            block
            for block in self._playback_config.get("blockOrder", [])
            if block in valid_blocks
        ]

        missing_explainers = sorted(
            [
                identifier
                for identifier in explainers
                if f"explainer:{identifier}" not in order
            ],
            key=lambda identifier: (
                records[identifier]["title"].casefold(),
                identifier,
            ),
        )
        missing_news = sorted(
            [
                identifier
                for identifier in ungrouped
                if f"news:{identifier}" not in order
            ],
            key=lambda identifier: (
                records[identifier]["title"].casefold(),
                identifier,
            ),
        )

        order.extend(f"explainer:{identifier}" for identifier in missing_explainers)
        order.extend(f"news:{identifier}" for identifier in missing_news)

        self._playback_config["blockOrder"] = order
        self._playback_config["groupNewsOrder"] = {
            identifier: grouped[identifier]
            for identifier in sorted(grouped)
        }
        return order, grouped

    # ------------------------------------------------------------------
    # Reiter aufbauen
    # ------------------------------------------------------------------
    def _find_main_notebook(self):
        for name in ("notebook", "tabs", "main_notebook"):
            candidate = getattr(self, name, None)
            try:
                if candidate is not None and candidate.winfo_class() == "TNotebook":
                    return candidate
            except Exception:
                pass

        for widget in self._walk_widgets(self):
            try:
                if widget.winfo_class() == "TNotebook":
                    return widget
            except Exception:
                continue
        return None

    def _install_playback_tab(self) -> None:
        if self._playback_ready:
            return

        notebook = self._find_main_notebook()
        if notebook is None:
            self.status_var.set(
                "Der Reiter Abspielfolge konnte das Hauptregister nicht finden."
            )
            return

        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Abspielfolge")
        self.playback_tab = tab

        header = ttk.Frame(tab)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(
            header,
            text="Thematische Abspielfolge",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "Grundlagen bilden Themenblöcke. Ihre News laufen zuerst, die "
                "Grundlage automatisch zuletzt. Nicht zugeordnete News sind "
                "eigenständige Blöcke und können frei zwischen den Themen stehen."
            ),
            wraplength=1100,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Panedwindow(tab, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=3)
        body.add(right, weight=2)

        # Baumansicht
        tree_box = ttk.LabelFrame(left, text="Blöcke und Zuordnungen", padding=8)
        tree_box.pack(fill="both", expand=True)

        tree_frame = ttk.Frame(tree_box)
        tree_frame.pack(fill="both", expand=True)

        self.playback_tree = ttk.Treeview(
            tree_frame,
            columns=("typ", "id"),
            show="tree headings",
            selectmode="browse",
        )
        self.playback_tree.heading("#0", text="Titel / Abspielfolge")
        self.playback_tree.heading("typ", text="Typ")
        self.playback_tree.heading("id", text="ID")
        self.playback_tree.column("#0", width=500, minwidth=280, stretch=True)
        self.playback_tree.column("typ", width=105, minwidth=80, stretch=False)
        self.playback_tree.column("id", width=100, minwidth=80, stretch=False)
        self.playback_tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.playback_tree.yview,
        )
        scroll.pack(side="right", fill="y")
        self.playback_tree.configure(yscrollcommand=scroll.set)
        self.playback_tree.bind(
            "<<TreeviewSelect>>",
            self._on_playback_selection,
        )

        controls = ttk.Frame(left)
        controls.pack(fill="x", pady=(8, 0))

        ttk.Button(
            controls,
            text="Nach oben",
            command=lambda: self._move_selected(-1),
        ).pack(side="left")
        ttk.Button(
            controls,
            text="Nach unten",
            command=lambda: self._move_selected(1),
        ).pack(side="left", padx=(6, 12))

        ttk.Label(controls, text="News zuordnen:").pack(side="left")
        self.playback_assignment_var = tk.StringVar(value="")
        self.playback_assignment_combo = ttk.Combobox(
            controls,
            textvariable=self.playback_assignment_var,
            state="disabled",
            width=44,
        )
        self.playback_assignment_combo.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(6, 6),
        )
        self.playback_assignment_combo.bind(
            "<<ComboboxSelected>>",
            self._assign_selected_news,
        )

        ttk.Button(
            controls,
            text="Aktualisieren",
            command=self._refresh_playback_view,
        ).pack(side="right")

        # Rechte Vorschau
        preview_box = ttk.LabelFrame(
            right,
            text="Lineare Vorschau",
            padding=8,
        )
        preview_box.pack(fill="both", expand=True)

        self.playback_preview = tk.Text(
            preview_box,
            wrap="word",
            state="disabled",
            width=48,
            padx=8,
            pady=8,
        )
        self.playback_preview.pack(fill="both", expand=True)

        footer = ttk.Frame(right)
        footer.pack(fill="x", pady=(8, 0))
        self.playback_info_var = tk.StringVar(value="")
        ttk.Label(
            footer,
            textvariable=self.playback_info_var,
            justify="left",
            wraplength=440,
        ).pack(anchor="w")

        ttk.Button(
            footer,
            text="Reihenfolge speichern",
            command=self._save_playback_from_ui,
        ).pack(anchor="e", pady=(8, 0))

        self._playback_ready = True
        self._refresh_playback_view()
        self.status_var.set(
            "News Studio 5.21 bereit │ Abspielfolge aktiv"
        )

    # ------------------------------------------------------------------
    # Ansicht aktualisieren
    # ------------------------------------------------------------------
    def _refresh_playback_view(self) -> None:
        if not self._playback_ready or self._playback_refreshing:
            return

        self._playback_refreshing = True
        try:
            self._playback_records = self._load_records()
            self._playback_config = self._load_playback_config()
            block_order, grouped = self._valid_model()
            self._save_playback_config()

            tree = self.playback_tree
            for item_id in tree.get_children(""):
                tree.delete(item_id)
            self._playback_item_meta = {}

            explainers = [
                record
                for record in self._playback_records.values()
                if self._is_explainer(record)
            ]
            explainers.sort(key=lambda item: (item["title"].casefold(), item["id"]))

            no_assignment = "— Ohne Grundlage —"
            labels = [no_assignment]
            self._playback_explainer_label_to_id = {no_assignment: ""}
            for record in explainers:
                label = f'{record["id"]} — {record["title"]}'
                labels.append(label)
                self._playback_explainer_label_to_id[label] = record["id"]
            self.playback_assignment_combo.configure(values=tuple(labels))

            block_number = 0
            for block in block_order:
                kind, identifier = block.split(":", 1)
                record = self._playback_records.get(identifier)
                if record is None:
                    continue
                block_number += 1

                if kind == "explainer":
                    news_ids = grouped.get(identifier, [])
                    label = (
                        f'{block_number}. Themenblock: {record["title"]} '
                        f'({len(news_ids)} News)'
                    )
                    root_id = tree.insert(
                        "",
                        "end",
                        text=label,
                        values=("Grundlage", identifier),
                        open=True,
                    )
                    self._playback_item_meta[root_id] = {
                        "kind": "explainer-block",
                        "id": identifier,
                        "block": block,
                    }

                    for index, news_id in enumerate(news_ids, start=1):
                        news_record = self._playback_records[news_id]
                        child_id = tree.insert(
                            root_id,
                            "end",
                            text=f"{index}. {news_record['title']}",
                            values=("News", news_id),
                        )
                        self._playback_item_meta[child_id] = {
                            "kind": "grouped-news",
                            "id": news_id,
                            "explainerId": identifier,
                            "block": block,
                        }

                    marker_id = tree.insert(
                        root_id,
                        "end",
                        text=f"→ danach: {record['title']}",
                        values=("Grundlage", identifier),
                        tags=("fixed",),
                    )
                    self._playback_item_meta[marker_id] = {
                        "kind": "explainer-marker",
                        "id": identifier,
                        "block": block,
                    }
                else:
                    root_id = tree.insert(
                        "",
                        "end",
                        text=f'{block_number}. Einzelmeldung: {record["title"]}',
                        values=("News ohne Grundlage", identifier),
                    )
                    self._playback_item_meta[root_id] = {
                        "kind": "ungrouped-news",
                        "id": identifier,
                        "block": block,
                    }

            self._update_preview(block_order, grouped)
            self._update_playback_info(grouped)
            self._on_playback_selection()
        finally:
            self._playback_refreshing = False

    def _update_preview(
        self,
        block_order: list[str],
        grouped: dict[str, list[str]],
    ) -> None:
        lines: list[str] = []
        position = 0
        groups: list[dict[str, Any]] = []

        for block in block_order:
            kind, identifier = block.split(":", 1)
            record = self._playback_records.get(identifier)
            if record is None:
                continue

            if kind == "explainer":
                news_ids = grouped.get(identifier, [])
                block_positions: list[str] = []
                for news_id in news_ids:
                    position += 1
                    news = self._playback_records[news_id]
                    lines.append(f"{position:02d}  NEWS       {news['title']}")
                    block_positions.append(news_id)

                position += 1
                lines.append(f"{position:02d}  GRUNDLAGE  {record['title']}")
                block_positions.append(identifier)
                groups.append(
                    {
                        "explainerId": identifier,
                        "newsIds": news_ids,
                        "playbackIds": block_positions,
                    }
                )
                lines.append("")
            else:
                position += 1
                lines.append(f"{position:02d}  NEWS       {record['title']}")
                lines.append("")

        self.playback_preview.configure(state="normal")
        self.playback_preview.delete("1.0", "end")
        self.playback_preview.insert("1.0", "\n".join(lines).rstrip())
        self.playback_preview.configure(state="disabled")

    def _update_playback_info(self, grouped: dict[str, list[str]]) -> None:
        explainer_count = len(grouped)
        without_news = sum(1 for values in grouped.values() if not values)
        ungrouped = sum(
            1
            for block in self._playback_config.get("blockOrder", [])
            if block.startswith("news:")
        )
        thin = sum(1 for values in grouped.values() if len(values) == 1)
        recommended = sum(1 for values in grouped.values() if 2 <= len(values) <= 5)

        self.playback_info_var.set(
            f"{explainer_count} Grundlagenblöcke · "
            f"{recommended} mit 2–5 News · "
            f"{thin} mit nur 1 News · "
            f"{without_news} ohne News · "
            f"{ungrouped} News ohne Grundlage"
        )

    # ------------------------------------------------------------------
    # Auswahl, Zuordnung und Verschieben
    # ------------------------------------------------------------------
    def _selected_meta(self) -> tuple[str | None, dict[str, str] | None]:
        selection = self.playback_tree.selection()
        if not selection:
            return None, None
        item_id = selection[0]
        return item_id, self._playback_item_meta.get(item_id)

    def _on_playback_selection(self, _event=None) -> None:
        _item_id, meta = self._selected_meta()
        if not meta or meta["kind"] not in {"grouped-news", "ungrouped-news"}:
            self.playback_assignment_var.set("")
            self.playback_assignment_combo.configure(state="disabled")
            return

        news = self._playback_records.get(meta["id"], {})
        current = news.get("explainerId", "")
        selected_label = "— Ohne Grundlage —"
        for label, identifier in self._playback_explainer_label_to_id.items():
            if identifier == current:
                selected_label = label
                break

        self.playback_assignment_var.set(selected_label)
        self.playback_assignment_combo.configure(state="readonly")

    def _assign_selected_news(self, _event=None) -> None:
        _item_id, meta = self._selected_meta()
        if not meta or meta["kind"] not in {"grouped-news", "ungrouped-news"}:
            return

        news_id = meta["id"]
        record = self._playback_records.get(news_id)
        if record is None:
            return

        target = self._playback_explainer_label_to_id.get(
            self.playback_assignment_var.get(),
            "",
        )
        path = Path(record["path"])
        article = _read_json(path)
        if article is None:
            messagebox.showerror(
                "Zuordnung fehlgeschlagen",
                "Die Artikeldatei konnte nicht gelesen werden.",
                parent=self,
            )
            return

        old_target = _clean(article.get("explainerId"))
        if old_target == target:
            return

        if target:
            article["explainerId"] = target
            article["sequenceRole"] = "context-news"
        else:
            article.pop("explainerId", None)
            if article.get("sequenceRole") == "context-news":
                article.pop("sequenceRole", None)

        _write_json(path, article)

        # Bestehende Reihenfolge des Beitrags aus alten Gruppen entfernen.
        group_order = self._playback_config.setdefault("groupNewsOrder", {})
        for explainer_id, values in list(group_order.items()):
            group_order[explainer_id] = [
                identifier for identifier in values if identifier != news_id
            ]

        old_block = f"news:{news_id}"
        blocks = self._playback_config.setdefault("blockOrder", [])
        blocks[:] = [block for block in blocks if block != old_block]

        if target:
            group_order.setdefault(target, []).append(news_id)
        else:
            # Als Einzelmeldung möglichst an der Position des bisherigen Themenblocks.
            blocks.append(old_block)

        self._save_playback_config()
        self._refresh_playback_view()
        self.refresh_all()
        self.status_var.set("News-Zuordnung gespeichert.")

    def _move_selected(self, direction: int) -> None:
        item_id, meta = self._selected_meta()
        if not item_id or not meta:
            return

        kind = meta["kind"]
        changed = False

        if kind in {"explainer-block", "ungrouped-news"}:
            blocks = self._playback_config.get("blockOrder", [])
            block = meta["block"]
            if block not in blocks:
                return
            index = blocks.index(block)
            target = index + direction
            if not 0 <= target < len(blocks):
                return
            blocks[index], blocks[target] = blocks[target], blocks[index]
            changed = True

        elif kind == "grouped-news":
            explainer_id = meta["explainerId"]
            values = self._playback_config.get("groupNewsOrder", {}).get(
                explainer_id,
                [],
            )
            news_id = meta["id"]
            if news_id not in values:
                return
            index = values.index(news_id)
            target = index + direction
            if not 0 <= target < len(values):
                return
            values[index], values[target] = values[target], values[index]
            changed = True

        # Der feste Grundlagenmarker kann nicht verschoben werden.
        if not changed:
            return

        self._save_playback_config()
        selected_id = meta.get("id")
        selected_kind = meta.get("kind")
        self._refresh_playback_view()

        # Auswahl nach dem Neuaufbau wiederherstellen.
        for new_item, new_meta in self._playback_item_meta.items():
            if (
                new_meta.get("id") == selected_id
                and new_meta.get("kind") == selected_kind
            ):
                self.playback_tree.selection_set(new_item)
                self.playback_tree.see(new_item)
                break

    def _save_playback_from_ui(self) -> None:
        self._save_playback_config()
        messagebox.showinfo(
            "Abspielfolge gespeichert",
            "Die manuelle Reihenfolge wurde gespeichert und wird beim nächsten "
            "Erzeugen von news.json verwendet.",
            parent=self,
        )
        self.status_var.set("Abspielfolge gespeichert.")

    # ------------------------------------------------------------------
    # Manuelle Reihenfolge auf news.json anwenden
    # ------------------------------------------------------------------
    def _apply_manual_order_to_news_json(self) -> dict[str, Any]:
        payload = _read_json(OUTPUT_PATH)
        if payload is None:
            raise ValueError(f"{OUTPUT_PATH.name} ist kein gültiges JSON-Objekt.")

        raw_articles = payload.get("articles")
        if not isinstance(raw_articles, list):
            raise ValueError("news.json enthält keine Artikelliste.")

        articles = [article for article in raw_articles if isinstance(article, dict)]
        by_id: dict[str, dict[str, Any]] = {}
        original_order: list[str] = []
        for article in articles:
            identifier = _clean(article.get("id"))
            if not identifier or identifier in by_id:
                continue
            by_id[identifier] = article
            original_order.append(identifier)

        # Das aktuelle Modell erneut aus den Artikeldateien bilden.
        self._playback_records = self._load_records()
        self._playback_config = self._load_playback_config()
        block_order, grouped = self._valid_model()
        self._save_playback_config()

        ordered_ids: list[str] = []
        playback_groups: list[dict[str, Any]] = []

        def add(identifier: str) -> None:
            if identifier in by_id and identifier not in ordered_ids:
                ordered_ids.append(identifier)

        for block_index, block in enumerate(block_order, start=1):
            kind, identifier = block.split(":", 1)
            if kind == "explainer":
                news_ids = [
                    news_id for news_id in grouped.get(identifier, []) if news_id in by_id
                ]
                for news_id in news_ids:
                    add(news_id)
                add(identifier)
                playback_ids = [
                    item
                    for item in [*news_ids, identifier]
                    if item in by_id
                ]
                playback_groups.append(
                    {
                        "explainerId": identifier,
                        "order": block_index,
                        "newsIds": news_ids,
                        "newsCount": len(news_ids),
                        "playbackIds": playback_ids,
                        "status": (
                            "recommended"
                            if 2 <= len(news_ids) <= 5
                            else "thin"
                            if len(news_ids) == 1
                            else "unlinked"
                            if len(news_ids) == 0
                            else "large"
                        ),
                    }
                )
            else:
                add(identifier)

        # Sicherheitsnetz für Beiträge, die noch nicht im Studio-Modell lagen.
        for identifier in original_order:
            add(identifier)

        ordered_articles = [by_id[identifier] for identifier in ordered_ids]
        payload["articles"] = ordered_articles
        payload["articleCount"] = len(ordered_articles)
        payload["playbackOrder"] = ordered_ids
        payload["playbackGroups"] = playback_groups
        payload["playbackPolicy"] = {
            "mode": "manual-block-order",
            "description": (
                "Manuell geordnete Themenblöcke. News einer Grundlage laufen "
                "zuerst; anschließend folgt die Grundlage. News ohne Grundlage "
                "laufen als frei positionierte Einzelblöcke."
            ),
            "source": "newsredaktion/playback_config.json",
            "recommendedNewsPerExplainer": {"min": 2, "max": 5},
        }
        payload["contentSchema"] = max(
            int(payload.get("contentSchema", 0) or 0),
            6,
        )
        payload.pop("playbackWarnings", None)

        _write_json(OUTPUT_PATH, payload)
        return {
            "total": len(ordered_ids),
            "groups": len(playback_groups),
            "standalone": sum(
                1 for block in block_order if block.startswith("news:")
            ),
        }

    def run_generator(self):
        super().run_generator()
        if not OUTPUT_PATH.exists():
            return

        try:
            stats = self._apply_manual_order_to_news_json()
        except Exception as exc:
            self.status_var.set(
                f"news.json erzeugt, manuelle Abspielfolge fehlgeschlagen: {exc}"
            )
            return

        self.status_var.set(
            f'news.json erzeugt │ {stats["total"]} Beiträge │ '
            f'{stats["groups"]} Themenblöcke │ '
            f'{stats["standalone"]} Einzelmeldungen'
        )

        if hasattr(self, "generator_log"):
            try:
                self.generator_log.configure(state="normal")
                self.generator_log.insert(
                    "end",
                    "\n\nMANUELLE ABSPIELFOLGE 5.21\n"
                    f'✓ {stats["total"]} Beiträge manuell geordnet\n'
                    f'✓ {stats["groups"]} Themenblöcke\n'
                    f'✓ {stats["standalone"]} frei positionierte Einzelmeldungen\n'
                    "✓ Grundlage jeweils automatisch am Gruppenende\n"
                    "✓ playbackOrder und articles-Array aktualisiert\n",
                )
                self.generator_log.configure(state="disabled")
                self.generator_log.see("end")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Nach Änderungen anderer Reiter aktualisieren
    # ------------------------------------------------------------------
    def refresh_all(self):
        result = super().refresh_all()
        if getattr(self, "_playback_ready", False):
            self.after_idle(self._refresh_playback_view)
        return result


def main() -> None:
    try:
        app = NewsStudio521()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.21 – Startfehler",
                "Das Studio wurde wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
