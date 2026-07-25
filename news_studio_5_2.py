#!/usr/bin/env python3
from __future__ import annotations

"""
ZUSTAND News Studio 5.2

Ergänzt News Studio 5.1 um eine lokale, nicht öffentliche Kontaktverwaltung.
Die stabile Version 5.1 bleibt die Basis und muss im selben Ordner liegen.

Wichtig:
- Kontaktdaten werden NICHT im Z-PANEL-Projekt, in Artikeldateien oder news.json gespeichert.
- Unter Windows liegt die private Datenbank standardmäßig unter
  %LOCALAPPDATA%\\ZUSTAND\\NewsStudio\\kontakte.json.
- Rechercheimporte dürfen ein optionales Feld "contacts" enthalten. 5.2 übernimmt
  diese Kontakte in die private Datenbank und verknüpft sie über die Quellen-URL.
"""

import hashlib
import importlib.util
import json
import os
import re
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CANDIDATES = (
    SCRIPT_DIR / "news_studio_5_1.py",
    SCRIPT_DIR / "news_studio_5_1(1).py",
)
BASE_SCRIPT = next((path for path in BASE_CANDIDATES if path.exists()), None)

if BASE_SCRIPT is None:
    raise SystemExit(
        "news_studio_5_1.py wurde nicht gefunden.\n"
        "Lege news_studio_5_2.py in denselben Ordner wie news_studio_5_1.py."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_1_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("news_studio_5_1.py konnte nicht geladen werden.")

base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

tk = base.tk
ttk = base.ttk
messagebox = base.messagebox
filedialog = base.filedialog

CONTACT_TYPES = ("Autor*in", "Wissenschaft", "Pressestelle", "Projektleitung")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def private_data_dir() -> Path:
    """Liefert bewusst einen Speicherort außerhalb des öffentlichen Repositories."""
    override = os.environ.get("ZUSTAND_PRIVATE_DATA", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if root:
            return Path(root) / "ZUSTAND" / "NewsStudio"

    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "zustand" / "news-studio"
    return Path.home() / ".local" / "share" / "zustand" / "news-studio"


PRIVATE_DIR = private_data_dir()
CONTACT_DB_PATH = PRIVATE_DIR / "kontakte.json"


def empty_contact_db() -> dict[str, Any]:
    return {
        "version": 1,
        "updatedAt": "",
        "contacts": {},
        "articleLinks": {},
    }


def read_contact_db() -> tuple[dict[str, Any], str]:
    """Liest die private Datenbank; beschädigte Dateien werden sicher beiseitegelegt."""
    if not CONTACT_DB_PATH.exists():
        return empty_contact_db(), ""

    try:
        data = json.loads(CONTACT_DB_PATH.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Wurzel muss ein JSON-Objekt sein")
    except Exception as exc:
        PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = CONTACT_DB_PATH.with_name(f"kontakte_beschaedigt_{stamp}.json")
        try:
            CONTACT_DB_PATH.replace(backup)
            detail = f"Beschädigte Datei wurde gesichert als: {backup}"
        except OSError:
            detail = "Beschädigte Datei konnte nicht automatisch umbenannt werden."
        return empty_contact_db(), f"Kontaktdatei konnte nicht gelesen werden: {exc}\n{detail}"

    contacts = data.get("contacts")
    links = data.get("articleLinks")
    if not isinstance(contacts, dict):
        contacts = {}
    if not isinstance(links, dict):
        links = {}

    data["version"] = 1
    data["contacts"] = contacts
    data["articleLinks"] = links
    data.setdefault("updatedAt", "")
    return data, ""


def write_contact_db(data: dict[str, Any]) -> None:
    """Schreibt atomar, damit ein Programmabbruch die Datenbank nicht zerstört."""
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    data["version"] = 1
    data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    temporary = CONTACT_DB_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(CONTACT_DB_PATH)


def normalize_source_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            return raw.lower().rstrip("/")
        clean = urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            parts.query,
            "",
        ))
        return clean.lower()
    except Exception:
        return raw.lower().rstrip("/")


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def contact_id_for(contact: dict[str, Any]) -> str:
    identity = "|".join((
        clean_text(contact.get("email")).lower(),
        clean_text(contact.get("profileUrl")).lower(),
        clean_text(contact.get("name")).lower(),
        clean_text(contact.get("institution")).lower(),
    ))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    name = clean_text(contact.get("name")) or "kontakt"
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()
                  .replace("ä", "ae").replace("ö", "oe")
                  .replace("ü", "ue").replace("ß", "ss")).strip("_")
    return f"{slug[:28] or 'kontakt'}_{digest}"


