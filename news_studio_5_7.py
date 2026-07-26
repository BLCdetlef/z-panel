#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.7 – Bauwesen, Stoffströme und Mobilität.

Benötigt im selben Ordner:
- news_studio_5_6.py
- news_studio_5_5_2.py und dessen bisherige Basisdateien

Version 5.7 erweitert den Rechercheprompt und die lokale Redaktionsmaske.
Alle Funktionen von Version 5.6 bleiben erhalten.
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_6.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_6.py wurde nicht gefunden.\n"
        "Lege News Studio 5.7 in denselben Ordner wie Version 5.6."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_6_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.6 konnte nicht geladen werden.")

base57 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base57
spec.loader.exec_module(base57)

# News Studio 5.6 hält das Modul von Version 5.5.2 unter base56.
studio552 = base57.base56

SYSTEM_FIELD_SPECS = (
    ("sector", "Bauwesen / Verkehr: Sektor", 2),
    ("materialOrSystem", "Material, Produkt oder System", 3),
    ("lifeCycleStage", "Lebenszyklusphase", 2),
    ("absoluteMagnitude", "Absolute Größenordnung", 4),
    ("perCapitaPerspective", "Pro-Kopf-Perspektive", 3),
    ("globalScaleQuestion", "Globale Verallgemeinerbarkeit", 4),
    ("circularity", "Kreislauf und Entsorgungsweg", 3),
    ("substitutionEffect", "Substitution oder zusätzlicher Verbrauch", 3),
    ("reboundRisk", "Rebound- oder Induktionsrisiko", 3),
    ("teachingPotential", "Potenzial für Lehre und Diskussion", 3),
)

SYSTEM_IMPORT_ALIASES = {
    "sector": ("sector", "sektor"),
    "materialOrSystem": ("materialOrSystem", "materialOderSystem"),
    "lifeCycleStage": ("lifeCycleStage", "lebenszyklusphase"),
    "absoluteMagnitude": ("absoluteMagnitude", "absoluteGroessenordnung"),
    "perCapitaPerspective": ("perCapitaPerspective", "proKopfPerspektive"),
    "globalScaleQuestion": ("globalScaleQuestion", "globaleSkalierungsfrage"),
    "circularity": ("circularity", "kreislauffaehigkeit"),
    "substitutionEffect": ("substitutionEffect", "substitution"),
    "reboundRisk": ("reboundRisk", "reboundRisiko"),
    "teachingPotential": ("teachingPotential", "lehrpotenzial"),
}

RESEARCH_EXTENSION = '## Verbindlicher Rechercheschwerpunkt: Bauwesen, gebaute Umwelt und Mobilität\n\nBerücksichtige bei jeder Recherche gezielt aktuelle Meldungen mit direkter Bedeutung\nfür Bauwesen, gebaute Umwelt, Infrastruktur oder Mobilität. Nimm nach Möglichkeit\nmindestens zwei solche Meldungen in die Auswahl auf, sofern im gewählten Zeitraum\nbelastbare neue Original- oder Primärquellen vorliegen. Erfinde keine Ersatzmeldungen,\nwenn keine geeigneten neuen Quellen vorhanden sind.\n\nSuche nicht nur nach als „nachhaltig“ bezeichneten Produkten und technischen\nInnovationen. Untersuche vor allem absolute Stoffströme, Bestände, Flächen,\nNutzungsdauern, Schadstoffeinträge, Entsorgungswege, globale Gerechtigkeit und die\nFrage, ob ein Modell weltweit verallgemeinerbar wäre.\n\n### Bauwesen und gebaute Umwelt\n\nPrüfe insbesondere neue Daten, Studien, amtliche Berichte und belastbare\nPraxisentwicklungen zu:\n\n- Wohnfläche pro Person in Deutschland, Europa und weltweit sowie zur Frage,\n  welche Wohnfläche global gerecht und ökologisch tragfähig sein könnte;\n- Neubau, Umbau, Umnutzung, Leerstand, Abriss, Bestandserhalt und Suffizienz;\n- tatsächlicher Wiederverwendung, hochwertigem Recycling, Downcycling,\n  Verfüllung, Verbrennung und Deponierung im Hoch- und Tiefbau;\n- Bauteilbörsen, Urban Mining, rückbaubaren Konstruktionen und ReTuna-ähnlichen\n  Einrichtungen für gebrauchte Baustoffe;\n- Zement, Beton, Sand, Kies, Gips, Stahl, Aluminium, Kupfer, Holz,\n  Holzwerkstoffplatten, Kunststoffen, Kunststoffrohren, Kabeln, Geotextilien,\n  Dämmstoffen, Werkzeugen, Elektrogeräten und Baumaschinen;\n- Lebensdauer, Reparierbarkeit, Trennbarkeit und Entsorgung von\n  Wärmedämmverbundsystemen und anderen Verbundkonstruktionen;\n- Bioziden in Fassadenfarben und Putzen sowie Auswaschungen in Boden und Wasser;\n- PFAS, Flammschutzmitteln, Weichmachern, Mikroplastik und weiteren\n  problematischen Stoffen in Bauprodukten;\n- Versiegelung, Landschaftszerschneidung, Rohstoffgewinnung und Importabhängigkeiten;\n- grauer Energie, grauen Emissionen und absoluten Materialmengen;\n- der Frage, was tatsächlich neu gebaut werden muss.\n\nPrüfe bei Materialien und Bauprodukten nach Möglichkeit die gesamte Kette:\n\nRohstoffgewinnung → Herstellung → Transport → Einbau → Nutzung → Wartung →\nSanierung → Rückbau → Wiederverwendung, Recycling, Verbrennung oder Deponierung.\n\n### Mobilität und Verkehr\n\nBetrachte Mobilität als Stoff-, Produktions-, Energie- und Flächensystem und\nnicht nur als Vergleich einzelner Antriebe. Suche insbesondere nach:\n\n- Pkw-Bestand je Einwohner*in oder Haushalt;\n- Masse der Pkw-Flotte beziehungsweise Tonnen Fahrzeugmasse pro Kopf;\n- Fahrzeuggewicht, Fahrzeuggröße, SUV-Anteil und tatsächlicher Auslastung;\n- täglicher Nutzungsdauer und langen Standzeiten privater Pkw;\n- Zahl, Größe und Kapazität von Fahrzeugfabriken und Zulieferstrukturen;\n- Stahl-, Aluminium-, Kupfer-, Kunststoff-, Gummi- und Batterierohstoffbedarf;\n- Parkplatzfläche, Parkhäusern, Straßenfläche und öffentlichem Raum pro Person;\n- Reifen- und Bremsabrieb, Mikroplastik, Lärm und Schadstoffeinträgen;\n- Herstellung, Wartung, Ersatzteilen und Entsorgung von Fahrzeugen und Batterien;\n- Flugreisen und Flugkilometern pro Person sowie ihrer sozialen Verteilung;\n- der hohen Klimawirkung des Flugverkehrs einschließlich Nicht-CO₂-Effekten\n  wie Kondensstreifen und Stickoxidwirkungen in großer Flughöhe;\n- Bedingungen, unter denen Bus und Bahn gegenüber Pkw und Flugzeug tatsächlich\n  besser abschneiden: Auslastung, Energiequelle, Fahrzeuggröße, Streckenlänge,\n  Infrastrukturaufwand und wirkliche Verlagerung;\n- der Frage, ob neue Angebote Autofahrten oder Flüge ersetzen oder nur zusätzliche\n  Verkehrsleistung erzeugen;\n- Verkehrsvermeidung, kurzen Wegen, kompakter Siedlungsentwicklung, gemeinsamer\n  Nutzung und besserer Auslastung vorhandener Fahrzeuge;\n- Neubau, Erhalt, Sanierung und möglichem Rückbau von Straßen, Schienen,\n  Brücken, Tunneln, Parkflächen und Flughäfen.\n\nErkläre bei geeigneten Meldungen verständlich, warum Bus und Bahn bei guter\nAuslastung in der Regel Vorteile haben: Ein Fahrzeug befördert viele Menschen;\nMaterial-, Energie- und Flächenaufwand verteilen sich auf mehr Personenkilometer.\nKennzeichne aber die Bedingungen und Systemgrenzen, statt öffentliche\nVerkehrsmittel pauschal als nachhaltig zu bezeichnen.\n\n### Verbindliche systemische Fragen\n\nPrüfe bei geeigneten Bau- und Verkehrsmeldungen:\n\n- Wie groß sind Bestand, Stoffstrom, Fläche oder Energieverbrauch absolut?\n- Wie hoch ist der Wert pro Person, Haushalt oder Personenkilometer?\n- Welchen Anteil hat das Bau- oder Verkehrssystem am Gesamtverbrauch?\n- Wie lange wird das Produkt oder Bauwerk tatsächlich genutzt?\n- Welche Umweltwirkungen entstehen über den vollständigen Lebenszyklus?\n- Was geschieht am Ende der Nutzung?\n- Wird etwas Vorhandenes messbar ersetzt oder kommt das Neue zusätzlich hinzu?\n- Welche Rebound- oder Induktionseffekte sind möglich?\n- Welche Folgen werden räumlich oder zeitlich ausgelagert?\n- Was geschähe, wenn alle Länder oder Menschen vergleichbare Pro-Kopf-Standards\n  bei Wohnfläche, Pkw-Bestand, Flügen, Infrastruktur oder Materialeinsatz anstrebten?\n- Ist die Entwicklung lokal sinnvoll, national skalierbar, global\n  verallgemeinerbar oder unter planetaren Grenzen nicht verallgemeinerbar?\n- Welche Bevölkerungsgruppen profitieren, und welche tragen Umwelt-, Gesundheits-\n  oder Kostenfolgen?\n- Wie lässt sich das Thema in Bauingenieur-Ausbildung oder öffentlicher Diskussion\n  anschaulich vermitteln?\n\nBevorzuge absolute, verständliche Kennzahlen wie Tonnen Fahrzeugmasse pro Person,\nQuadratmeter Parkplatzfläche pro Einwohner*in, Wohnfläche pro Kopf, Tonnen\nBaustoff pro Person, gesamte Jahresmengen, Nutzungsdauer, Auslastung sowie\nWiederverwendungs- und echte Recyclinganteile.\n\n### Quellen\n\nPrüfe zusätzlich besonders:\n\nUmweltbundesamt, Statistisches Bundesamt, BBSR, BAM, BASt, BGR, Difu,\nFraunhofer-Institute, Wuppertal Institut, Öko-Institut, Thünen-Institut,\nEuropean Environment Agency, Eurostat, Joint Research Centre, UNEP International\nResource Panel, OECD, International Energy Agency, GlobalABC, amtliche Kommunen,\nVerkehrs- und Baubehörden, Hochschulen und wissenschaftliche Fachjournale.\n\nResearchGate, LinkedIn, Presseartikel, Verbands- und Unternehmensseiten dürfen\nals Fundstellen dienen, gelten aber nicht automatisch als Originalquelle.\n\n### Zusätzliche Importfelder für Bau- und Verkehrsthemen\n\nDas Wort „genau“ in der vorherigen Beschreibung des editorial-Objekts ist für\nNews Studio 5.7 als „mindestens“ zu verstehen. Ergänze bei Bau-, Material-,\nInfrastruktur- und Verkehrsthemen im Objekt "editorial" zusätzlich diese Felder.\nBei anderen Meldungen dürfen sie leer bleiben:\n\n{\n  "sector": "Hochbau, Tiefbau, Infrastruktur, Mobilität, Gebäudetechnik oder Querschnitt",\n  "materialOrSystem": "betroffenes Material, Produkt, Verkehrsmittel oder System",\n  "lifeCycleStage": "Rohstoff, Herstellung, Bau, Nutzung, Wartung, Sanierung, Rückbau oder Entsorgung",\n  "absoluteMagnitude": "absolute Mengen, Bestände, Flächen oder Energieverbräuche",\n  "perCapitaPerspective": "Pro-Kopf-, Haushalts- oder Personenkilometer-Perspektive",\n  "globalScaleQuestion": "Folgen einer weltweiten Übertragung vergleichbarer Standards",\n  "circularity": "Wiederverwendung, hochwertiges Recycling, Downcycling, Verbrennung oder Deponierung",\n  "substitutionEffect": "was tatsächlich ersetzt wird und was zusätzlich entsteht",\n  "reboundRisk": "mögliche Mehrverbräuche, induzierter Verkehr oder andere gegenläufige Effekte",\n  "teachingPotential": "konkrete Verwendung in Bauingenieur-Ausbildung oder öffentlicher Diskussion"\n}\n\nKeine dieser Angaben darf erfunden werden. Wenn belastbare Daten fehlen, benenne\ndie Lücke ausdrücklich unter "uncertainties".'