def normalize_contact(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    aliases = {
        "name": ("name", "contactName"),
        "role": ("role", "contactRole"),
        "institution": ("institution", "contactInstitution"),
        "country": ("country", "contactCountry"),
        "email": ("email", "contactEmail"),
        "phone": ("phone", "contactPhone"),
        "profileUrl": ("profileUrl", "contactUrl"),
        "contactSourceUrl": ("contactSourceUrl", "verificationUrl"),
        "contactType": ("contactType", "type"),
        "notes": ("notes", "contactNote"),
    }

    result: dict[str, Any] = {}
    for target, candidates in aliases.items():
        value = ""
        for candidate in candidates:
            if raw.get(candidate) not in (None, ""):
                value = clean_text(raw.get(candidate))
                break
        result[target] = value

    preferred = raw.get("preferred", raw.get("preferredContact", False))
    result["preferred"] = bool(preferred)

    if result["contactType"] not in CONTACT_TYPES:
        lowered = result["contactType"].lower()
        mapping = {
            "autor": "Autor*in",
            "autor*in": "Autor*in",
            "author": "Autor*in",
            "wissenschaftler*in": "Wissenschaft",
            "wissenschaft": "Wissenschaft",
            "researcher": "Wissenschaft",
            "press": "Pressestelle",
            "pressestelle": "Pressestelle",
            "media": "Pressestelle",
            "projektleitung": "Projektleitung",
            "project lead": "Projektleitung",
        }
        result["contactType"] = mapping.get(lowered, "Wissenschaft")

    if not result["name"] and not result["institution"]:
        return None
    if result["email"] and not EMAIL_RE.match(result["email"]):
        # Nicht verwerfen: sichtbar im Editor lassen, aber als Prüfhinweis markieren.
        note = "E-Mail-Adresse beim Import formal auffällig – bitte prüfen."
        result["notes"] = f"{result['notes']} {note}".strip()

    return result


def merge_contact(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key in (
        "name", "role", "institution", "country", "email", "phone",
        "profileUrl", "contactSourceUrl", "contactType",
    ):
        incoming_value = clean_text(incoming.get(key))
        if incoming_value and not clean_text(merged.get(key)):
            merged[key] = incoming_value

    if incoming.get("preferred"):
        merged["preferred"] = True
    else:
        merged.setdefault("preferred", False)

    old_notes = clean_text(merged.get("notes"))
    new_notes = clean_text(incoming.get("notes"))
    if new_notes and new_notes not in old_notes:
        merged["notes"] = (old_notes + "\n" + new_notes).strip()
    else:
        merged["notes"] = old_notes
    return merged


def contacts_from_article(raw: dict[str, Any]) -> list[dict[str, Any]]:
    contacts = raw.get("contacts", [])
    if isinstance(contacts, dict):
        contacts = [contacts]
    if not isinstance(contacts, list):
        contacts = []

    # Auch eine ältere flache Kontaktstruktur wird akzeptiert.
    if not contacts and any(key in raw for key in (
        "contactName", "contactEmail", "contactInstitution", "contactUrl"
    )):
        contacts = [raw]

    result = []
    for item in contacts:
        normalized = normalize_contact(item)
        if normalized:
            result.append(normalized)
    return result


def sync_contacts_from_import(path: Path, db: dict[str, Any]) -> dict[str, int]:
    """Übernimmt Kontakte, ohne die importierten Artikeldateien zu verändern."""
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    articles = raw.get("articles", []) if isinstance(raw, dict) else []
    if not isinstance(articles, list):
        raise ValueError("Die Recherche-Datei enthält keine gültige Artikelliste.")

    contacts_db = db.setdefault("contacts", {})
    links_db = db.setdefault("articleLinks", {})
    new_count = 0
    updated_count = 0
    link_count = 0

    for article in articles:
        if not isinstance(article, dict):
            continue
        contacts = contacts_from_article(article)
        if not contacts:
            continue

        source_url = clean_text(article.get("sourceUrl"))
        source_key = normalize_source_url(source_url)
        if not source_key:
            # Fallback nur für lokale Zuordnung, falls eine Altdatei keine URL enthält.
            title_key = clean_text(article.get("title")).lower()
            source_key = f"title:{title_key}" if title_key else ""
        if not source_key:
            continue

        link = links_db.setdefault(source_key, {
            "sourceUrl": source_url,
            "title": clean_text(article.get("title")),
            "contactIds": [],
        })
        if not isinstance(link, dict):
            link = {"sourceUrl": source_url, "title": clean_text(article.get("title")), "contactIds": []}
            links_db[source_key] = link
        link["sourceUrl"] = source_url or clean_text(link.get("sourceUrl"))
        link["title"] = clean_text(article.get("title")) or clean_text(link.get("title"))
        contact_ids = link.setdefault("contactIds", [])
        if not isinstance(contact_ids, list):
            contact_ids = []
            link["contactIds"] = contact_ids

        for contact in contacts:
            contact_id = contact_id_for(contact)
            if contact_id in contacts_db and isinstance(contacts_db[contact_id], dict):
                before = json.dumps(contacts_db[contact_id], ensure_ascii=False, sort_keys=True)
                contacts_db[contact_id] = merge_contact(contacts_db[contact_id], contact)
                after = json.dumps(contacts_db[contact_id], ensure_ascii=False, sort_keys=True)
                if before != after:
                    updated_count += 1
            else:
                contacts_db[contact_id] = contact
                new_count += 1

            if contact_id not in contact_ids:
                contact_ids.append(contact_id)
                link_count += 1

    return {"new": new_count, "updated": updated_count, "links": link_count}


class NewsStudio52(base.NewsStudio):
    def __init__(self):
        self.contact_db, db_warning = read_contact_db()
        self.current_contact_id: str | None = None
        self.contact_paths_by_item: dict[str, str] = {}
        super().__init__()

        self.title("ZUSTAND News Studio 5.2")
        self._replace_widget_text("ZUSTAND News Studio 5.1", "ZUSTAND News Studio 5.2")
        self._add_contacts_tab()
        self._add_article_contact_box()
        self._add_article_contacts_button()
        self.refresh_contacts()
        self._update_article_contact_badge()
        self.status_var.set(
            "News Studio 5.2 bereit │ private Kontaktverwaltung aktiv"
        )

        if db_warning:
            self.after(350, lambda: messagebox.showwarning(
                "Kontaktdatei zurückgesetzt", db_warning, parent=self
            ))

    def _replace_widget_text(self, old: str, new: str) -> None:
        def walk(widget):
            try:
                if widget.cget("text") == old:
                    widget.configure(text=new)
            except Exception:
                pass
            for child in widget.winfo_children():
                walk(child)
        walk(self)

    def _find_widget_by_text(self, text: str):
        def walk(widget):
            try:
                if widget.cget("text") == text:
                    return widget
            except Exception:
                pass
            for child in widget.winfo_children():
                found = walk(child)
                if found is not None:
                    return found
            return None
        return walk(self)

    def _add_contacts_tab(self) -> None:
        self.contacts_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.contacts_tab, text="Kontakte")

        outer = ttk.Panedwindow(self.contacts_tab, orient="horizontal")
        outer.pack(fill="both", expand=True, padx=10, pady=10)
        left = ttk.Frame(outer, padding=6)
        right = ttk.Frame(outer, padding=8)
        outer.add(left, weight=2)
        outer.add(right, weight=3)

        ttk.Label(left, text="Interne Interviewkontakte",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(
            left,
            text="Nur lokal gespeichert – nicht Bestandteil von news.json.",
            wraplength=430,
        ).pack(anchor="w", pady=(0, 5))

        self.contact_list = ttk.Treeview(
            left,
            columns=("preferred", "name", "institution", "type", "links"),
            show="headings",
            selectmode="browse",
        )
        headings = {
            "preferred": "★",
            "name": "Name",
            "institution": "Institution",
            "type": "Typ",
            "links": "Meldungen",
        }
        for key, title in headings.items():
            self.contact_list.heading(key, text=title)
        self.contact_list.column("preferred", width=35, anchor="center", stretch=False)
        self.contact_list.column("name", width=180, anchor="w")
        self.contact_list.column("institution", width=190, anchor="w")
        self.contact_list.column("type", width=95, anchor="w", stretch=False)
        self.contact_list.column("links", width=70, anchor="center", stretch=False)
        self.contact_list.pack(fill="both", expand=True, pady=6)
        self.contact_list.bind("<<TreeviewSelect>>", self.load_selected_contact)
        self.contact_list.bind("<Double-1>", self.load_selected_contact)

        left_buttons = ttk.Frame(left)
        left_buttons.pack(fill="x")
        ttk.Button(left_buttons, text="Neu", command=self.new_contact).pack(side="left")
        ttk.Button(
            left_buttons, text="Kontakte aus Recherche-Datei",
            command=self.import_contacts_only,
        ).pack(side="left", padx=5)
        ttk.Button(
            left_buttons, text="Aktualisieren", command=self.refresh_contacts
        ).pack(side="left")

        self.contact_vars = {
            "name": tk.StringVar(),
            "role": tk.StringVar(),
            "institution": tk.StringVar(),
            "country": tk.StringVar(),
            "email": tk.StringVar(),
            "phone": tk.StringVar(),
            "profileUrl": tk.StringVar(),
            "contactSourceUrl": tk.StringVar(),
            "contactType": tk.StringVar(value="Wissenschaft"),
        }
        self.contact_preferred_var = tk.BooleanVar(value=False)

        ttk.Label(right, text="Kontakt bearbeiten",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            right,
            text=f"Private Datei: {CONTACT_DB_PATH}",
            font=("Consolas", 9),
            wraplength=710,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        form = ttk.Frame(right)
        form.pack(fill="both", expand=True)

        def row(label: str, key: str) -> None:
            frame = ttk.Frame(form)
            frame.pack(fill="x", pady=3)
            ttk.Label(frame, text=label, width=22).pack(side="left")
            ttk.Entry(frame, textvariable=self.contact_vars[key]).pack(
                side="left", fill="x", expand=True
            )

        row("Name", "name")
        row("Rolle/Funktion", "role")
        row("Institution", "institution")
        row("Land", "country")
        row("E-Mail", "email")
        row("Telefon", "phone")
        row("Profil-URL", "profileUrl")
        row("Nachweis-/Kontaktseite", "contactSourceUrl")

        type_row = ttk.Frame(form)
        type_row.pack(fill="x", pady=3)
        ttk.Label(type_row, text="Kontakttyp", width=22).pack(side="left")
        ttk.Combobox(
            type_row,
            textvariable=self.contact_vars["contactType"],
            values=CONTACT_TYPES,
            state="readonly",
        ).pack(side="left", fill="x", expand=True)

        preferred_row = ttk.Frame(form)
        preferred_row.pack(fill="x", pady=3)
        ttk.Label(preferred_row, text="Bevorzugt", width=22).pack(side="left")
        ttk.Checkbutton(
            preferred_row,
            text="Erste Wahl für die Interviewanfrage",
            variable=self.contact_preferred_var,
        ).pack(side="left")

        ttk.Label(form, text="Notizen", width=22).pack(anchor="w", pady=(8, 2))
        self.contact_notes = tk.Text(form, height=6, wrap="word")
        self.contact_notes.pack(fill="x")

        association_box = ttk.LabelFrame(form, text="Verknüpfte Meldungen", padding=8)
        association_box.pack(fill="both", expand=True, pady=(10, 4))
        self.contact_links_text = tk.Text(
            association_box, height=6, wrap="word", state="disabled"
        )
        self.contact_links_text.pack(fill="both", expand=True)

        actionbar = ttk.Frame(right)
        actionbar.pack(fill="x", pady=(8, 0))
        ttk.Button(actionbar, text="Speichern", command=self.save_contact).pack(side="left")
        ttk.Button(
            actionbar, text="Mit aktuellem Beitrag verknüpfen",
            command=self.link_contact_to_current_article,
        ).pack(side="left", padx=5)
        ttk.Button(
            actionbar, text="E-Mail kopieren", command=self.copy_contact_email
        ).pack(side="left", padx=(0, 5))
        ttk.Button(
            actionbar, text="Profil öffnen", command=self.open_contact_profile
        ).pack(side="left")
        ttk.Button(
            actionbar, text="Löschen", command=self.delete_contact
        ).pack(side="right")

    def _add_article_contact_box(self) -> None:
        article_label = self._find_widget_by_text("Artikeltext")
        if article_label is None:
            return
        parent = article_label.master
        box = ttk.LabelFrame(parent, text="Interview und Kontakt", padding=8)
        try:
            box.pack(fill="x", pady=(8, 2), before=article_label)
        except tk.TclError:
            box.pack(fill="x", pady=(8, 2))
        self.article_contact_summary_var = tk.StringVar(
            value="Noch kein Kontakt mit diesem Beitrag verknüpft."
        )
        ttk.Label(
            box,
            textvariable=self.article_contact_summary_var,
            wraplength=760,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            box, text="Kontakte öffnen", command=self.open_current_article_contacts
        ).pack(side="right", padx=(8, 0))

    def _add_article_contacts_button(self) -> None:
        refresh_button = self._find_widget_by_text("Aktualisieren")
        if refresh_button is None:
            return
        try:
            ttk.Button(
                refresh_button.master,
                text="Kontakte",
                command=self.open_current_article_contacts,
            ).pack(side="left", padx=(0, 5))
        except Exception:
            pass

    def build_research_prompt(self, period: str) -> str:
        prompt = super().build_research_prompt(period)
        extension = (
            "\n\nErmittle außerdem für jede Meldung nach Möglichkeit eine konkret "
            "ansprechbare Person. Bevorzuge eine Autorin oder einen Autor der "
            "Veröffentlichung; falls keine öffentlich ausgewiesene berufliche "
            "Kontaktmöglichkeit vorliegt, nutze die zuständige wissenschaftliche "
            "Pressestelle oder Projektleitung. Verwende ausschließlich auf offiziellen "
            "Institutionsseiten öffentlich veröffentlichte berufliche Kontaktdaten. "
            "E-Mail-Adressen oder Telefonnummern niemals erraten. Nicht sicher "
            "ermittelbare Felder bleiben leer.\n\n"
            "Erweitere jeden Artikel optional um dieses Feld:\n"
            '"contacts": [\n'
            "  {\n"
            '    "name": "...",\n'
            '    "role": "...",\n'
            '    "institution": "...",\n'
            '    "country": "...",\n'
            '    "email": "...",\n'
            '    "phone": "...",\n'
            '    "profileUrl": "https://...",\n'
            '    "contactSourceUrl": "https://...",\n'
            '    "contactType": "Autor*in|Wissenschaft|Pressestelle|Projektleitung",\n'
            '    "preferred": true,\n'
            '    "notes": "Warum diese Person geeignet ist und was vor der Anfrage zu prüfen ist."\n'
            "  }\n"
            "]\n\n"
            "Diese Kontaktangaben dienen ausschließlich der internen Redaktion. "
            "News Studio 5.2 speichert sie lokal außerhalb des öffentlichen "
            "Z-PANEL-Projektordners."
        )
        return prompt + extension

    def import_research_file(self):
        """Nutzt den bewährten 5.1-Import und übernimmt danach Kontakte privat."""
        chosen: dict[str, str] = {"path": ""}
        original_dialog = base.filedialog.askopenfilename

        def capture_dialog(*args, **kwargs):
            selected = original_dialog(*args, **kwargs)
            chosen["path"] = selected or ""
            return selected

        base.filedialog.askopenfilename = capture_dialog
        try:
            result = super().import_research_file()
        finally:
            base.filedialog.askopenfilename = original_dialog

        if chosen["path"]:
            self._sync_contacts_path(Path(chosen["path"]), show_result=True)
        return result

    def import_contacts_only(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Recherche-Datei mit Kontakten auswählen",
            filetypes=(("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")),
        )
        if path:
            self._sync_contacts_path(Path(path), show_result=True)

    def _sync_contacts_path(self, path: Path, show_result: bool) -> None:
        try:
            result = sync_contacts_from_import(path, self.contact_db)
            write_contact_db(self.contact_db)
        except Exception as exc:
            messagebox.showerror(
                "Kontakte konnten nicht übernommen werden",
                f"{path.name}\n\n{exc}",
                parent=self,
            )
            return

        self.refresh_contacts()
        self._update_article_contact_badge()
        total = result["new"] + result["updated"]
        self.status_var.set(
            f"Kontakte übernommen: {result['new']} neu, "
            f"{result['updated']} ergänzt, {result['links']} Verknüpfung(en)"
        )
        if show_result:
            messagebox.showinfo(
                "Interne Kontakte übernommen",
                (
                    f"Neue Kontakte: {result['new']}\n"
                    f"Ergänzte Kontakte: {result['updated']}\n"
                    f"Neue Artikel-Verknüpfungen: {result['links']}\n\n"
                    f"Private Datei:\n{CONTACT_DB_PATH}\n\n"
                    "Artikeldateien und news.json wurden nicht um Kontaktdaten erweitert."
                ),
                parent=self,
            )

    def _contact_link_count(self, contact_id: str) -> int:
        count = 0
        for link in self.contact_db.get("articleLinks", {}).values():
            if isinstance(link, dict) and contact_id in link.get("contactIds", []):
                count += 1
        return count

    def refresh_contacts(self) -> None:
        if not hasattr(self, "contact_list"):
            return
        for item in self.contact_list.get_children():
            self.contact_list.delete(item)
        self.contact_paths_by_item.clear()

        contacts = self.contact_db.get("contacts", {})
        rows = []
        for contact_id, contact in contacts.items():
            if not isinstance(contact, dict):
                continue
            rows.append((
                0 if contact.get("preferred") else 1,
                clean_text(contact.get("name")).lower(),
                contact_id,
                contact,
            ))
        rows.sort()

        for _, __, contact_id, contact in rows:
            item = self.contact_list.insert(
                "",
                "end",
                values=(
                    "★" if contact.get("preferred") else "",
                    clean_text(contact.get("name")),
                    clean_text(contact.get("institution")),
                    clean_text(contact.get("contactType")),
                    self._contact_link_count(contact_id),
                ),
            )
            self.contact_paths_by_item[item] = contact_id

    def new_contact(self) -> None:
        self.current_contact_id = None
        for var in self.contact_vars.values():
            var.set("")
        self.contact_vars["contactType"].set("Wissenschaft")
        self.contact_preferred_var.set(False)
        self.contact_notes.delete("1.0", "end")
        self._set_links_text("Noch keine Meldung verknüpft.")
        self.status_var.set("Neuer interner Kontakt")

    def load_selected_contact(self, _event=None) -> None:
        selection = self.contact_list.selection()
        if not selection:
            return
        contact_id = self.contact_paths_by_item.get(selection[0])
        contact = self.contact_db.get("contacts", {}).get(contact_id, {})
        if not contact_id or not isinstance(contact, dict):
            return

        self.current_contact_id = contact_id
        for key, var in self.contact_vars.items():
            var.set(clean_text(contact.get(key)))
        self.contact_preferred_var.set(bool(contact.get("preferred")))
        self.contact_notes.delete("1.0", "end")
        self.contact_notes.insert("1.0", str(contact.get("notes", "")))
        self._refresh_contact_links_text(contact_id)
        self.status_var.set(
            f"Kontakt geöffnet: {clean_text(contact.get('name')) or contact_id}"
        )

    def _contact_payload_from_form(self) -> dict[str, Any]:
        payload = {key: clean_text(var.get()) for key, var in self.contact_vars.items()}
        payload["preferred"] = bool(self.contact_preferred_var.get())
        payload["notes"] = self.contact_notes.get("1.0", "end").strip()
        if not payload["name"] and not payload["institution"]:
            raise ValueError("Bitte mindestens Name oder Institution eintragen.")
        if payload["email"] and not EMAIL_RE.match(payload["email"]):
            raise ValueError("Die E-Mail-Adresse ist formal ungültig.")
        for key in ("profileUrl", "contactSourceUrl"):
            value = payload[key]
            if value and not base.valid_url(value):
                raise ValueError(f"{key} enthält keine gültige Webadresse.")
        return payload

    def save_contact(self) -> str | None:
        try:
            payload = self._contact_payload_from_form()
        except ValueError as exc:
            messagebox.showwarning("Kontakt unvollständig", str(exc), parent=self)
            return None

        contact_id = self.current_contact_id or contact_id_for(payload)
        self.contact_db.setdefault("contacts", {})[contact_id] = payload
        try:
            write_contact_db(self.contact_db)
        except Exception as exc:
            messagebox.showerror("Kontakt konnte nicht gespeichert werden", str(exc), parent=self)
            return None

        self.current_contact_id = contact_id
        self.refresh_contacts()
        self._select_contact(contact_id)
        self._update_article_contact_badge()
        self.status_var.set(f"Kontakt gespeichert: {payload['name'] or payload['institution']}")
        return contact_id

    def delete_contact(self) -> None:
        contact_id = self.current_contact_id
        if not contact_id:
            return
        contact = self.contact_db.get("contacts", {}).get(contact_id, {})
        name = clean_text(contact.get("name")) or contact_id
        if not messagebox.askyesno(
            "Kontakt löschen",
            f"Soll der interne Kontakt „{name}“ einschließlich aller Verknüpfungen gelöscht werden?",
            parent=self,
        ):
            return

        self.contact_db.get("contacts", {}).pop(contact_id, None)
        for link in self.contact_db.get("articleLinks", {}).values():
            if not isinstance(link, dict):
                continue
            ids = link.get("contactIds", [])
            if isinstance(ids, list):
                link["contactIds"] = [item for item in ids if item != contact_id]
        write_contact_db(self.contact_db)
        self.new_contact()
        self.refresh_contacts()
        self._update_article_contact_badge()
        self.status_var.set(f"Kontakt gelöscht: {name}")

    def _set_links_text(self, text: str) -> None:
        if not hasattr(self, "contact_links_text"):
            return
        self.contact_links_text.configure(state="normal")
        self.contact_links_text.delete("1.0", "end")
        self.contact_links_text.insert("1.0", text)
        self.contact_links_text.configure(state="disabled")

    def _refresh_contact_links_text(self, contact_id: str) -> None:
        lines = []
        for link in self.contact_db.get("articleLinks", {}).values():
            if not isinstance(link, dict) or contact_id not in link.get("contactIds", []):
                continue
            title = clean_text(link.get("title")) or "Meldung ohne Titel"
            source = clean_text(link.get("sourceUrl"))
            lines.append(f"• {title}\n  {source}".rstrip())
        self._set_links_text("\n\n".join(lines) if lines else "Noch keine Meldung verknüpft.")

    def _current_article_source(self) -> tuple[str, str]:
        if not hasattr(self, "article_vars"):
            return "", ""
        source_url = clean_text(self.article_vars["sourceUrl"].get())
        title = clean_text(self.article_vars["title"].get())
        return source_url, title

    def link_contact_to_current_article(self) -> None:
        contact_id = self.current_contact_id or self.save_contact()
        if not contact_id:
            return
        source_url, title = self._current_article_source()
        if not source_url:
            messagebox.showwarning(
                "Quellen-URL fehlt",
                "Der aktuelle Beitrag braucht eine Quellen-URL, damit der Kontakt eindeutig verknüpft werden kann.",
                parent=self,
            )
            return

        key = normalize_source_url(source_url)
        link = self.contact_db.setdefault("articleLinks", {}).setdefault(key, {
            "sourceUrl": source_url,
            "title": title,
            "contactIds": [],
        })
        link["sourceUrl"] = source_url
        link["title"] = title
        ids = link.setdefault("contactIds", [])
        if contact_id not in ids:
            ids.append(contact_id)
        write_contact_db(self.contact_db)
        self.refresh_contacts()
        self._select_contact(contact_id)
        self._refresh_contact_links_text(contact_id)
        self._update_article_contact_badge()
        self.status_var.set("Kontakt mit aktuellem Beitrag verknüpft")

    def _contacts_for_source(self, source_url: str) -> list[tuple[str, dict[str, Any]]]:
        key = normalize_source_url(source_url)
        link = self.contact_db.get("articleLinks", {}).get(key, {})
        ids = link.get("contactIds", []) if isinstance(link, dict) else []
        result = []
        for contact_id in ids if isinstance(ids, list) else []:
            contact = self.contact_db.get("contacts", {}).get(contact_id)
            if isinstance(contact, dict):
                result.append((contact_id, contact))
        result.sort(key=lambda item: (not bool(item[1].get("preferred")), clean_text(item[1].get("name"))))
        return result

    def _update_article_contact_badge(self) -> None:
        if not hasattr(self, "article_contact_summary_var"):
            return
        source_url, _ = self._current_article_source()
        contacts = self._contacts_for_source(source_url) if source_url else []
        if not contacts:
            self.article_contact_summary_var.set(
                "Noch kein Kontakt mit diesem Beitrag verknüpft."
            )
            return
        labels = []
        for _, contact in contacts[:3]:
            name = clean_text(contact.get("name")) or clean_text(contact.get("institution"))
            institution = clean_text(contact.get("institution"))
            labels.append(f"{name} ({institution})" if institution and institution != name else name)
        suffix = f" und {len(contacts) - 3} weitere" if len(contacts) > 3 else ""
        self.article_contact_summary_var.set(
            f"{len(contacts)} Kontakt(e): " + ", ".join(labels) + suffix
        )

    def open_current_article_contacts(self) -> None:
        source_url, _ = self._current_article_source()
        contacts = self._contacts_for_source(source_url) if source_url else []
        self.tabs.select(self.contacts_tab)
        if contacts:
            contact_id, _contact = contacts[0]
            self._select_contact(contact_id)
            self.load_selected_contact()
        else:
            self.new_contact()
            messagebox.showinfo(
                "Noch kein Kontakt verknüpft",
                (
                    "Zu diesem Beitrag ist noch kein interner Kontakt gespeichert.\n\n"
                    "Du kannst einen Kontakt anlegen und anschließend „Mit aktuellem Beitrag verknüpfen“ wählen."
                ),
                parent=self,
            )

    def _select_contact(self, contact_id: str) -> None:
        for item, stored_id in self.contact_paths_by_item.items():
            if stored_id == contact_id:
                self.contact_list.selection_set(item)
                self.contact_list.focus(item)
                self.contact_list.see(item)
                return

    def copy_contact_email(self) -> None:
        email = clean_text(self.contact_vars["email"].get())
        if not email:
            messagebox.showinfo("Keine E-Mail-Adresse", "Für diesen Kontakt ist keine E-Mail-Adresse gespeichert.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(email)
        self.update_idletasks()
        self.status_var.set(f"E-Mail-Adresse kopiert: {email}")

    def open_contact_profile(self) -> None:
        url = clean_text(self.contact_vars["profileUrl"].get()) or clean_text(
            self.contact_vars["contactSourceUrl"].get()
        )
        if not url:
            messagebox.showinfo("Keine Kontaktseite", "Für diesen Kontakt ist keine Profil- oder Nachweis-URL gespeichert.", parent=self)
            return
        webbrowser.open(url)

    def load_selected_article(self, _event=None):
        result = super().load_selected_article(_event)
        self._update_article_contact_badge()
        return result

    def new_article(self):
        result = super().new_article()
        self._update_article_contact_badge()
        return result


if __name__ == "__main__":
    NewsStudio52().mainloop()