CHECKLIST_EXTENSION = """\
□ Bauwesen- oder Mobilitätsrelevanz geprüft
□ Absolute Mengen, Bestände oder Flächen geprüft
□ Pro-Kopf- oder Personenkilometer-Perspektive geprüft
□ Vollständigen Lebenszyklus einschließlich Entsorgung betrachtet
□ Tatsächliche Substitution gegenüber zusätzlichem Verbrauch geprüft
□ Rebound- oder Induktionseffekte geprüft
□ Globale Verallgemeinerbarkeit und Gerechtigkeit geprüft
□ Eignung für Bauingenieur-Ausbildung oder öffentliche Diskussion geprüft"""


def patch_editorial_schema() -> None:
    """Erweitert die 5.5.2-Redaktionsfelder vor dem Aufbau der Oberfläche."""
    existing = {key for key, _label, _height in studio552.EDITORIAL_FIELD_SPECS}
    additions = tuple(
        spec for spec in SYSTEM_FIELD_SPECS if spec[0] not in existing
    )
    if additions:
        studio552.EDITORIAL_FIELD_SPECS = (
            tuple(studio552.EDITORIAL_FIELD_SPECS) + additions
        )

    aliases = dict(studio552.EDITORIAL_IMPORT_ALIASES)
    for key, values in SYSTEM_IMPORT_ALIASES.items():
        aliases.setdefault(key, values)
    studio552.EDITORIAL_IMPORT_ALIASES = aliases


patch_editorial_schema()


class NewsStudio57(base57.NewsStudio56):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.7")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.6", "ZUSTAND News Studio 5.7"
        )
        self._ensure_systemic_research_checklist()
        self.status_var.set(
            "News Studio 5.7 bereit │ Bauwesen, Stoffströme und Mobilität im Rechercheprofil"
        )

    def _ensure_systemic_research_checklist(self) -> None:
        guide = self.editorial_data.setdefault("guide", {})
        current = str(guide.get("researchChecklist", "") or "").strip()
        marker = "Globale Verallgemeinerbarkeit und Gerechtigkeit geprüft"

        if marker not in current:
            guide["researchChecklist"] = (
                current + "\n" + CHECKLIST_EXTENSION
            ).strip()
            self.editorial_data["updatedAt"] = studio552.now_iso()
            studio552.write_editorial_file(self.editorial_data)

        widget = getattr(self, "editorial_guide_widgets", {}).get(
            "researchChecklist"
        )
        if widget is not None:
            displayed = widget.get("1.0", "end").strip()
            if marker not in displayed:
                widget.delete("1.0", "end")
                widget.insert(
                    "1.0", guide.get("researchChecklist", "")
                )

    def build_research_prompt(self, period: str) -> str:
        prompt = super().build_research_prompt(period)

        # Die frühere Formulierung „genau diese Felder“ würde die neuen
        # redaktionellen Felder ausschließen.
        prompt = prompt.replace(
            'Ergänze in jedem Artikel ein Objekt \\"editorial\\" mit genau diesen Feldern:',
            'Ergänze in jedem Artikel ein Objekt \\"editorial\\" mit mindestens diesen Feldern:',
        )
        prompt = prompt.replace(
            'Ergänze in jedem Artikel ein Objekt "editorial" mit genau diesen Feldern:',
            'Ergänze in jedem Artikel ein Objekt "editorial" mit mindestens diesen Feldern:',
        )
        return prompt.rstrip() + "\n\n" + RESEARCH_EXTENSION + "\n"


if __name__ == "__main__":
    app = NewsStudio57()
    app.mainloop()
