"""Knowledge map — tracks LIOS learning progress across EU and German law topics."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_MAP_FILE = Path("data/memory/knowledge_map.json")
_ANSWER_HISTORY_FILE = Path("data/memory/answer_history.jsonl")
_CORPUS_FILE = Path("data/corpus/legal_chunks.jsonl")
_lock = Lock()

_STATUS_ORDER = ["unknown", "seed", "learning", "connected", "functional", "mastered"]
_QUESTION_TEMPLATES = [
    "Was regelt {regulation} {article} ({title}) und welche Pflichten entstehen für Unternehmen?",
    "Wann ist {regulation} {article} ({title}) anwendbar und auf wen?",
    "Welche Risiken oder Sanktionen ergeben sich aus {regulation} {article} ({title}) bei Verstößen?",
    "Wie setzt man die Anforderungen aus {regulation} {article} ({title}) praktisch um?",
    "Welche Nachweise oder Dokumentation verlangt {regulation} {article} ({title}) konkret?",
]
_STOP_WORDS = {
    "der", "die", "das", "den", "dem", "des", "und", "oder", "mit", "auf", "für", "von", "aus",
    "ein", "eine", "einer", "eines", "einem", "zu", "im", "in", "an", "is", "are", "this", "that",
    "shall", "must", "under", "nach", "what", "which", "when", "where", "wer", "wie", "was",
}
_TOPIC_CORPUS_HINTS: dict[str, list[str]] = {
    "csrd": ["csrd"],
    "esrs": ["esrs"],
    "eu_taxonomy": ["taxonomy", "taxonom", "eu_taxonomy"],
    "sfdr": ["sfdr"],
    "cs3d": ["cs3d", "csddd", "due diligence"],
    "eudr": ["eudr", "deforestation"],
    "lksg": ["lksg"],
    "gdpr": ["gdpr", "dsgvo"],
    "behg": ["behg"],
    "ksg": ["ksg"],
    "hgb": ["hgb"],
    "reach": ["reach"],
    "mifid2": ["mifid"],
    "srd2": ["srd", "aktionär"],
    "ai_act": ["ai act", "ai"],
    "nis2": ["nis2"],
}
_CORPUS_CHUNKS_CACHE: list[dict] | None = None

# ── Topic seed map ─────────────────────────────────────────────────────────────

_SEED_MAP: list[dict] = [
    # EU-Nachhaltigkeitsrecht
    {"id": "csrd", "name": "CSRD", "category": "EU-Nachhaltigkeitsrecht",
     "status": "functional", "pct": 85, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Corporate Sustainability Reporting Directive 2022/2464 — Pflicht zur Nachhaltigkeitsberichterstattung für große EU-Unternehmen"},
    {"id": "esrs", "name": "ESRS-Standards", "category": "EU-Nachhaltigkeitsrecht",
     "status": "functional", "pct": 75, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "European Sustainability Reporting Standards — 12 Standards für Umwelt-, Sozial- und Governance-Berichterstattung"},
    {"id": "eu_taxonomy", "name": "EU-Taxonomie", "category": "EU-Nachhaltigkeitsrecht",
     "status": "connected", "pct": 55, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU-Taxonomieverordnung 2020/852 — Klassifizierung ökologisch nachhaltiger Wirtschaftstätigkeiten"},
    {"id": "sfdr", "name": "SFDR", "category": "EU-Nachhaltigkeitsrecht",
     "status": "learning", "pct": 40, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Sustainable Finance Disclosure Regulation 2019/2088 — Artikel-6-, 8- und 9-Fondsklassifizierung"},
    {"id": "cs3d", "name": "CS3D / CSDDD", "category": "EU-Nachhaltigkeitsrecht",
     "status": "seed", "pct": 10, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Corporate Sustainability Due Diligence Directive — Menschenrechts- und Umweltsorgfaltspflichten"},
    {"id": "eudr", "name": "EUDR", "category": "EU-Nachhaltigkeitsrecht",
     "status": "seed", "pct": 5, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU-Entwaldungsverordnung 2023/1115 — Entwaldungsfreie Lieferkettenpflichten"},
    {"id": "green_deal", "name": "Europäischer Green Deal", "category": "EU-Nachhaltigkeitsrecht",
     "status": "seed", "pct": 10, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU-Politikrahmen für Klimaneutralität bis 2050 — Fit for 55, REPowerEU"},
    {"id": "ied", "name": "Industrieemissionsrichtlinie", "category": "EU-Nachhaltigkeitsrecht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "IED 2010/75/EU — Integrierte Vermeidung und Verminderung der Umweltverschmutzung"},
    {"id": "reach", "name": "REACH-Verordnung", "category": "EU-Nachhaltigkeitsrecht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "REACH 1907/2006 — Registrierung, Bewertung, Zulassung und Beschränkung chemischer Stoffe"},

    # EU-Finanzrecht
    {"id": "mifid2", "name": "MiFID II", "category": "EU-Finanzrecht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Richtlinie über Märkte für Finanzinstrumente II — Anlageberatung, ESG-Integrationsanforderungen"},
    {"id": "srd2", "name": "Aktionärsrechterichtlinie II", "category": "EU-Finanzrecht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "SRD II 2017/828 — Aktionärsengagement, Say-on-Pay, Transaktionen mit nahestehenden Parteien"},
    {"id": "eu_whistleblower", "name": "EU-Hinweisgeberschutzrichtlinie", "category": "EU-Finanzrecht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Richtlinie 2019/1937 — Schutz von Personen, die EU-Rechtsverstöße melden"},
    {"id": "gdpr", "name": "DSGVO", "category": "EU-Finanzrecht",
     "status": "connected", "pct": 65, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Datenschutz-Grundverordnung 2016/679 — Rechte betroffener Personen und Unternehmenspflichten"},
    {"id": "eu_competition", "name": "EU-Wettbewerbsrecht", "category": "EU-Finanzrecht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "AEUV Artikel 101–102 — Kartelle, Missbrauch marktbeherrschender Stellung, Fusionskontrolle"},

    # Deutsches Recht
    {"id": "lksg", "name": "LkSG — Lieferkettensorgfaltspflichtengesetz", "category": "Deutsches Recht",
     "status": "learning", "pct": 35, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Lieferkettensorgfaltspflichtengesetz — Menschenrechts- und Umweltsorgfaltspflichten für deutsche Unternehmen"},
    {"id": "behg", "name": "BEHG — Brennstoffemissionshandel", "category": "Deutsches Recht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Brennstoffemissionshandelsgesetz — Nationale CO₂-Bepreisung für Wärme und Verkehr"},
    {"id": "ksg", "name": "KSG — Klimaschutzgesetz", "category": "Deutsches Recht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Klimaschutzgesetz — Verbindliche jährliche CO₂-Minderungsziele Deutschlands nach Sektoren"},
    {"id": "german_corporate", "name": "GmbHG / AktG", "category": "Deutsches Recht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "GmbH-Gesetz und Aktiengesetz — Deutsches Gesellschaftsrecht, Vorstandspflichten, Aufsichtsrat"},
    {"id": "hgb", "name": "HGB — Handelsgesetzbuch", "category": "Deutsches Recht",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Handelsgesetzbuch — Rechnungslegungspflichten, Jahresabschluss, Lagebericht"},
    {"id": "bgb_contracts", "name": "BGB — Vertragsrecht", "category": "Deutsches Recht",
     "status": "seed", "pct": 15, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Bürgerliches Gesetzbuch — Vertragsschluss, Haftung, Schadensersatz"},

    # Rechtsgrundlagen
    {"id": "eu_legal_terms", "name": "EU-Rechtsvokabular", "category": "Rechtsgrundlagen",
     "status": "connected", "pct": 62, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Grundbegriffe des EU-Rechts: Richtlinie vs. Verordnung, Subsidiarität, Verhältnismäßigkeit, Vorabentscheidungsverfahren"},
    {"id": "cjeu_cases", "name": "EuGH-Umweltentscheidungen", "category": "Rechtsgrundlagen",
     "status": "learning", "pct": 40, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Leitentscheidungen des Gerichtshofs der EU zu Umwelt- und Nachhaltigkeitsrecht"},
    {"id": "greenwashing_law", "name": "Greenwashing-Recht", "category": "Rechtsgrundlagen",
     "status": "learning", "pct": 45, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU-Richtlinie über Umweltaussagen, UWG §5 irreführende Angaben — Rechtsstandard für Umweltbehauptungen"},
    {"id": "double_materiality", "name": "Doppelte Wesentlichkeit", "category": "Rechtsgrundlagen",
     "status": "connected", "pct": 58, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "CSRD/ESRS-Anforderung — Auswirkungs- und finanzielle Wesentlichkeitsbewertung"},

    # Globale Rahmenwerke
    {"id": "gri", "name": "GRI-Standards", "category": "Globale Rahmenwerke",
     "status": "learning", "pct": 45, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Global Reporting Initiative — Freiwillige Nachhaltigkeitsberichterstattung, kompatibel mit ESRS"},
    {"id": "tcfd", "name": "TCFD", "category": "Globale Rahmenwerke",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Task Force on Climate-related Financial Disclosures — 4 Säulen, Grundlage für ESRS E1"},
    {"id": "issb", "name": "ISSB / IFRS S1 S2", "category": "Globale Rahmenwerke",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "International Sustainability Standards Board — IFRS S1 allgemein, IFRS S2 klimabezogen"},

    # EU-Primärrecht
    {"id": "teu", "name": "Vertrag über die EU (TEU)", "category": "EU-Primärrecht",
     "status": "functional", "pct": 72, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Vertrag über die Europäische Union — institutioneller Rahmen, Werte, Grundsätze, Zuständigkeiten der EU"},
    {"id": "tfeu", "name": "AEUV / TFEU", "category": "EU-Primärrecht",
     "status": "functional", "pct": 70, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Vertrag über die Arbeitsweise der EU — Binnenmarkt, Grundfreiheiten, Wettbewerbsrecht, AEUV Art. 101–109"},
    {"id": "eu_charter", "name": "EU-Grundrechtecharta", "category": "EU-Primärrecht",
     "status": "connected", "pct": 62, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Charta der Grundrechte der EU — verbindliche Grundrechte beim Vollzug von EU-Recht, Art. 7 Datenschutz, Art. 17 Eigentum"},
    {"id": "eu_legislative", "name": "EU-Gesetzgebungsverfahren", "category": "EU-Primärrecht",
     "status": "connected", "pct": 58, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Ordentliches Gesetzgebungsverfahren — Initiativmonopol Kommission, Mitentscheidung Parlament/Rat, Trilog"},

    # EuGH-Leitentscheidungen
    {"id": "van_gend_loos", "name": "Van Gend en Loos (1963)", "category": "EuGH-Leitentscheidungen",
     "status": "functional", "pct": 68, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Rs. 26/62 — Unmittelbare Wirkung des EU-Rechts: Einzelpersonen können sich vor nationalen Gerichten direkt auf EU-Recht berufen"},
    {"id": "costa_enel", "name": "Costa v ENEL (1964)", "category": "EuGH-Leitentscheidungen",
     "status": "functional", "pct": 68, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Rs. 6/64 — Vorrang des EU-Rechts: EU-Recht hat Vorrang vor nationalem Recht, auch vor späteren nationalen Gesetzen"},
    {"id": "cassis_dijon", "name": "Cassis de Dijon (1979)", "category": "EuGH-Leitentscheidungen",
     "status": "connected", "pct": 62, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Rs. 120/78 — Gegenseitige Anerkennung: In einem Mitgliedstaat rechtmäßig hergestellte Waren können im gesamten Binnenmarkt verkauft werden"},
    {"id": "francovich", "name": "Francovich (1991)", "category": "EuGH-Leitentscheidungen",
     "status": "connected", "pct": 58, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Rs. C-6/90 — Staatshaftung: Mitgliedstaaten haften für Schäden aus Verstößen gegen EU-Recht gegenüber Einzelpersonen"},
    {"id": "schrems", "name": "Schrems I & II", "category": "EuGH-Leitentscheidungen",
     "status": "connected", "pct": 55, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Rs. C-362/14 & C-311/18 — Transatlantischer Datentransfer: Safe Harbor und Privacy Shield für ungültig erklärt; Standardvertragsklauseln unter strengen Bedingungen"},
    {"id": "google_spain", "name": "Google Spain (2014)", "category": "EuGH-Leitentscheidungen",
     "status": "connected", "pct": 60, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Rs. C-131/12 — Recht auf Vergessenwerden: Suchmaschinen müssen auf Antrag veraltete oder irrelevante Einträge aus den Suchergebnissen löschen"},

    # EU-Institutionen
    {"id": "eu_commission", "name": "Europäische Kommission", "category": "EU-Institutionen",
     "status": "functional", "pct": 70, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Hüterin der Verträge — Initiativmonopol, Wettbewerbskontrolle, Vertragsverletzungsverfahren, 27 Kommissare"},
    {"id": "eu_parliament", "name": "Europäisches Parlament", "category": "EU-Institutionen",
     "status": "connected", "pct": 62, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Direkt gewählte Volksvertretung — Mitgesetzgebung im ordentlichen Verfahren, Haushaltskontrolle, 705 Abgeordnete"},
    {"id": "cjeu_court", "name": "EuGH — Gerichtshof der EU", "category": "EU-Institutionen",
     "status": "connected", "pct": 62, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Oberster Gerichtshof der EU — Vorabentscheidungsverfahren, Nichtigkeitsklagen, Vertragsverletzungsverfahren"},

    # EU-Digitalrecht
    {"id": "ai_act", "name": "EU AI-Gesetz", "category": "EU-Digitalrecht",
     "status": "learning", "pct": 30, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "KI-Verordnung (EU) 2024/1689 — risikobasierter Rahmen für KI-Systeme: verboten, hochriskant, allgemeinzweckfähig"},
    {"id": "nis2", "name": "NIS2-Richtlinie", "category": "EU-Digitalrecht",
     "status": "seed", "pct": 25, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Richtlinie 2022/2555 — Cybersicherheitspflichten für wesentliche und wichtige Einrichtungen in der EU"},
]

# ── Fragenbank — alle Fragen auf Deutsch ──────────────────────────────────────

_QUESTION_BANK: dict[str, list[dict]] = {
    "csrd": [
        # --- existing questions ---
        {"type": "definition", "q": "Was ist die CSRD und welche Richtlinie ersetzt sie?"},
        {"type": "application", "q": "Eine deutsche AG hat 400 Mitarbeiter, €80 Mio. Umsatz, €45 Mio. Bilanzsumme. Gilt CSRD ab 2025?"},
        {"type": "application", "q": "Ein börsennotiertes KMU mit 150 Mitarbeitern möchte CSRD bis 2028 aussetzen. Ist dies zulässig?"},
        {"type": "definition", "q": "Was regelt Artikel 19a der CSRD und welche Angaben muss er enthalten?"},
        {"type": "case", "q": "Ein Unternehmen veröffentlicht einen Nachhaltigkeitsbericht, lässt Scope-3-Emissionen wegen fehlender Daten aus. Ist dies CSRD-konform?"},
        {"type": "definition", "q": "Welche drei Phasentermine sieht das schrittweise Inkrafttreten der CSRD vor?"},
        {"type": "application", "q": "Eine Nicht-EU-Muttergesellschaft hat eine große EU-Tochter. Ab wann gilt CSRD für die Gruppe?"},
        # --- Student perspective ---
        {"type": "student", "q": "Erkläre die CSRD in einfachen Worten — welches Problem löst sie?"},
        {"type": "student", "q": "Wie unterscheidet sich die CSRD von der alten NFRD (Nicht-Finanzberichterstattungsrichtlinie)?"},
        {"type": "student", "q": "Was bedeutet 'doppelte Wesentlichkeit' und warum ist sie das Herzstück der CSRD?"},
        # --- Teacher perspective ---
        {"type": "teacher", "q": "Gib ein Lehrbeispiel: Wann gilt die CSRD für ein KMU und wann nicht?"},
        {"type": "teacher", "q": "Erkläre die dreistufige Einführung der CSRD anhand einer Zeitleiste."},
        # --- Lawyer perspective ---
        {"type": "lawyer", "q": "Was sagt Art. 2 CSRD zum Begriff 'großes Unternehmen' — nennen Sie die genauen Schwellenwerte."},
        {"type": "lawyer", "q": "Welche Ausnahmen vom CSRD-Anwendungsbereich sieht Art. 2 Abs. 2 für Tochtergesellschaften vor?"},
        {"type": "lawyer", "q": "Welche Anforderungen stellt CSRD Art. 8 an die externe Prüfung des Nachhaltigkeitsberichts?"},
        # --- Business owner perspective ---
        {"type": "business_owner", "q": "Mein Unternehmen hat 260 Mitarbeiter und €50 Mio. Umsatz. Bin ich von der CSRD betroffen?"},
        {"type": "business_owner", "q": "Was kostet die CSRD-Compliance ungefähr und was muss ich zuerst tun?"},
        {"type": "business_owner", "q": "Ich bin Geschäftsführer einer GmbH mit 320 Mitarbeitern — ab wann muss ich berichten und was droht bei Verstoß?"},
        # --- National court perspective ---
        {"type": "court", "q": "Wie ist CSRD Art. 19a auszulegen, wenn eine nationale Behörde den Begriff 'Nachhaltigkeitsinformation' interpretiert?"},
        {"type": "court", "q": "Kann ein Einzelner aus der CSRD unmittelbare Rechte gegenüber einem Unternehmen ableiten?"},
        # --- European Court perspective ---
        {"type": "ecj", "q": "Welche Erwägungsgründe der CSRD erläutern den Gesetzeszweck und wie sollten sie bei der Auslegung von Art. 19a herangezogen werden?"},
        {"type": "ecj", "q": "Steht die CSRD-Prüfpflicht (Art. 8) im Einklang mit dem Verhältnismäßigkeitsprinzip für KMU?"},
    ],
    "esrs": [
        {"type": "definition", "q": "Was ist der Unterschied zwischen ESRS 1 und ESRS 2?"},
        {"type": "definition", "q": "Nennen Sie die 5 Umwelt-ESRS-Standards (E1–E5) und deren Regelungsgegenstand."},
        {"type": "application", "q": "Ein Unternehmen hat keine wesentlichen Klimarisiken. Muss es dennoch nach ESRS E1 berichten?"},
        {"type": "case", "q": "Ein Prüfer stellt fest, dass ein Unternehmen nur finanzielle Wesentlichkeit bewertet, nicht aber die Auswirkungswesentlichkeit. Welcher ESRS wird verletzt?"},
        {"type": "definition", "q": "Was deckt ESRS G1 ab und für wen gilt er?"},
        {"type": "application", "q": "Welcher ESRS-Standard regelt die eigene Belegschaft — Lohngleichheit, Arbeitsbedingungen, Gewerkschaften?"},
        # --- Student ---
        {"type": "student", "q": "Was sind die ESRS und wozu braucht man sie neben der CSRD?"},
        {"type": "student", "q": "Erkläre den Unterschied zwischen themenspezifischen ESRS (E1–E5, S1–S4, G1) und den übergreifenden ESRS 1 und 2."},
        # --- Lawyer ---
        {"type": "lawyer", "q": "Welche ESRS-Angaben sind 'freiwillig' und welche sind bei Wesentlichkeit Pflicht?"},
        {"type": "lawyer", "q": "Was fordert ESRS 2 IRO-1 konkret und welche Dokumentationspflichten entstehen?"},
        # --- Business owner ---
        {"type": "business_owner", "q": "Welche ESRS-Standards müssen wir zwingend anwenden — gibt es eine Mindestliste?"},
        {"type": "business_owner", "q": "Unser Unternehmen hat keine Biodiversitätsrisiken identifiziert. Müssen wir ESRS E4 trotzdem anwenden?"},
        # --- Teacher ---
        {"type": "teacher", "q": "Erkläre das IRO-Konzept (Impact, Risk, Opportunity) anhand eines Produktionsunternehmens."},
        # --- Court ---
        {"type": "court", "q": "Wie sind die ESRS rechtlich einzuordnen — haben sie unmittelbare Bindungswirkung oder gelten sie nur über die CSRD?"},
        # --- ECJ ---
        {"type": "ecj", "q": "Welche Erwägungsgründe der ESRS-Delegierten Verordnung 2023/2772 erläutern den Begriff 'Wesentlichkeit'?"},
    ],
    "eu_taxonomy": [
        {"type": "definition", "q": "Welche 6 Umweltziele hat die EU-Taxonomieverordnung?"},
        {"type": "definition", "q": "Was bedeutet DNSH (Do No Significant Harm) in der EU-Taxonomie?"},
        {"type": "application", "q": "Ein Windenergieprojekt beansprucht Taxonomiekonformität. Welche drei Kriterien müssen erfüllt sein?"},
        {"type": "case", "q": "Eine Bank finanziert ein Gaskraftwerk und erklärt es als taxonomiekonform als Übergangstätigkeit. Welche Bedingungen gelten?"},
        {"type": "definition", "q": "Welche KPIs müssen Nicht-Finanzunternehmen unter CSRD zur EU-Taxonomie offenlegen?"},
    ],
    "sfdr": [
        {"type": "definition", "q": "Was ist der Unterschied zwischen einem Artikel-8- und einem Artikel-9-Fonds gemäß SFDR?"},
        {"type": "definition", "q": "Was sind Principal Adverse Impact (PAI)-Indikatoren nach SFDR?"},
        {"type": "application", "q": "Ein Artikel-9-Fonds hält 5 % in Anleihen ohne Nachhaltigkeitsziel. Bleibt er Artikel 9?"},
        {"type": "case", "q": "Ein Fondsmanager vermarktet ein Produkt als 'nachhaltig' ohne SFDR-Artikel-8-Klassifizierung. Welches rechtliche Risiko besteht?"},
        {"type": "definition", "q": "Für wen gilt SFDR — alle EU-Unternehmen oder nur bestimmte Einheiten?"},
    ],
    "lksg": [
        {"type": "definition", "q": "Was ist das LkSG und für welche Unternehmen gilt es?"},
        {"type": "application", "q": "Eine deutsche GmbH hat 2.800 Mitarbeiter. Ab welchem Jahr gilt das LkSG?"},
        {"type": "definition", "q": "Erfasst das LkSG nur unmittelbare Zulieferer oder die gesamte Lieferkette?"},
        {"type": "case", "q": "Ein Zulieferer in Bangladesch verstößt gegen Kinderarbeitsgesetze. Was muss das deutsche Mutterunternehmen nach LkSG tun?"},
        {"type": "application", "q": "Was passiert, wenn ein Unternehmen die LkSG-Risikoanalyse unterlässt? Nennen Sie die Sanktion."},
        {"type": "definition", "q": "Was ist ein Beschwerdeverfahren nach LkSG und wer muss es einrichten?"},
    ],
    "german_corporate": [
        {"type": "definition", "q": "Was ist der Unterschied zwischen einer GmbH und einer AG nach deutschem Recht?"},
        {"type": "definition", "q": "Was ist der Aufsichtsrat und wie unterscheidet er sich vom Vorstand?"},
        {"type": "application", "q": "Eine GmbH will Gewinne ohne Gesellschafterbeschluss ausschütten. Ist dies nach GmbHG zulässig?"},
        {"type": "definition", "q": "Was ist Mitbestimmung und wann gilt sie für deutsche Unternehmen?"},
        {"type": "case", "q": "Ein Vorstandsmitglied schließt einen persönlich vorteilhaften Vertrag ohne Genehmigung des Aufsichtsrats. Welche Rechtsfolge sieht das AktG vor?"},
        {"type": "definition", "q": "Wie hoch ist das Mindeststammkapital einer GmbH bzw. das Grundkapital einer AG?"},
    ],
    "bgb_contracts": [
        {"type": "definition", "q": "Welche drei Elemente sind für einen wirksamen Vertragsschluss nach BGB § 145 erforderlich?"},
        {"type": "definition", "q": "Was ist Schadensersatz und wann entsteht er nach BGB § 280?"},
        {"type": "application", "q": "Ein Unternehmen unterzeichnet einen Vertrag unter Drohung (§ 123 BGB). Welcher Rechtsbehelf steht zur Verfügung?"},
        {"type": "case", "q": "Ein Lieferant liefert mangelhafte Waren. Der Käufer möchte den Vertrag aufheben. Welche BGB-Vorschriften greifen in welcher Reihenfolge?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen Anfechtung und Rücktritt nach BGB?"},
    ],
    "gdpr": [
        {"type": "definition", "q": "Was sind die 6 Rechtsgrundlagen für die Verarbeitung personenbezogener Daten nach Art. 6 DSGVO?"},
        {"type": "application", "q": "Ein Unternehmen verarbeitet Gesundheitsdaten von Mitarbeitern für die Lohnbuchhaltung. Welcher DSGVO-Artikel gilt und welche zusätzliche Voraussetzung ist nötig?"},
        {"type": "definition", "q": "Wie hoch ist die maximale DSGVO-Geldbuße und wie wird sie berechnet?"},
        {"type": "case", "q": "Ein Mitarbeiter verlangt Löschung aller seiner Daten nach Art. 17 DSGVO. Das Unternehmen verweigert dies unter Berufung auf gesetzliche Aufbewahrungspflichten. Ist dies rechtmäßig?"},
        {"type": "definition", "q": "Was ist eine Datenschutz-Folgenabschätzung (DSFA) und wann ist sie Pflicht?"},
    ],
    "greenwashing_law": [
        {"type": "definition", "q": "Was ist Greenwashing nach EU-Verbraucherrecht und welche Richtlinie regelt es?"},
        {"type": "application", "q": "Ein Unternehmen behauptet, sein Produkt sei 'klimaneutral', stützt dies aber allein auf Kompensationen. Ist diese Aussage nach der EU-Richtlinie über Umweltaussagen zulässig?"},
        {"type": "case", "q": "Eine Fluggesellschaft wirbt für 'nachhaltige Flüge' ohne Belege. Welche Vorschrift des UWG könnte greifen?"},
        {"type": "definition", "q": "Was muss ein Unternehmen nachweisen, um nach der vorgeschlagenen EU-Richtlinie über Umweltaussagen eine gültige Umweltbehauptung aufzustellen?"},
        {"type": "application", "q": "Ein Händler verwendet ein nicht EU-zugelassenes privates Ökosiegel. Welches rechtliche Risiko besteht nach 2026?"},
    ],
    "eu_legal_terms": [
        {"type": "definition", "q": "Was ist der Unterschied zwischen einer EU-Richtlinie und einer EU-Verordnung?"},
        {"type": "definition", "q": "Was ist das Subsidiaritätsprinzip im EU-Recht und wo ist es in den Verträgen verankert?"},
        {"type": "definition", "q": "Was ist ein Vorabentscheidungsverfahren und welches Gericht entscheidet darüber?"},
        {"type": "application", "q": "Eine EU-Verordnung ist in Kraft getreten, Deutschland hat sie aber nicht umgesetzt. Gilt sie für deutsche Unternehmen?"},
        {"type": "definition", "q": "Was ist das Verhältnismäßigkeitsprinzip im EU-Recht und wie begrenzt es EU-Maßnahmen?"},
        {"type": "definition", "q": "Was ist die unmittelbare Wirkung im EU-Recht? Nennen Sie ein Beispiel für eine Norm mit unmittelbarer Wirkung."},
        {"type": "case", "q": "Ein deutsches Gericht ist unsicher, wie eine EU-Richtlinie auszulegen ist. Was muss es tun, bevor es entscheidet?"},
    ],
    "double_materiality": [
        {"type": "definition", "q": "Was sind die zwei Dimensionen der doppelten Wesentlichkeit nach CSRD/ESRS?"},
        {"type": "application", "q": "Ein Unternehmen stellt fest, dass seine Fabriken lokale Flüsse verschmutzen (Auswirkung), dies sich aber nicht auf die Finanzlage auswirkt. Muss es darüber nach ESRS berichten?"},
        {"type": "case", "q": "Ein Unternehmen führt nur eine finanzielle Wesentlichkeitsanalyse durch und lässt die Auswirkungswesentlichkeit aus. Welcher ESRS-Standard wird verletzt?"},
        {"type": "definition", "q": "Was ist IRO (Impact, Risk, Opportunity) und in welchem Verhältnis steht es zur doppelten Wesentlichkeit?"},
    ],
    "tcfd": [
        {"type": "definition", "q": "Was sind die 4 TCFD-Säulen — Governance, Strategie, Risikomanagement und welche ist die vierte?"},
        {"type": "application", "q": "Ein Unternehmen nutzt TCFD als Rahmen für die Klimaberichterstattung. Reicht dies für die Einhaltung von ESRS E1 aus?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen physischen Klimarisiken und Übergangsklimakrisiken nach TCFD?"},
        {"type": "case", "q": "Ein Investor fordert TCFD-konforme Offenlegungen. Das Unternehmen hat keine Klimastrategie. Was muss es mindestens offenlegen?"},
    ],
    "cjeu_cases": [
        {"type": "definition", "q": "Was wurde in der Rs. C-237/07 (Janecek) zum Verhältnis von EU-Umweltrecht und individuellen Rechten entschieden?"},
        {"type": "definition", "q": "Welche Bedeutung haben Klimaklagen im Stil von Urgenda für EU-Umweltrechtsverpflichtungen?"},
        {"type": "application", "q": "Ein Mitgliedstaat setzt eine EU-Umweltrichtlinie nicht um. Was kann ein Unternehmen nach EuGH-Rechtsprechung tun?"},
        {"type": "definition", "q": "Was ist das Francovich-Prinzip und wann kann ein Unternehmen Schadensersatz vom Staat verlangen?"},
    ],
    "cs3d": [
        {"type": "definition", "q": "Was ist die CS3D und wie unterscheidet sie sich vom LkSG?"},
        {"type": "application", "q": "Ein Unternehmen mit 1.000 EU-Mitarbeitern und €450 Mio. Umsatz — gilt CS3D?"},
        {"type": "definition", "q": "Verpflichtet die CS3D Unternehmen nur zur Überwachung unmittelbarer Lieferanten oder der gesamten Wertschöpfungskette?"},
        {"type": "case", "q": "Ein Tier-2-Lieferant eines Unternehmens verstößt gegen ILO-Übereinkommen. Was muss das Unternehmen nach CS3D tun?"},
    ],
    "hgb": [
        {"type": "definition", "q": "Was ist der Lagebericht nach HGB und wer ist zur Erstellung verpflichtet?"},
        {"type": "application", "q": "Eine deutsche GmbH hat €6 Mio. Umsatz und 25 Mitarbeiter. Welche HGB-Größenklasse gilt?"},
        {"type": "definition", "q": "Was ist der Grundsatz der Vorsicht in der HGB-Rechnungslegung?"},
        {"type": "case", "q": "Ein Unternehmen wechselt von HGB zu IFRS. Welche HGB-Offenlegungspflichten gelten?"},
    ],
    "ksg": [
        {"type": "definition", "q": "Welche jährlichen CO₂-Minderungsziele setzt das KSG und für welche Sektoren?"},
        {"type": "application", "q": "Der deutsche Verkehrssektor überschreitet sein KSG-Jahresemissionsbudget. Welche Rechtsfolge tritt ein?"},
        {"type": "definition", "q": "Was ist das Klimaschutzprogramm und welche Bundesbehörde ist dafür verantwortlich?"},
    ],
    "behg": [
        {"type": "definition", "q": "Welche Brennstoffe erfasst das BEHG und ab welchem Jahr begann die nationale CO₂-Bepreisung?"},
        {"type": "application", "q": "Ein Heizöllieferant vertreibt 500.000 Tonnen CO₂-Äquivalent. Was sind seine BEHG-Pflichten?"},
        {"type": "definition", "q": "Wie verhält sich das BEHG zum EU-ETS — können Emissionen doppelt angerechnet werden?"},
    ],
    "gri": [
        {"type": "definition", "q": "Was sind die GRI Universal Standards und in welchem Verhältnis stehen sie zu den themenbezogenen Standards?"},
        {"type": "application", "q": "Ein Unternehmen verwendet GRI-Standards für seinen Nachhaltigkeitsbericht. Reicht dies für die CSRD-Konformität aus?"},
        {"type": "definition", "q": "Was ist das GRI-Wesentlichkeitsprinzip und wie unterscheidet es sich von der ESRS-doppelten Wesentlichkeit?"},
    ],
    "issb": [
        {"type": "definition", "q": "Was ist der Unterschied zwischen IFRS S1 und IFRS S2?"},
        {"type": "application", "q": "Ein EU-börsennotiertes Unternehmen berichtet bereits nach ISSB. Erfüllt dies die ESRS-Anforderungen?"},
        {"type": "definition", "q": "Welche Jurisdiktion hat als erste ISSB-konforme Berichterstattung verpflichtend eingeführt und ab wann?"},
    ],
    "eu_whistleblower": [
        {"type": "definition", "q": "Welche Unternehmen müssen nach der EU-Hinweisgeberschutzrichtlinie interne Meldekanäle einrichten?"},
        {"type": "application", "q": "Ein Mitarbeiter meldet CSRD-Betrug intern und wird anschließend benachteiligt. Welchen Schutz bietet die Richtlinie?"},
        {"type": "definition", "q": "Bis wann mussten die Mitgliedstaaten die EU-Hinweisgeberschutzrichtlinie umsetzen?"},
    ],
    "reach": [
        {"type": "definition", "q": "Was verpflichtet REACH Unternehmen bei chemischen Stoffen ab 1 Tonne pro Jahr zu tun?"},
        {"type": "application", "q": "Ein Unternehmen importiert ein Produkt mit SVHC-Anteilen über 0,1 Gewichtsprozent. Welche REACH-Pflicht gilt?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen REACH-Registrierung, -Zulassung und -Beschränkung?"},
    ],
    "eu_competition": [
        {"type": "definition", "q": "Was verbietet AEUV Art. 101 und was ist die Ausnahme nach Art. 101 Abs. 3?"},
        {"type": "application", "q": "Zwei Wettbewerber vereinbaren den Austausch von Nachhaltigkeitskostendaten. Könnte dies Art. 101 verletzen?"},
        {"type": "definition", "q": "Was ist die Marktbeherrschungsschwelle im EU-Wettbewerbsrecht und was verbietet Art. 102?"},
        {"type": "case", "q": "Ein großes Technologieunternehmen verweigert einem Nachhaltigkeitsdatenanbieter den Plattformzugang. Welcher AEUV-Artikel greift?"},
    ],
    "mifid2": [
        {"type": "definition", "q": "Welche Nachhaltigkeitsänderungen hat MiFID II erhalten und ab wann gelten sie?"},
        {"type": "application", "q": "Ein Anlageberater fragt Kunden nicht nach ESG-Präferenzen. Ist das ab 2022 MiFID-II-konform?"},
        {"type": "definition", "q": "Was ist eine Nachhaltigkeitspräferenz nach MiFID II und welche drei Optionen hat ein Kunde?"},
    ],
    "ied": [
        {"type": "definition", "q": "Was ist eine Beste Verfügbare Technik (BVT) nach der Industrieemissionsrichtlinie und wer legt sie fest?"},
        {"type": "application", "q": "Eine Anlage überschreitet die IED-Emissionsgrenzwerte. Wie reagiert die zuständige Behörde?"},
        {"type": "definition", "q": "Welche Industrieanlagen benötigen in Deutschland eine IED-Genehmigung?"},
    ],
    "srd2": [
        {"type": "definition", "q": "Welche Aktionärsengagementverpflichtungen legt SRD II institutionellen Investoren auf?"},
        {"type": "application", "q": "Ein Unternehmen vergütet seinen CEO mit dem 300-fachen des Medianlohns der Mitarbeiter. Welche SRD-II-Offenlegung ist erforderlich?"},
        {"type": "definition", "q": "Was ist eine Transaktion mit nahestehenden Parteien nach SRD II und wann ist Aktionärsgenehmigung erforderlich?"},
    ],
    # Neue Themen
    "teu": [
        {"type": "definition", "q": "Was sind die fünf Grundwerte der EU nach Art. 2 TEU?"},
        {"type": "definition", "q": "Was regelt Art. 50 TEU und was sind seine Voraussetzungen?"},
        {"type": "application", "q": "Die Kommission leitet ein Vertragsverletzungsverfahren ein. Auf welcher TEU/AEUV-Grundlage?"},
        {"type": "definition", "q": "Was ist das Prinzip der begrenzten Einzelermächtigung nach Art. 5 TEU?"},
    ],
    "tfeu": [
        {"type": "definition", "q": "Was sind die vier Grundfreiheiten des AEUV?"},
        {"type": "application", "q": "Deutschland verbietet Importe eines in Frankreich zugelassenen Lebensmittels. Welcher AEUV-Artikel ist betroffen?"},
        {"type": "definition", "q": "Was regeln AEUV Art. 101 und 102 und wer überwacht ihre Einhaltung?"},
        {"type": "definition", "q": "Was ist das ordentliche Gesetzgebungsverfahren nach Art. 294 AEUV?"},
    ],
    "eu_charter": [
        {"type": "definition", "q": "Wann wurde die EU-Grundrechtecharta rechtlich verbindlich und in welchem Verhältnis steht sie zur EMRK?"},
        {"type": "application", "q": "Ein Unternehmen verarbeitet personenbezogene Daten im Auftrag einer Behörde. Welches Chartagrundrecht ist berührt?"},
        {"type": "definition", "q": "Was unterscheidet Rechte von Grundsätzen in der EU-Grundrechtecharta?"},
    ],
    "eu_legislative": [
        {"type": "definition", "q": "Was ist der Trilog und welche drei Institutionen nehmen daran teil?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen einem EU-Beschluss und einer EU-Empfehlung?"},
        {"type": "application", "q": "Die Kommission schlägt eine Richtlinie vor. Parlament lehnt sie ab. Was kann die Kommission tun?"},
    ],
    "van_gend_loos": [
        {"type": "definition", "q": "Was entschied der EuGH in Van Gend en Loos (1963) zur unmittelbaren Wirkung des EU-Rechts?"},
        {"type": "application", "q": "Ein Unternehmen beruft sich direkt auf eine EU-Verordnung vor einem deutschen Gericht. Ist dies möglich? Welches Urteil begründet das?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen unmittelbarer Wirkung und Vorrang des EU-Rechts?"},
    ],
    "costa_enel": [
        {"type": "definition", "q": "Warum begründete das Costa-v-ENEL-Urteil (1964) den Vorrang des EU-Rechts vor nationalem Recht?"},
        {"type": "application", "q": "Ein nationales Gesetz widerspricht einer EU-Verordnung. Welches Recht hat Vorrang und auf welches Urteil stützt sich dies?"},
        {"type": "case", "q": "Deutschland erlässt ein Gesetz, das einer bereits geltenden EU-Richtlinie widerspricht. Was muss ein deutsches Gericht tun?"},
    ],
    "cassis_dijon": [
        {"type": "definition", "q": "Was ist das Prinzip der gegenseitigen Anerkennung nach Cassis de Dijon (1979)?"},
        {"type": "application", "q": "Frankreich verbietet den Verkauf eines in Deutschland zugelassenen Produkts. Welche Cassis-Grundsätze greifen?"},
        {"type": "definition", "q": "Welche vier zwingenden Erfordernisse erkannte der EuGH in Cassis de Dijon als Ausnahme vom freien Warenverkehr an?"},
    ],
    "francovich": [
        {"type": "definition", "q": "Was ist das Francovich-Prinzip (1991) und unter welchen drei Voraussetzungen haftet ein Mitgliedstaat?"},
        {"type": "application", "q": "Deutschland setzt eine Insolvenzschutzrichtlinie nicht um und ein Arbeitnehmer erleidet einen Schaden. Was kann er verlangen?"},
        {"type": "case", "q": "Ein Unternehmen erleidet Schäden, weil ein Mitgliedstaat eine EU-Richtlinie falsch umgesetzt hat. Welche Ansprüche hat es?"},
    ],
    "schrems": [
        {"type": "definition", "q": "Was haben Schrems I (2015) und Schrems II (2020) für den Datentransfer in die USA bedeutet?"},
        {"type": "application", "q": "Ein Unternehmen überträgt EU-Kundendaten in die USA auf Basis von Standardvertragsklauseln. Welche Zusatzmaßnahmen verlangt Schrems II?"},
        {"type": "definition", "q": "Was ist das EU-US-Datenschutzrahmenwerk (Data Privacy Framework) und warum wurde es nach Schrems II eingeführt?"},
    ],
    "google_spain": [
        {"type": "definition", "q": "Was entschied der EuGH in Google Spain (2014) zum Recht auf Vergessenwerden?"},
        {"type": "application", "q": "Eine Person beantragt bei Google die Entfernung veralteter Suchergebnisse. Unter welchen Voraussetzungen muss Google nachkommen?"},
        {"type": "definition", "q": "Wie verhält sich das Recht auf Vergessenwerden aus Google Spain zum DSGVO Art. 17?"},
    ],
    "eu_commission": [
        {"type": "definition", "q": "Was ist das Initiativmonopol der Kommission und warum hat sie es?"},
        {"type": "application", "q": "Die Kommission vermutet staatliche Beihilfen durch Deutschland. Welches Verfahren leitet sie ein?"},
        {"type": "definition", "q": "Welche drei Hauptaufgaben hat die Europäische Kommission nach den Verträgen?"},
    ],
    "eu_parliament": [
        {"type": "definition", "q": "Wie viele Abgeordnete hat das Europäische Parlament und wie werden sie gewählt?"},
        {"type": "application", "q": "Rat und Parlament sind sich über einen Richtlinientext uneinig. Was passiert im ordentlichen Gesetzgebungsverfahren?"},
        {"type": "definition", "q": "Welche Haushaltsbefugnisse hat das Europäische Parlament?"},
    ],
    "cjeu_court": [
        {"type": "definition", "q": "Was ist ein Vorabentscheidungsverfahren nach Art. 267 AEUV und wer kann es einleiten?"},
        {"type": "application", "q": "Ein deutsches Gericht zweifelt an der Auslegung einer EU-Richtlinie. Muss es den EuGH anrufen?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen EuGH (Gerichtshof) und EuG (Gericht) bei EU-Streitigkeiten?"},
    ],
    "ai_act": [
        {"type": "definition", "q": "Welche vier Risikostufen unterscheidet das EU AI-Gesetz für KI-Systeme?"},
        {"type": "application", "q": "Ein Unternehmen setzt KI zur Kreditwürdigkeitsprüfung ein. Welche Risikostufe gilt nach dem AI-Gesetz?"},
        {"type": "definition", "q": "Was sind Allzweck-KI-Modelle (GPAI) nach dem EU AI-Gesetz und welche Pflichten treffen ihre Anbieter?"},
    ],
    "nis2": [
        {"type": "definition", "q": "Welche Unternehmen gelten als 'wesentliche Einrichtungen' nach NIS2 und welche Sektoren sind erfasst?"},
        {"type": "application", "q": "Ein mittelgroßes Energieunternehmen erleidet einen Cyberangriff. Welche NIS2-Meldepflichten gelten?"},
        {"type": "definition", "q": "Was ist der Unterschied zwischen wesentlichen und wichtigen Einrichtungen nach NIS2?"},
    ],
}

# ── 6-perspective extensions ────────────────────────────────────────────────────

_QUESTION_BANK["eu_taxonomy"].extend([
    {"type": "student", "q": "Erkläre die EU-Taxonomie in einfachen Worten — was klassifiziert sie und warum?"},
    {"type": "student", "q": "Was ist der Unterschied zwischen 'Klimaschutz' und 'Klimaanpassung' als Umweltziele der EU-Taxonomie?"},
    {"type": "teacher", "q": "Zeige anhand eines Windenergieprojekts, wie die drei Taxonomiekriterien (wesentlicher Beitrag, DNSH, Mindestschutz) geprüft werden."},
    {"type": "teacher", "q": "Erkläre mit einem einfachen Beispiel, was 'Do No Significant Harm' (DNSH) in der Praxis bedeutet."},
    {"type": "lawyer", "q": "Welche vier kumulativen Voraussetzungen muss eine Wirtschaftstätigkeit nach Art. 3 EU-Taxonomie-VO erfüllen?"},
    {"type": "lawyer", "q": "Was genau müssen Nicht-Finanzunternehmen mit mehr als 500 Mitarbeitern nach Art. 8 der Taxonomie-Offenlegungsverordnung offenlegen?"},
    {"type": "business_owner", "q": "Muss ich als produzierendes Unternehmen Taxonomiequoten offenlegen und wenn ja, welche KPIs?"},
    {"type": "business_owner", "q": "Unser Unternehmen hat keine Taxonomie-eligible Aktivitäten. Welche Erklärung müssen wir im CSRD-Bericht abgeben?"},
    {"type": "court", "q": "Wie ist 'wesentlicher Beitrag' nach Art. 10 EU-Taxonomie-VO auszulegen, wenn delegierte Rechtsakte keine Grenzwerte für eine Aktivität festlegen?"},
    {"type": "ecj", "q": "Ist die Einbeziehung von Erdgas und Kernenergie als Übergangstätigkeiten mit dem Nachhaltigkeitsprinzip nach Art. 3 Abs. 3 TEU vereinbar?"},
])

_QUESTION_BANK["sfdr"].extend([
    {"type": "student", "q": "Was ist SFDR und warum unterscheidet sie Produkte in Artikel 6, 8 und 9?"},
    {"type": "student", "q": "Erkläre den Begriff 'Principal Adverse Impacts' (PAI) — was sind Hauptnachteile für Nachhaltigkeitsfaktoren?"},
    {"type": "teacher", "q": "Gib ein Lehrbeispiel für einen Artikel-8-Fonds vs. Artikel-9-Fonds — wie unterscheiden sie sich in Praxis und Offenlegungspflichten?"},
    {"type": "lawyer", "q": "Was fordert SFDR Art. 9 von einem Produkt, das als 'Fonds mit nachhaltigem Investment' klassifiziert wird — alle Voraussetzungen?"},
    {"type": "lawyer", "q": "Welche Informationen sind nach SFDR Art. 6 zu Nachhaltigkeitsrisiken in vorvertraglichen Unterlagen verpflichtend?"},
    {"type": "business_owner", "q": "Ich biete Vermögensverwaltung für Privatkunden an — falle ich unter SFDR und was muss ich auf meiner Website veröffentlichen?"},
    {"type": "business_owner", "q": "Unser Artikel-8-Fonds hält eine Anleihe ohne E/S-Ziel. Verlieren wir die Klassifizierung?"},
    {"type": "court", "q": "Wie ist 'nachhaltige Investition' in Art. 2 Nr. 17 SFDR auszulegen, wenn keine verbindlichen Mindestkriterien festgelegt sind?"},
    {"type": "ecj", "q": "Verstößt die SFDR gegen den Grundsatz der Rechtssicherheit, weil der Begriff 'nachhaltige Investition' keine klare Legaldefinition hat?"},
])

_QUESTION_BANK["cs3d"].extend([
    {"type": "student", "q": "Was ist die CS3D und wie unterscheidet sie sich grundlegend vom deutschen LkSG?"},
    {"type": "student", "q": "Welche Unternehmen fallen unter die CS3D — erkläre die Schwellenwerte für Anfänger."},
    {"type": "teacher", "q": "Erkläre anhand einer globalen Lieferkette, welche Sorgfaltspflichten die CS3D von Unternehmen verlangt."},
    {"type": "lawyer", "q": "Was fordert CS3D Art. 5 zum Sorgfaltspflichtensystem — welche 6 Schritte sind vorgesehen?"},
    {"type": "lawyer", "q": "Welche zivilrechtliche Haftung sieht CS3D Art. 22 für Unternehmen vor, die Sorgfaltspflichten verletzen?"},
    {"type": "business_owner", "q": "Mein Unternehmen hat €450 Mio. Umsatz und 1.200 EU-Mitarbeiter — falle ich unter CS3D und ab wann?"},
    {"type": "business_owner", "q": "Was sind die ersten drei Schritte für CS3D-Compliance, die ich heute einleiten muss?"},
    {"type": "court", "q": "Wie ist CS3D Art. 22 zur zivilrechtlichen Haftung auszulegen, wenn der Schaden durch einen Tier-3-Lieferanten verursacht wurde?"},
    {"type": "ecj", "q": "Steht die CS3D-Haftungsregelung (Art. 22) im Einklang mit dem Verhältnismäßigkeitsprinzip, angesichts der globalen Lieferkettenausdehnung?"},
])

_QUESTION_BANK["eudr"] = [
    {"type": "definition", "q": "Was ist die EU-Entwaldungsverordnung (EUDR) und welche 7 Rohstoffkategorien deckt sie ab?"},
    {"type": "definition", "q": "Was bedeutet 'entwaldungsfrei' nach EUDR und welcher Stichtag gilt für die Landnutzung?"},
    {"type": "application", "q": "Ein Unternehmen importiert Palmöl aus Indonesien. Welche EUDR-Sorgfaltspflichten muss es erfüllen?"},
    {"type": "case", "q": "Ein Händler kann für seinen Kakaolieferanten keine GPS-Koordinaten der Herkunftsflächen vorlegen. Welche EUDR-Konsequenzen drohen?"},
    {"type": "student", "q": "Was ist die EUDR in einfachen Worten — warum gibt es sie und was soll sie verhindern?"},
    {"type": "student", "q": "Was bedeutet 'Entwaldungsfreiheit' nach EUDR — was müssen Unternehmen nachweisen?"},
    {"type": "teacher", "q": "Erkläre anhand eines Schokoladenherstellers, wie die EUDR-Sorgfaltserklärung in der Praxis funktioniert."},
    {"type": "lawyer", "q": "Was sind die drei Schritte der EUDR-Sorgfaltspflicht nach Art. 8–10 und welche Dokumentation ist erforderlich?"},
    {"type": "lawyer", "q": "Welche Sanktionen sieht Art. 25 EUDR vor und wie hoch sind die Mindestbußgelder?"},
    {"type": "business_owner", "q": "Ich importiere Kaffee aus Brasilien — falle ich unter die EUDR und was muss ich bis Ende 2025 einrichten?"},
    {"type": "business_owner", "q": "Was ist die EUDR-Sorgfaltserklärung und wer ist für ihre Einreichung verantwortlich?"},
    {"type": "court", "q": "Wie ist der Begriff 'Betreiber' in der EUDR auszulegen, wenn ein Unternehmen Zwischenhändler in der Lieferkette ist?"},
    {"type": "ecj", "q": "Ist das EUDR-Marktverbot (Art. 3) verhältnismäßig im Hinblick auf die Handelsfreiheit nach AEUV Art. 34 ff.?"},
]

_QUESTION_BANK["green_deal"] = [
    {"type": "definition", "q": "Was ist der Europäische Green Deal und welche Hauptziele hat er bis 2050?"},
    {"type": "definition", "q": "Was ist das 'Fit for 55'-Paket und wie hängt es mit dem Green Deal zusammen?"},
    {"type": "application", "q": "Ein Unternehmen der Stahlindustrie plant eine neue Anlage. Welche Green-Deal-Rechtsakte sind relevant?"},
    {"type": "case", "q": "Ein Mitgliedstaat verzögert die Umsetzung von Green-Deal-Richtlinien. Welche Konsequenzen drohen?"},
    {"type": "student", "q": "Erkläre den Europäischen Green Deal in 3 Sätzen — was ist das Ziel und welche Instrumente nutzt die EU?"},
    {"type": "student", "q": "Wie hängen CSRD, EU-Taxonomie und Green Deal zusammen — erkläre den Zusammenhang."},
    {"type": "teacher", "q": "Erkläre anhand von 'Fit for 55', wie der Green Deal konkrete Gesetzgebung erzeugt."},
    {"type": "lawyer", "q": "Welchen rechtlichen Status hat der Green Deal — ist er verbindliches Recht oder politisches Programm?"},
    {"type": "lawyer", "q": "Welches Primärrecht (TEU/AEUV) bildet die Rechtsgrundlage für Green-Deal-Maßnahmen?"},
    {"type": "business_owner", "q": "Wie wirkt sich der Green Deal konkret auf ein produzierendes Unternehmen aus — welche Gesetze muss ich kennen?"},
    {"type": "business_owner", "q": "Was ist das EU-Klimagesetz und welche verbindliche Verpflichtung ergibt sich für mein Unternehmen?"},
    {"type": "court", "q": "Hat der European Green Deal als Mitteilung der Kommission unmittelbare Rechtswirkung oder nur die darauf basierenden Einzelmaßnahmen?"},
    {"type": "ecj", "q": "Inwiefern kann der Grundsatz der Klimaneutralität aus dem EU-Klimagesetz als Auslegungsmaßstab für andere EU-Umweltrechtsakte dienen?"},
]

_QUESTION_BANK["ied"].extend([
    {"type": "student", "q": "Was ist die Industrieemissionsrichtlinie (IED) in einfachen Worten — welche Anlagen sind betroffen?"},
    {"type": "student", "q": "Was ist 'Beste Verfügbare Technik' (BVT) und warum ist sie das Herzstück der IED?"},
    {"type": "teacher", "q": "Erkläre anhand einer Zementfabrik, wie eine IED-Genehmigung beantragt und überwacht wird."},
    {"type": "lawyer", "q": "Was sind BVT-Schlussfolgerungen nach IED Art. 13 und welche Rechtswirkung haben sie für Genehmigungen?"},
    {"type": "lawyer", "q": "Welche Sanktionen und Berichtspflichten sieht die IED vor, wenn Emissionsgrenzwerte überschritten werden?"},
    {"type": "business_owner", "q": "Meine Anlage produziert 50.000 Tonnen Stahl/Jahr — falle ich unter die IED und welche Genehmigung brauche ich?"},
    {"type": "business_owner", "q": "Welche Behörde ist in Deutschland für IED-Genehmigungen zuständig?"},
    {"type": "court", "q": "Wie ist 'Stand der Technik' nach IED auszulegen, wenn BVT-Schlussfolgerungen eine bestimmte Technologie nicht explizit erwähnen?"},
    {"type": "ecj", "q": "Kann ein Einzelner (Anwohner) aus IED-Emissionsgrenzwerten direkt Ansprüche gegen eine Anlage geltend machen?"},
])

_QUESTION_BANK["reach"].extend([
    {"type": "student", "q": "Was ist REACH in einfachen Worten — was müssen Unternehmen mit chemischen Stoffen tun?"},
    {"type": "student", "q": "Erkläre den Unterschied zwischen REACH-Registrierung, Zulassung und Beschränkung."},
    {"type": "teacher", "q": "Zeige anhand eines Chemikalienproduzenten mit einem Stoff über 10 t/Jahr, was REACH-Registrierung bedeutet."},
    {"type": "lawyer", "q": "Was sind 'besonders besorgniserregende Stoffe' (SVHC) nach REACH Art. 57 und wie werden sie in die Kandidatenliste aufgenommen?"},
    {"type": "lawyer", "q": "Welche Mitteilungspflichten hat ein Importeur nach REACH Art. 7 für Erzeugnisse mit SVHC-Anteilen über 0,1 Gewichtsprozent?"},
    {"type": "business_owner", "q": "Wir importieren Textilien aus China — welche REACH-Pflichten haben wir als Importeur?"},
    {"type": "business_owner", "q": "Welche Behörde überwacht REACH in Deutschland und welche Sanktionen drohen bei Verstößen?"},
    {"type": "court", "q": "Wie ist die REACH-Zulassungspflicht nach Art. 56 auszulegen, wenn eine Substitutionsmöglichkeit für SVHC nur theoretisch besteht?"},
    {"type": "ecj", "q": "Steht die REACH-Zulassungspflicht im Einklang mit dem Verhältnismäßigkeitsprinzip, wenn sie KMU stark belastet?"},
])

_QUESTION_BANK["mifid2"].extend([
    {"type": "student", "q": "Was ist MiFID II und welche Finanzdienstleistungen reguliert sie?"},
    {"type": "student", "q": "Was bedeutet die ESG-Integrationsanforderung in MiFID II für Anlageberater?"},
    {"type": "teacher", "q": "Erkläre anhand eines Beratungsgesprächs, wie ein Berater seit 2022 Nachhaltigkeitspräferenzen abfragen muss."},
    {"type": "lawyer", "q": "Was fordert MiFID II Art. 25 Abs. 2 seit der ESG-Änderung 2022 zur Geeignetheitsprüfung?"},
    {"type": "lawyer", "q": "Was sind die drei Nachhaltigkeitspräferenzoptionen nach MiFID II und wie müssen Berater sie dokumentieren?"},
    {"type": "business_owner", "q": "Mein Beratungsunternehmen berät Privatkunden bei Wertpapieranlagen — welche ESG-Pflichten muss ich seit 2022 erfüllen?"},
    {"type": "business_owner", "q": "Was passiert, wenn ich als Berater die ESG-Präferenzabfrage beim Kunden unterlasse?"},
    {"type": "court", "q": "Wie ist 'Nachhaltigkeitspräferenz' in MiFID II auszulegen, wenn ein Kunde keine klare Präferenz hat?"},
    {"type": "ecj", "q": "Ist die MiFID-II-ESG-Integrationsanforderung mit dem Grundsatz der Vertragsfreiheit und der Anlagefreiheit vereinbar?"},
])

_QUESTION_BANK["srd2"].extend([
    {"type": "student", "q": "Was ist die Aktionärsrechterichtlinie II (SRD II) und welche Aktionärsrechte stärkt sie?"},
    {"type": "student", "q": "Was bedeutet 'Say on Pay' nach SRD II — haben Aktionäre ein verbindliches Stimmrecht über Vorstandsvergütung?"},
    {"type": "teacher", "q": "Erkläre anhand einer börsennotierten AG, wie das Vergütungssystem nach SRD II genehmigt werden muss."},
    {"type": "lawyer", "q": "Was fordert SRD II Art. 9a zur Aktionärsstimmabgabe über die Vergütungspolitik des Vorstands?"},
    {"type": "lawyer", "q": "Welche Offenlegungspflichten bei Transaktionen mit nahestehenden Parteien sieht SRD II Art. 9c vor?"},
    {"type": "business_owner", "q": "Unsere AG ist an der Frankfurter Börse notiert — welche SRD-II-Pflichten treffen uns jedes Jahr?"},
    {"type": "business_owner", "q": "Was ist der Unterschied zwischen Vergütungsbericht und Vergütungspolitik nach SRD II?"},
    {"type": "court", "q": "Wie ist SRD II Art. 9c zu nahestehenden Parteien auszulegen, wenn ein Vorstandsmitglied gleichzeitig Hauptaktionär ist?"},
    {"type": "ecj", "q": "Steht das SRD-II-Stimmrecht über Vergütungspolitik im Einklang mit dem Eigentumsrecht nach Art. 17 EU-Grundrechtecharta?"},
])

_QUESTION_BANK["eu_whistleblower"].extend([
    {"type": "student", "q": "Was ist die EU-Hinweisgeberschutzrichtlinie und wen schützt sie?"},
    {"type": "student", "q": "Erkläre den Unterschied zwischen internem und externem Meldekanal nach der Richtlinie."},
    {"type": "teacher", "q": "Zeige anhand eines Unternehmens mit 250 Mitarbeitern, wie ein konformes Hinweisgebersystem eingerichtet wird."},
    {"type": "lawyer", "q": "Welche Arten von Hinweisgebern schützt Richtlinie 2019/1937 und gegen welche Vergeltungsmaßnahmen?"},
    {"type": "lawyer", "q": "Was fordert Richtlinie 2019/1937 Art. 9 zu internen Meldekanälen — Vertraulichkeit, Fristen, Rückmeldung?"},
    {"type": "business_owner", "q": "Mein Unternehmen hat 60 Mitarbeiter — bin ich verpflichtet, einen internen Meldekanal einzurichten?"},
    {"type": "business_owner", "q": "Was passiert, wenn ich als Unternehmen eine Hinweisgeberin nach ihrer Meldung entlasse?"},
    {"type": "court", "q": "Wie ist der Schutzbereich der Richtlinie auszulegen, wenn ein Hinweisgeber Informationen durch unbefugten Zugang erlangt hat?"},
    {"type": "ecj", "q": "Steht der Schutz anonymer Hinweisgeber nach der EU-Richtlinie im Einklang mit dem Recht auf effektiven Rechtsschutz?"},
])

_QUESTION_BANK["eu_competition"].extend([
    {"type": "student", "q": "Was verbietet EU-Wettbewerbsrecht nach AEUV Art. 101 und 102 — erkläre es mit einem einfachen Beispiel."},
    {"type": "student", "q": "Was ist der Unterschied zwischen einem Kartell (Art. 101 AEUV) und dem Missbrauch einer marktbeherrschenden Stellung (Art. 102)?"},
    {"type": "teacher", "q": "Erkläre anhand eines Preisabsprache-Beispiels, wie die EU-Kommission einen Art.-101-Fall untersucht."},
    {"type": "lawyer", "q": "Was sind die vier Voraussetzungen für eine Freistellung nach Art. 101 Abs. 3 AEUV?"},
    {"type": "lawyer", "q": "Unter welchen Voraussetzungen kann die Kommission nach der EU-Fusionskontrollverordnung einen Zusammenschluss untersagen?"},
    {"type": "business_owner", "q": "Dürfen wir als Branchenteilnehmer Nachhaltigkeitskostendaten mit Wettbewerbern teilen, ohne Art. 101 zu verletzen?"},
    {"type": "business_owner", "q": "Wie hoch können EU-Kartellgeldbußen maximal sein und wie berechnet die Kommission sie?"},
    {"type": "court", "q": "Wie ist Art. 102 AEUV auszulegen, wenn ein marktbeherrschendes Unternehmen nachhaltigkeitsbezogene Anforderungen an Lieferanten stellt?"},
    {"type": "ecj", "q": "Inwiefern können nachhaltigkeitsbezogene Vereinbarungen zwischen Wettbewerbern unter Art. 101 Abs. 3 AEUV freigestellt werden?"},
])

_QUESTION_BANK["lksg"].extend([
    {"type": "student", "q": "Was ist das LkSG in einfachen Worten — welches Problem soll es lösen?"},
    {"type": "student", "q": "Was bedeutet 'angemessene Sorgfalt' nach LkSG — müssen Unternehmen Menschenrechtsverletzungen verhindern oder nur versuchen?"},
    {"type": "teacher", "q": "Erkläre anhand eines deutschen Automobilzulieferers, wie die LkSG-Risikoanalyse in der Praxis durchgeführt wird."},
    {"type": "lawyer", "q": "Was fordert § 5 LkSG zur Risikoanalyse — Umfang, Häufigkeit und Dokumentation?"},
    {"type": "lawyer", "q": "Was sieht § 24 LkSG als Sanktion vor und welche Behörde verhängt Bußgelder?"},
    {"type": "business_owner", "q": "Mein Unternehmen hat 3.500 Mitarbeiter — bin ich ab 2023 oder 2024 von LkSG betroffen?"},
    {"type": "business_owner", "q": "Was ist der Unterschied zwischen unmittelbaren Zulieferern (§ 3 LkSG) und mittelbaren Zulieferern (§ 9 LkSG)?"},
    {"type": "court", "q": "Können Betroffene nach LkSG direkte zivilrechtliche Ansprüche gegen deutsche Unternehmen geltend machen?"},
    {"type": "ecj", "q": "Wie verhält sich das LkSG zur CS3D — gilt das LkSG als ausreichende Vorwegnahme?"},
])

_QUESTION_BANK["behg"].extend([
    {"type": "student", "q": "Was ist das BEHG und wie funktioniert der nationale CO₂-Preis in Deutschland?"},
    {"type": "student", "q": "Warum gibt es ein nationales BEHG, wenn es bereits das EU-ETS gibt?"},
    {"type": "teacher", "q": "Erkläre anhand eines Heizöllieferanten, wie BEHG-Zertifikate erworben und abgegeben werden."},
    {"type": "lawyer", "q": "Welche Emissionsmengen fallen unter das BEHG und wer ist Inverkehrbringer nach § 3 BEHG?"},
    {"type": "lawyer", "q": "Was ist die jährliche BEHG-Zertifikatsabgabefrist und welche Sanktionen gelten bei Nichterfüllung?"},
    {"type": "business_owner", "q": "Ich betreibe Fernwärme mit Erdgas — welche BEHG-Pflichten treffen mich und wie berechne ich meine CO₂-Kosten?"},
    {"type": "business_owner", "q": "Gibt es BEHG-Ausnahmen oder Befreiungen für bestimmte Unternehmen?"},
    {"type": "court", "q": "Wie ist 'Inverkehrbringen' im BEHG auszulegen, wenn Kraftstoff grenzüberschreitend geliefert wird?"},
    {"type": "ecj", "q": "Ist das BEHG mit EU-Beihilferecht vereinbar, wenn bestimmte Sektoren von der CO₂-Bepreisung ausgenommen sind?"},
])

_QUESTION_BANK["ksg"].extend([
    {"type": "student", "q": "Was ist das deutsche Klimaschutzgesetz (KSG) und welche Ziele setzt es?"},
    {"type": "student", "q": "Was ist ein 'Jahresemissionsbudget' nach KSG und was passiert, wenn ein Sektor es überschreitet?"},
    {"type": "teacher", "q": "Erkläre, wie die Sektorziele des KSG (Verkehr, Gebäude, Energie) kontrolliert und durchgesetzt werden."},
    {"type": "lawyer", "q": "Was ordnet § 8 KSG an, wenn ein Sektor das Jahresemissionsbudget überschreitet?"},
    {"type": "lawyer", "q": "Welche Behörde überwacht die KSG-Zielerreichung und welche Rechtswirkung haben KSG-Sofortprogramme?"},
    {"type": "business_owner", "q": "Hat das KSG direkte Auswirkungen auf mein Unternehmen oder nur auf den Staat?"},
    {"type": "business_owner", "q": "Wie hängen KSG-Sektorziele und BEHG-CO₂-Preis in der Praxis zusammen?"},
    {"type": "court", "q": "Können NGOs aufgrund des KSG Klagen gegen den deutschen Staat einreichen? (vgl. Neubauer-Urteil BVerfG)"},
    {"type": "ecj", "q": "Ist das KSG mit dem europäischen Klimagesetz (Verordnung 2021/1119) vereinbar und besteht ein Umsetzungsvorrang?"},
])

_QUESTION_BANK["german_corporate"].extend([
    {"type": "student", "q": "Was ist der Unterschied zwischen GmbH und AG nach deutschem Recht — wann wählt man welche?"},
    {"type": "student", "q": "Was ist der Aufsichtsrat in einer deutschen AG und warum gibt es ihn?"},
    {"type": "teacher", "q": "Erkläre anhand einer Unternehmensübernahme, welche Organe nach AktG zustimmen müssen."},
    {"type": "lawyer", "q": "Was ist die Business Judgment Rule nach § 93 Abs. 1 S. 2 AktG und wann schützt sie Vorstandsmitglieder?"},
    {"type": "lawyer", "q": "Was sieht § 119 AktG zur Hauptversammlung vor und welche Beschlüsse sind der HV vorbehalten?"},
    {"type": "business_owner", "q": "Ich möchte meine GmbH in eine AG umwandeln — welche Schritte sind nach deutschem Recht erforderlich?"},
    {"type": "business_owner", "q": "Was ist das Mindeststammkapital einer GmbH und welche Haftung habe ich als Gesellschafter?"},
    {"type": "court", "q": "Wie ist die Treuepflicht von Gesellschaftern nach GmbHG auszulegen, wenn ein Mehrheitsgesellschafter Minderheitsinteressen ignoriert?"},
    {"type": "ecj", "q": "Steht die deutsche Mitbestimmungsregelung (paritätischer Aufsichtsrat) im Einklang mit der EU-Niederlassungsfreiheit nach AEUV Art. 49?"},
])

_QUESTION_BANK["bgb_contracts"].extend([
    {"type": "student", "q": "Wie entsteht ein Vertrag nach BGB — erkläre Angebot und Annahme in einfachen Worten."},
    {"type": "student", "q": "Was ist der Unterschied zwischen Nichtigkeit und Anfechtbarkeit eines Vertrags nach BGB?"},
    {"type": "teacher", "q": "Erkläre anhand eines Kaufvertrags über fehlerhafte Waren, welche Rechte der Käufer nach BGB hat."},
    {"type": "lawyer", "q": "Was sind die Voraussetzungen für einen Schadensersatzanspruch nach § 280 Abs. 1 BGB?"},
    {"type": "lawyer", "q": "Was regelt § 305 BGB zu AGB und wann ist eine AGB-Klausel nach § 307 BGB unwirksam?"},
    {"type": "business_owner", "q": "Mein Lieferant liefert mangelhaft und verweigert Nacherfüllung — welche BGB-Rechte habe ich und in welcher Reihenfolge?"},
    {"type": "business_owner", "q": "Was ist die Verjährungsfrist für Kaufvertragsansprüche nach BGB und ab wann beginnt sie?"},
    {"type": "court", "q": "Wie ist § 242 BGB (Treu und Glauben) als Generalklausel bei einem Vertragsverstoß auszulegen?"},
    {"type": "ecj", "q": "Inwiefern wird das deutsche BGB-Vertragsrecht durch EU-Richtlinien (z.B. Verbraucherrechte-RL) überlagert?"},
])

_QUESTION_BANK["gdpr"].extend([
    {"type": "student", "q": "Was ist die DSGVO in einfachen Worten — welche Rechte gibt sie Einzelpersonen?"},
    {"type": "student", "q": "Was ist der Unterschied zwischen Verantwortlichem und Auftragsverarbeiter nach DSGVO?"},
    {"type": "teacher", "q": "Erkläre anhand einer Kundendatenbank, welche DSGVO-Pflichten ein Unternehmen beim Aufbau erfüllen muss."},
    {"type": "lawyer", "q": "Was sind besondere Kategorien personenbezogener Daten nach Art. 9 DSGVO und welche Rechtsgrundlage ist für ihre Verarbeitung erforderlich?"},
    {"type": "lawyer", "q": "Was fordert Art. 13 DSGVO zur Informationspflicht — welche Informationen müssen bei Datenerhebung bereitgestellt werden?"},
    {"type": "business_owner", "q": "Mein Online-Shop nutzt Google Analytics — welche DSGVO-Anforderungen muss ich erfüllen?"},
    {"type": "business_owner", "q": "Was ist ein Auftragsverarbeitungsvertrag (AVV) und wann ist er Pflicht?"},
    {"type": "court", "q": "Wie ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse) auszulegen, wenn ein Unternehmen Marketing-Daten ohne Einwilligung verarbeitet?"},
    {"type": "ecj", "q": "Wie verhält sich Art. 17 DSGVO (Recht auf Löschung) zu nationalen Archivierungspflichten — welches Recht hat Vorrang?"},
])

_QUESTION_BANK["hgb"].extend([
    {"type": "student", "q": "Was ist das HGB und welche Unternehmen müssen nach HGB Bücher führen?"},
    {"type": "student", "q": "Was ist der Unterschied zwischen Jahresabschluss und Lagebericht nach HGB?"},
    {"type": "teacher", "q": "Erkläre anhand einer mittelgroßen GmbH, welche HGB-Pflichten zum Jahresabschluss bestehen und bis wann."},
    {"type": "lawyer", "q": "Was sind die HGB-Größenklassen (§ 267 HGB) und welche Offenlegungspflichten gelten für jede Klasse?"},
    {"type": "lawyer", "q": "Was fordert § 289c HGB zum nichtfinanziellen Bericht für große kapitalmarktorientierte Unternehmen?"},
    {"type": "business_owner", "q": "Meine GmbH hat €8 Mio. Umsatz und 55 Mitarbeiter — welche HGB-Abschluss- und Offenlegungspflichten habe ich?"},
    {"type": "business_owner", "q": "Bis wann muss ich meinen Jahresabschluss beim Bundesanzeiger einreichen und welche Strafe droht bei Verspätung?"},
    {"type": "court", "q": "Wie ist der handelsrechtliche Grundsatz der Vorsicht (§ 252 HGB) auszulegen, wenn ein Wertminderungsrisiko unsicher ist?"},
    {"type": "ecj", "q": "Wie verhält sich die HGB-Rechnungslegung zur IFRS-Pflicht für kapitalmarktorientierte Unternehmen nach der EU-IAS-Verordnung?"},
])

_QUESTION_BANK["eu_legal_terms"].extend([
    {"type": "student", "q": "Erkläre den Unterschied zwischen primärem EU-Recht (Verträge) und sekundärem EU-Recht (Richtlinien, Verordnungen)."},
    {"type": "student", "q": "Was ist eine Vorabentscheidung des EuGH und warum ist sie für nationale Gerichte bindend?"},
    {"type": "teacher", "q": "Erkläre anhand eines Beispiels, wie das Subsidiaritätsprinzip bestimmt, wer — EU oder Mitgliedstaat — gesetzgeberisch tätig werden darf."},
    {"type": "lawyer", "q": "Was ist der Grundsatz der richtlinienkonformen Auslegung und welche Grenzen hat er nach der EuGH-Rechtsprechung?"},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen unmittelbarer Anwendbarkeit einer EU-Verordnung und unmittelbarer Wirkung einer Richtlinienbestimmung?"},
    {"type": "business_owner", "q": "Was bedeutet es für mein Unternehmen, wenn eine EU-Verordnung direkt gilt, ohne nationale Umsetzung?"},
    {"type": "business_owner", "q": "Kann ich als Unternehmen ein EU-Recht vor einem deutschen Gericht geltend machen, auch wenn Deutschland es nicht umgesetzt hat?"},
    {"type": "court", "q": "Was ist die Pflicht zur richtlinienkonformen Auslegung nationalen Rechts und wo sind ihre Grenzen (contra legem)?"},
    {"type": "ecj", "q": "Was ist die Rewe/Comet-Doktrin und wie schützt das EU-Recht individuelle Rechte vor nationalen Verfahrenshindernissen?"},
])

_QUESTION_BANK["greenwashing_law"].extend([
    {"type": "student", "q": "Was ist Greenwashing und warum ist es nach EU-Recht verboten?"},
    {"type": "student", "q": "Was ist die EU-Richtlinie über Umweltaussagen (Green Claims Directive) — wann tritt sie in Kraft?"},
    {"type": "teacher", "q": "Erkläre anhand eines 'klimaneutral'-Labels, wie ein Unternehmen es legal verwenden kann."},
    {"type": "lawyer", "q": "Was fordert die vorgeschlagene EU-Richtlinie über Umweltaussagen zur Nachweispflicht vor einer Umweltbehauptung?"},
    {"type": "lawyer", "q": "Was sind die Sanktionen nach der EU-Richtlinie zur Stärkung der Verbraucher für den ökologischen Wandel (Richtlinie 2024/825)?"},
    {"type": "business_owner", "q": "Darf ich mein Produkt 'CO₂-neutral' nennen, wenn ich Emissionen durch Waldzertifikate kompensiere?"},
    {"type": "business_owner", "q": "Was ist ein 'anerkanntes Umweltzeichen' nach der vorgeschlagenen EU-Richtlinie und welche Labels zählen dazu?"},
    {"type": "court", "q": "Wie ist UWG § 5 zur irreführenden Werbung bei Umweltbehauptungen auszulegen, wenn die Aussage faktisch korrekt, aber irreführend kontextualisiert ist?"},
    {"type": "ecj", "q": "Wie verhält sich das EU-Recht über Umweltaussagen zum nationalen UWG — gilt Vollharmonisierung?"},
])

_QUESTION_BANK["double_materiality"].extend([
    {"type": "student", "q": "Was ist doppelte Wesentlichkeit und warum ist sie der Schlüsselbegriff der CSRD?"},
    {"type": "student", "q": "Erkläre den Unterschied zwischen Auswirkungswesentlichkeit (Inside-out) und finanzieller Wesentlichkeit (Outside-in)."},
    {"type": "teacher", "q": "Zeige anhand eines Automobilherstellers, wie er eine doppelte Wesentlichkeitsanalyse durchführt."},
    {"type": "lawyer", "q": "Was fordert ESRS 1 Abschnitt 3 zur Wesentlichkeitsbeurteilung — Prozess, Dokumentation, externe Überprüfung?"},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen dem ESRS-Wesentlichkeitsbegriff und dem IFRS-S-Wesentlichkeitsbegriff (Investor focus)?"},
    {"type": "business_owner", "q": "Wie führe ich eine Wesentlichkeitsanalyse durch und wen muss ich dabei einbeziehen?"},
    {"type": "business_owner", "q": "Was bedeutet es praktisch, dass ein Thema wesentlich ist — muss ich zwingend darüber berichten?"},
    {"type": "court", "q": "Wie ist 'Wesentlichkeit' nach ESRS auszulegen, wenn Auswirkungen kurzfristig nicht finanziell messbar sind?"},
    {"type": "ecj", "q": "Sind die ESRS-Wesentlichkeitsstandards verhältnismäßig, wenn sie KMU als Zulieferer indirekt über große Unternehmen binden?"},
])

_QUESTION_BANK["tcfd"].extend([
    {"type": "student", "q": "Was ist TCFD und welche vier Säulen bilden den Rahmen?"},
    {"type": "student", "q": "Was sind physische Klimarisiken und Übergangsrisiken nach TCFD — gib je ein Beispiel."},
    {"type": "teacher", "q": "Erkläre anhand eines Energieunternehmens, wie ein TCFD-konformer Klimarisikobericht aufgebaut ist."},
    {"type": "lawyer", "q": "Was fordert ESRS E1 vom TCFD-Rahmen — ist TCFD-Konformität ausreichend für CSRD-Compliance?"},
    {"type": "lawyer", "q": "Welche Szenarien verlangt TCFD für Klimarisikoanalysen und welche Temperaturpfade sind Standard?"},
    {"type": "business_owner", "q": "Müssen wir als nicht-börsennotiertes Unternehmen TCFD-Berichte erstellen?"},
    {"type": "business_owner", "q": "Was ist der Unterschied zwischen einem TCFD-Bericht und einem ESRS-E1-Klimabericht?"},
    {"type": "court", "q": "Welche Bedeutung haben TCFD-Leitlinien als 'Soft Law' bei der Auslegung von ESRS E1?"},
    {"type": "ecj", "q": "Inwiefern verpflichtet der EU-Klimacheck-Vorbehalt im EU-Klimagesetz nationale Gerichte, Klimaszenarien bei Genehmigungen zu berücksichtigen?"},
])

_QUESTION_BANK["gri"].extend([
    {"type": "student", "q": "Was sind GRI-Standards und für wen sind sie gedacht?"},
    {"type": "student", "q": "Was ist der Unterschied zwischen 'GRI In Übereinstimmung' und 'referenziert GRI'?"},
    {"type": "teacher", "q": "Erkläre anhand eines Unternehmens mit 200 Mitarbeitern, wie ein GRI-Bericht aufgebaut wird."},
    {"type": "lawyer", "q": "Sind GRI-Standards rechtlich verbindlich oder freiwillig — und in welchem Verhältnis stehen sie zur CSRD?"},
    {"type": "lawyer", "q": "Welche GRI-Standards sind mit ESRS kompatibel und wo bestehen inhaltliche Unterschiede?"},
    {"type": "business_owner", "q": "Wir berichten seit Jahren nach GRI — können wir Teile für unseren CSRD-Bericht wiederverwenden?"},
    {"type": "business_owner", "q": "Was ist der Unterschied zwischen GRI-Wesentlichkeit und ESRS-doppelter Wesentlichkeit?"},
    {"type": "court", "q": "Können GRI-Standards als Auslegungsmaßstab für ESRS-Begriffe herangezogen werden?"},
    {"type": "ecj", "q": "Hat die EU-Kommission durch die ESRS-Delegierten Verordnung GRI-Konzepte rechtsverbindlich gemacht?"},
])

_QUESTION_BANK["issb"].extend([
    {"type": "student", "q": "Was ist das ISSB und was unterscheidet IFRS S1 von IFRS S2?"},
    {"type": "student", "q": "Für wen sind ISSB-Standards gedacht — EU-Unternehmen oder globale Kapitalmärkte?"},
    {"type": "teacher", "q": "Erkläre anhand eines börsennotierten Unternehmens, wie IFRS S1 und S2 in einem integrierten Bericht angewendet werden."},
    {"type": "lawyer", "q": "Was fordert IFRS S2 von Unternehmen zu klimabezogenen Risiken — welche Metriken sind verpflichtend?"},
    {"type": "lawyer", "q": "Wie verhält sich ISSB zu ESRS — gibt es eine Interoperabilitätsbrücke und welche Lücken bleiben?"},
    {"type": "business_owner", "q": "Reicht ein ISSB-konformer Bericht für die ESRS-Pflichten unter der CSRD?"},
    {"type": "business_owner", "q": "Welche Länder haben ISSB bereits verpflichtend eingeführt und was bedeutet das für global operierende Unternehmen?"},
    {"type": "court", "q": "Können ISSB-Standards als Auslegungsmaßstab für ESRS-Anforderungen herangezogen werden, wenn ESRS eine Lücke hat?"},
    {"type": "ecj", "q": "Inwiefern muss die EU bei der Anerkennung von ISSB als Äquivalenz sicherstellen, dass ESRS-Schutzniveaus nicht unterschritten werden?"},
])

_QUESTION_BANK["teu"].extend([
    {"type": "student", "q": "Was ist der TEU und was regelt er — erkläre den Unterschied zum AEUV."},
    {"type": "student", "q": "Was sind die Grundwerte der EU nach Art. 2 TEU und was passiert, wenn ein Mitgliedstaat sie verletzt?"},
    {"type": "teacher", "q": "Erkläre anhand des Art.-7-Verfahrens, wie die EU auf Rechtsstaatsverstöße eines Mitgliedstaats reagieren kann."},
    {"type": "lawyer", "q": "Was regelt Art. 4 Abs. 2 TEU zur nationalen Identität und welche Bedeutung hat er für EU-Gesetzgebung?"},
    {"type": "lawyer", "q": "Was sind die EU-Zuständigkeiten nach Art. 3–6 TEU (ausschließlich, geteilt, unterstützend) — nennen Sie je ein Beispiel?"},
    {"type": "business_owner", "q": "Welche Bedeutung hat der TEU für mein Unternehmen — regelt er direkt unternehmerische Pflichten?"},
    {"type": "business_owner", "q": "Was ist der Unterschied zwischen EU-Recht und nationalem Recht und wie wirkt sich das auf mein Unternehmen aus?"},
    {"type": "court", "q": "Wie ist Art. 4 Abs. 3 TEU (Grundsatz der loyalen Zusammenarbeit) bei einem nationalen Umsetzungsversäumnis auszulegen?"},
    {"type": "ecj", "q": "Inwiefern begrenzt Art. 5 TEU (begrenzte Einzelermächtigung) die EU-Zuständigkeit im Bereich Unternehmensbesteuerung?"},
])

_QUESTION_BANK["tfeu"].extend([
    {"type": "student", "q": "Was sind die vier Grundfreiheiten des AEUV und warum sind sie für den Binnenmarkt zentral?"},
    {"type": "student", "q": "Was ist der Unterschied zwischen Niederlassungsfreiheit (Art. 49 AEUV) und freiem Dienstleistungsverkehr (Art. 56)?"},
    {"type": "teacher", "q": "Erkläre anhand eines deutschen Unternehmens, das in Frankreich Dienstleistungen anbietet, wie Art. 56 AEUV funktioniert."},
    {"type": "lawyer", "q": "Was sind die Keck-Doktrin-Ausnahmen von der Dassonville-Formel für Maßnahmen gleicher Wirkung nach Art. 34 AEUV?"},
    {"type": "lawyer", "q": "Was ist Art. 114 AEUV als Rechtsgrundlage für Binnenmarktharmonisierung und welche Mehrheit ist im Rat erforderlich?"},
    {"type": "business_owner", "q": "Mein deutsches Unternehmen will eine Niederlassung in Polen eröffnen — welche AEUV-Rechte habe ich?"},
    {"type": "business_owner", "q": "Darf Deutschland meinen Wettbewerbern aus anderen EU-Ländern den Marktzugang erschweren?"},
    {"type": "court", "q": "Wie ist 'Maßnahmen gleicher Wirkung' nach Art. 34 AEUV auszulegen, wenn nationale Vorschriften importierte Waren stärker belasten?"},
    {"type": "ecj", "q": "Unter welchen Voraussetzungen darf Deutschland nach Art. 36 AEUV Einfuhrbeschränkungen aus Gründen des Gesundheitsschutzes rechtfertigen?"},
])

_QUESTION_BANK["eu_charter"].extend([
    {"type": "student", "q": "Was ist die EU-Grundrechtecharta und ab wann ist sie rechtlich bindend?"},
    {"type": "student", "q": "Erkläre den Unterschied zwischen Rechten und Grundsätzen in der Charta — welche sind vor Gericht einklagbar?"},
    {"type": "teacher", "q": "Erkläre anhand eines DSGVO-Falls, wie Art. 7 (Datenschutz) und Art. 8 (Privatsphäre) der Charta angewendet werden."},
    {"type": "lawyer", "q": "Was ist die horizontale Wirkung der EU-Grundrechtecharta — gilt sie zwischen Privatpersonen?"},
    {"type": "lawyer", "q": "Was regelt Art. 51 der Charta zum Anwendungsbereich — wann sind Mitgliedstaaten an die Charta gebunden?"},
    {"type": "business_owner", "q": "Hat die Charta direkte Auswirkungen auf mein Unternehmen oder gilt sie nur für den Staat?"},
    {"type": "business_owner", "q": "Kann ein Arbeitnehmer sich gegenüber meinem Unternehmen auf Grundrechte aus der Charta berufen?"},
    {"type": "court", "q": "Wie ist Art. 47 der Charta (effektiver Rechtsschutz) auszulegen, wenn ein nationales Verfahren EU-Recht unangemessen beschränkt?"},
    {"type": "ecj", "q": "Inwiefern kann Art. 17 der Charta (Eigentumsrecht) gegen EU-Regulierung wie CSRD oder Taxonomie geltend gemacht werden?"},
])

_QUESTION_BANK["eu_legislative"].extend([
    {"type": "student", "q": "Was ist das ordentliche EU-Gesetzgebungsverfahren — erkläre die drei Schritte."},
    {"type": "student", "q": "Was ist ein Trilog und warum gibt es ihn?"},
    {"type": "teacher", "q": "Zeige anhand der CSRD-Entstehung, wie ein EU-Gesetzgebungsverfahren in der Praxis funktioniert."},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen erster, zweiter und dritter Lesung im EU-Gesetzgebungsverfahren?"},
    {"type": "lawyer", "q": "Was sind delegierte Rechtsakte (Art. 290 AEUV) vs. Durchführungsrechtsakte (Art. 291) — je ein Beispiel?"},
    {"type": "business_owner", "q": "Kann ich als Unternehmen den EU-Gesetzgebungsprozess beeinflussen und wenn ja, wie?"},
    {"type": "business_owner", "q": "Was ist eine öffentliche Konsultation der EU-Kommission und warum sollte ich daran teilnehmen?"},
    {"type": "court", "q": "Kann ein nationales Gericht einen EU-Rechtsakt wegen Verfahrensfehlern für ungültig erklären?"},
    {"type": "ecj", "q": "Was ist Komitologie und wie kontrolliert der EuGH die Befugnisse der Kommission bei delegierten Rechtsakten?"},
])

_QUESTION_BANK["van_gend_loos"].extend([
    {"type": "student", "q": "Was hat der EuGH in Van Gend en Loos (1963) entschieden — erkläre es in einfachen Worten."},
    {"type": "student", "q": "Was bedeutet 'unmittelbare Wirkung' — kann ich als Bürger EU-Recht direkt vor einem deutschen Gericht geltend machen?"},
    {"type": "teacher", "q": "Erkläre anhand eines konkreten Falls, wie unmittelbare Wirkung nach Van Gend en Loos in der Praxis angewendet wird."},
    {"type": "lawyer", "q": "Was sind die drei Voraussetzungen für die unmittelbare Wirkung einer EU-Norm nach Van Gend en Loos?"},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen vertikaler unmittelbarer Wirkung (Staat vs. Bürger) und horizontaler unmittelbarer Wirkung (Bürger vs. Bürger)?"},
    {"type": "business_owner", "q": "Was bedeutet Van Gend en Loos für mein Unternehmen im Verhältnis zum deutschen Staat?"},
    {"type": "business_owner", "q": "Kann ich als Unternehmen direkt auf eine EU-Verordnung pochen, wenn Deutschland sie nicht national umgesetzt hat?"},
    {"type": "court", "q": "Wann hat eine Richtlinienbestimmung nach Van Gend en Loos unmittelbare Wirkung und wann nicht?"},
    {"type": "ecj", "q": "Welche Bedeutung hatte Van Gend en Loos für die Entwicklung des EU-Rechts als 'neue Rechtsordnung'?"},
])

_QUESTION_BANK["costa_enel"].extend([
    {"type": "student", "q": "Was hat Costa v. ENEL (1964) entschieden — erkläre den Vorrang des EU-Rechts für Anfänger."},
    {"type": "student", "q": "Warum hat EU-Recht Vorrang vor nationalem Recht — welcher Fall begründet das?"},
    {"type": "teacher", "q": "Erkläre anhand eines Beispiels, was passiert, wenn ein deutsches Gesetz gegen EU-Recht verstößt."},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen Vorrang des EU-Rechts (Costa) und unmittelbarer Wirkung (Van Gend en Loos)?"},
    {"type": "lawyer", "q": "Wie ist der Vorrang des EU-Rechts nach Costa in Bezug auf nationales Verfassungsrecht zu bewerten (Solange-Rechtsprechung)?"},
    {"type": "business_owner", "q": "Was bedeutet der EU-Rechtsvorrang für mein Unternehmen, wenn nationale und EU-Vorschriften widersprüchlich sind?"},
    {"type": "business_owner", "q": "Muss ein deutsches Gericht ein nationales Gesetz, das gegen EU-Recht verstößt, unangewendet lassen?"},
    {"type": "court", "q": "Was muss ein deutsches Gericht tun, wenn ein Gesetz gegen eine EU-Verordnung verstößt?"},
    {"type": "ecj", "q": "Inwiefern schränkt das BVerfG-Urteil zum EU-Anleihekaufprogramm (PSPP) den EU-Rechtsvorrang nach Costa ein?"},
])

_QUESTION_BANK["cassis_dijon"].extend([
    {"type": "student", "q": "Was hat das Cassis-de-Dijon-Urteil (1979) entschieden und warum ist es für den Binnenmarkt wichtig?"},
    {"type": "student", "q": "Was ist das Prinzip der gegenseitigen Anerkennung — wie hilft es Unternehmen im EU-Binnenmarkt?"},
    {"type": "teacher", "q": "Erkläre anhand eines deutschen Produkts, das in Frankreich verboten wird, wie Cassis angewendet wird."},
    {"type": "lawyer", "q": "Was sind die vier 'zwingenden Erfordernisse' des Allgemeininteresses nach Cassis de Dijon?"},
    {"type": "lawyer", "q": "Wie hat der EuGH in Keck (1993) die Cassis-Doktrin eingeschränkt — was gilt seitdem für Verkaufsmodalitäten?"},
    {"type": "business_owner", "q": "Mein in Deutschland zugelassenes Produkt wird von Frankreich als illegal abgelehnt — was kann ich tun?"},
    {"type": "business_owner", "q": "Warum muss ich mein Produkt nicht für jeden EU-Markt separat zertifizieren lassen?"},
    {"type": "court", "q": "Wann ist eine nationale Produktregel nach Cassis eine zulässige Beschränkung und wann verletzt sie Art. 34 AEUV?"},
    {"type": "ecj", "q": "Wie hat sich das Cassis-Prinzip der gegenseitigen Anerkennung durch das Binnenmarktprogramm von 1985 institutionalisiert?"},
])

_QUESTION_BANK["francovich"].extend([
    {"type": "student", "q": "Was hat Francovich (1991) entschieden — können Bürger den Staat für EU-Rechtsverstöße verklagen?"},
    {"type": "student", "q": "Was ist Staatshaftung im EU-Recht und warum ist sie ein wichtiges Instrument für Einzelpersonen?"},
    {"type": "teacher", "q": "Erkläre anhand eines Arbeitnehmers, dessen Unternehmen insolvent ist, wie Francovich-Ansprüche funktionieren."},
    {"type": "lawyer", "q": "Was sind die drei Francovich-Voraussetzungen für die Staatshaftung bei Umsetzungsversäumnis?"},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen Francovich-Haftung (Umsetzungsversäumnis) und Brasserie-du-Pêcheur-Haftung (hinreichend qualifizierter Verstoß)?"},
    {"type": "business_owner", "q": "Kann mein Unternehmen Schadensersatz vom deutschen Staat verlangen, wenn Deutschland eine EU-Richtlinie zu spät umsetzt?"},
    {"type": "business_owner", "q": "Wie hoch ist die Beweislast bei einem Francovich-Anspruch und welches Gericht ist zuständig?"},
    {"type": "court", "q": "Was ist ein 'hinreichend qualifizierter Verstoß' nach Brasserie du Pêcheur/Factortame (1996) — wie wird er bestimmt?"},
    {"type": "ecj", "q": "Inwiefern hat Francovich die Durchsetzung des EU-Rechts gestärkt und welche Grenzen bestehen?"},
])

_QUESTION_BANK["schrems"].extend([
    {"type": "student", "q": "Was haben Schrems I und Schrems II entschieden — erkläre es für Nicht-Juristen."},
    {"type": "student", "q": "Was ist das EU-US-Datenschutzrahmenwerk (Data Privacy Framework 2023) und warum gibt es es?"},
    {"type": "teacher", "q": "Erkläre anhand eines US-Cloud-Anbieters, was Schrems II für europäische Unternehmen bedeutet."},
    {"type": "lawyer", "q": "Was sind die Voraussetzungen für die Nutzung von Standardvertragsklauseln nach Schrems II und welche 'zusätzlichen Maßnahmen' sind erforderlich?"},
    {"type": "lawyer", "q": "Was hat das Urteil C-311/18 (Schrems II) zu US-Geheimdienstüberwachung im Verhältnis zu Art. 52 EU-Grundrechtecharta entschieden?"},
    {"type": "business_owner", "q": "Ich nutze Salesforce (US-Cloud) für EU-Kundendaten — was sind meine Pflichten nach Schrems II?"},
    {"type": "business_owner", "q": "Ist das EU-US-Datenschutzrahmenwerk von 2023 sicher oder droht ein Schrems III?"},
    {"type": "court", "q": "Wie ist Art. 46 DSGVO zu Standardvertragsklauseln nach Schrems II auszulegen, wenn Überwachungsgesetze im Drittland bestehen?"},
    {"type": "ecj", "q": "Inwiefern verpflichtet Schrems II nationale Datenschutzbehörden, US-Datentransfers ohne Transfer Impact Assessment zu untersagen?"},
])

_QUESTION_BANK["google_spain"].extend([
    {"type": "student", "q": "Was hat Google Spain (2014) entschieden — was ist das Recht auf Vergessenwerden?"},
    {"type": "student", "q": "Warum sind Suchmaschinenergebnisse personenbezogene Daten — was hat der EuGH in Google Spain festgestellt?"},
    {"type": "teacher", "q": "Erkläre anhand eines veralteten Zeitungsartikels über eine Privatperson, wie das Recht auf Vergessenwerden funktioniert."},
    {"type": "lawyer", "q": "Was sind die Voraussetzungen für einen erfolgreichen Antrag auf Löschung von Suchergebnissen nach Google Spain?"},
    {"type": "lawyer", "q": "Wie verhält sich Google Spain zu Art. 17 DSGVO — hat Google Spain die DSGVO-Norm beeinflusst?"},
    {"type": "business_owner", "q": "Mein Unternehmen erscheint in negativen Suchergebnissen — kann ich Google Spain/Art. 17 DSGVO nutzen?"},
    {"type": "business_owner", "q": "Gilt das Recht auf Vergessenwerden auch außerhalb der EU, z.B. auf google.com?"},
    {"type": "court", "q": "Wie ist das Recht auf Vergessenwerden mit der Pressefreiheit (Art. 11 Charta) in Ausgleich zu bringen?"},
    {"type": "ecj", "q": "Welche Bedeutung hat das Urteil C-136/17 (GC v. CNIL) für sensible Daten in Suchergebnissen?"},
])

_QUESTION_BANK["cjeu_cases"].extend([
    {"type": "student", "q": "Was ist die Klimaklage-Welle und wie hat der EuGH zu Klimapflichten beigetragen?"},
    {"type": "student", "q": "Erkläre die Bedeutung der Janecek-Entscheidung (C-237/07) für das Recht auf saubere Luft."},
    {"type": "teacher", "q": "Erkläre anhand von Urgenda, wie strategische Klimaklagen das EU- und nationale Umweltrecht beeinflussen."},
    {"type": "lawyer", "q": "Was entschied der EuGH in C-594/18 P (Österreich vs. Kommission) zur EU-Beihilfe für Atomkraft?"},
    {"type": "lawyer", "q": "Welche Grundsätze für Umwelthaftung hat der EuGH in Nomarchiaki Aftodioikisi Aitoloakarnanias (C-43/10) entwickelt?"},
    {"type": "business_owner", "q": "Was bedeutet das EuGH-Urteil zu Umweltinformationen (C-204/09, Flachglas Torgau) für mein Unternehmen?"},
    {"type": "business_owner", "q": "Welches EuGH-Urteil verpflichtet EU-Institutionen, Umweltinformationen herauszugeben?"},
    {"type": "court", "q": "Welche Bedeutung hat das Vorabentscheidungsverfahren für das nationale Umwelthaftungsrecht?"},
    {"type": "ecj", "q": "Wie hat der EuGH den Begriff 'Umweltschaden' in der Umwelthaftungsrichtlinie 2004/35/EG ausgelegt?"},
])

_QUESTION_BANK["eu_commission"].extend([
    {"type": "student", "q": "Was macht die EU-Kommission und warum hat sie als einzige Institution das Initiativmonopol?"},
    {"type": "student", "q": "Was ist ein Vertragsverletzungsverfahren und was passiert, wenn Deutschland eine EU-Richtlinie nicht umsetzt?"},
    {"type": "teacher", "q": "Erkläre den Weg von einer Kommissionsinitiative bis zu einem fertigen EU-Gesetz."},
    {"type": "lawyer", "q": "Welche Befugnisse hat die Kommission nach Art. 17 TEU im EU-Wettbewerbsrecht (Art. 101/102 AEUV)?"},
    {"type": "lawyer", "q": "Was ist ein Konformitätsbeschluss der Kommission und welche Rechtswirkung hat er?"},
    {"type": "business_owner", "q": "Wie kann mein Unternehmen an Kommissionskonsultationen teilnehmen und warum ist das wichtig?"},
    {"type": "business_owner", "q": "Was bedeutet eine Kommissionsbeihilfe-Untersuchung für mein Unternehmen, wenn ich staatliche Förderung erhalten habe?"},
    {"type": "court", "q": "Inwiefern bindet eine Kommissionsentscheidung nationale Gerichte in einem daraus folgenden Schadensersatzverfahren?"},
    {"type": "ecj", "q": "Was ist die 'institutionelle Balance' zwischen Kommission, Rat und Parlament und wie hat der EuGH sie gestärkt?"},
])

_QUESTION_BANK["eu_parliament"].extend([
    {"type": "student", "q": "Was macht das EU-Parlament und warum wird es direkt gewählt?"},
    {"type": "student", "q": "Warum darf das EU-Parlament keine Gesetzesinitiativen einbringen — und wie übt es trotzdem Einfluss aus?"},
    {"type": "teacher", "q": "Erkläre anhand des AI Act, welche Rolle das Parlament im Gesetzgebungsverfahren gespielt hat."},
    {"type": "lawyer", "q": "Was sind die Befugnisse des Parlaments im ordentlichen Gesetzgebungsverfahren nach Art. 294 AEUV?"},
    {"type": "lawyer", "q": "Wie funktioniert das Haushaltsverfahren nach Art. 314 AEUV und welche Sonderrolle hat das Parlament?"},
    {"type": "business_owner", "q": "Warum sollte ich die Arbeit des EU-Parlaments verfolgen — wie beeinflusst es Unternehmensregulierung?"},
    {"type": "business_owner", "q": "Was ist ein EP-Bericht und welche praktische Bedeutung hat er im Gesetzgebungsverfahren?"},
    {"type": "court", "q": "Hat das EU-Parlament Klagebefugnis vor dem EuGH und in welchen Situationen nutzt es sie?"},
    {"type": "ecj", "q": "Inwiefern hat das Europäische Parlament durch den Lissabonner Vertrag im Bereich Handelsabkommen (Art. 207 AEUV) neue Rechte erhalten?"},
])

_QUESTION_BANK["cjeu_court"].extend([
    {"type": "student", "q": "Was ist der EuGH und was ist der Unterschied zwischen EuGH (Gerichtshof) und EuG (Gericht)?"},
    {"type": "student", "q": "Was ist ein Vorabentscheidungsverfahren und welches nationale Gericht stellt die Fragen?"},
    {"type": "teacher", "q": "Erkläre anhand eines deutschen Unternehmensrechtsstreits, wie und warum ein Gericht den EuGH einschalten würde."},
    {"type": "lawyer", "q": "Was ist der Unterschied zwischen Vorabentscheidungsverfahren (Art. 267 AEUV) und Nichtigkeitsklage (Art. 263)?"},
    {"type": "lawyer", "q": "Unter welchen Voraussetzungen können Einzelpersonen nach Art. 263 Abs. 4 AEUV direkt gegen EU-Rechtsakte klagen?"},
    {"type": "business_owner", "q": "Kann mein Unternehmen direkt vor dem EuGH klagen und wenn ja, unter welchen Voraussetzungen?"},
    {"type": "business_owner", "q": "Was ist ein EuGH-Gutachten (Art. 218 Abs. 11 AEUV) und wann wird es eingeholt?"},
    {"type": "court", "q": "Was ist die Bindungswirkung eines EuGH-Vorabentscheidungsurteils für das nationale Gericht, das die Frage gestellt hat?"},
    {"type": "ecj", "q": "Was ist das CILFIT-Urteil (1982) und wie begrenzt es die Vorlageverpflichtung letztinstanzlicher nationaler Gerichte?"},
])

_QUESTION_BANK["ai_act"].extend([
    {"type": "student", "q": "Was ist der EU AI Act und wie klassifiziert er KI-Systeme nach Risiko?"},
    {"type": "student", "q": "Was sind 'verbotene KI-Praktiken' nach dem EU AI Act — nenne drei Beispiele."},
    {"type": "teacher", "q": "Erkläre anhand eines HR-Tools zur Bewerbungsauswahl, wie der AI Act es einordnet und was das für das Unternehmen bedeutet."},
    {"type": "lawyer", "q": "Was sind die Pflichten für Anbieter von Hochrisiko-KI-Systemen nach Art. 9–15 AI Act?"},
    {"type": "lawyer", "q": "Was sind die Transparenzpflichten nach Art. 50 AI Act für KI-Systeme, die mit Menschen interagieren?"},
    {"type": "business_owner", "q": "Mein Unternehmen setzt KI-gestütztes Kreditscoring ein — falle ich unter Hochrisiko-KI und was muss ich tun?"},
    {"type": "business_owner", "q": "Was ist ein KI-Konformitätsbewertungsverfahren (Conformity Assessment) und wie läuft es ab?"},
    {"type": "court", "q": "Wie ist 'erhebliches Risiko' bei Allzweck-KI-Modellen nach Art. 51 AI Act auszulegen — welcher Schwellenwert gilt?"},
    {"type": "ecj", "q": "Steht das AI-Act-Verbot bestimmter biometrischer Kategorisierungssysteme im Einklang mit Art. 8 EU-Grundrechtecharta?"},
])

_QUESTION_BANK["nis2"].extend([
    {"type": "student", "q": "Was ist NIS2 und welche Unternehmen müssen sich registrieren?"},
    {"type": "student", "q": "Was ist der Unterschied zwischen 'wesentlichen' und 'wichtigen' Einrichtungen nach NIS2?"},
    {"type": "teacher", "q": "Erkläre anhand eines mittelgroßen Energieunternehmens, welche NIS2-Pflichten es hat."},
    {"type": "lawyer", "q": "Was fordert NIS2 Art. 21 zu Cybersicherheitsmaßnahmen — welche 10 Mindestmaßnahmen sind vorgesehen?"},
    {"type": "lawyer", "q": "Was sind die Meldepflichten nach NIS2 Art. 23 bei einem bedeutenden Sicherheitsvorfall — Fristen und Inhalt?"},
    {"type": "business_owner", "q": "Unser Unternehmen hat 60 Mitarbeiter und €12 Mio. Umsatz im Gesundheitssektor — fällt es unter NIS2?"},
    {"type": "business_owner", "q": "Was passiert, wenn wir einen Cyberangriff nicht fristgerecht melden — welche Sanktionen drohen?"},
    {"type": "court", "q": "Wie ist 'bedeutender Sicherheitsvorfall' nach NIS2 Art. 23 auszulegen — gibt es Schwellenwerte?"},
    {"type": "ecj", "q": "Inwiefern ist NIS2 mit der DSGVO vereinbar, wenn Sicherheitsvorfallsmeldungen personenbezogene Daten enthalten?"},
])


def _load_corpus_chunks() -> list[dict]:
    global _CORPUS_CHUNKS_CACHE
    if _CORPUS_CHUNKS_CACHE is not None:
        return _CORPUS_CHUNKS_CACHE

    chunks: list[dict] = []
    if not _CORPUS_FILE.exists():
        _CORPUS_CHUNKS_CACHE = chunks
        return chunks

    try:
        with _CORPUS_FILE.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not obj.get("text"):
                    continue
                chunks.append(obj)
    except Exception:
        chunks = []

    _CORPUS_CHUNKS_CACHE = chunks
    return chunks


def _extract_keywords(text: str, limit: int = 3) -> list[str]:
    words = re.findall(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]{3,}", text)
    out: list[str] = []
    seen: set[str] = set()
    for w in words:
        wl = w.lower()
        if wl in _STOP_WORDS:
            continue
        if wl in seen:
            continue
        seen.add(wl)
        out.append(w)
        if len(out) >= limit:
            break
    return out


def _chunk_matches_topic(chunk: dict, topic_id: str, topic_name: str) -> bool:
    reg = str(chunk.get("regulation", "")).lower()
    title = str(chunk.get("title", "")).lower()
    text = str(chunk.get("text", "")).lower()
    hints = _TOPIC_CORPUS_HINTS.get(topic_id, [])

    if topic_id and topic_id.replace("_", "") in reg.replace("_", ""):
        return True
    if topic_name and topic_name.lower() in title:
        return True
    for h in hints:
        if h in reg or h in title or h in text:
            return True
    return False


def _build_corpus_question(topic_id: str, topic_name: str, asked: int) -> dict | None:
    chunks = _load_corpus_chunks()
    if not chunks:
        return None

    filtered = [c for c in chunks if _chunk_matches_topic(c, topic_id, topic_name)]
    if not filtered:
        filtered = chunks

    chunk = filtered[asked % len(filtered)]
    regulation = chunk.get("regulation") or topic_name or "EU-Recht"
    article = chunk.get("article") or "Artikel"
    title = chunk.get("title") or "Kernanforderung"
    text = chunk.get("text") or ""
    template = _QUESTION_TEMPLATES[asked % len(_QUESTION_TEMPLATES)]
    question = template.format(regulation=regulation, article=article, title=title)
    kws = _extract_keywords(text, limit=3)
    if kws:
        question += f" Bitte berücksichtige: {', '.join(kws)}."
    return {
        "type": "corpus",
        "q": question,
        "source": "pdf_corpus",
        "regulation": regulation,
        "article": article,
        "title": title,
    }


def _load() -> list[dict]:
    if _MAP_FILE.exists():
        try:
            data = json.loads(_MAP_FILE.read_text())
            saved_ids = {t["id"] for t in data}
            for seed in _SEED_MAP:
                if seed["id"] not in saved_ids:
                    data.append(dict(seed))
            return data
        except Exception:
            pass
    return [dict(t) for t in _SEED_MAP]


def _save(topics: list[dict]) -> None:
    _MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MAP_FILE.write_text(json.dumps(topics, indent=2, ensure_ascii=False))


def get_map() -> list[dict]:
    with _lock:
        return _load()


def get_overall_pct() -> int:
    topics = get_map()
    if not topics:
        return 0
    return round(sum(t["pct"] for t in topics) / len(topics))


def get_next_learn_topic(include_mastered: bool = False) -> dict | None:
    topics = get_map()
    if not topics:
        return None
    if include_mastered:
        topics.sort(key=lambda t: (t.get("questions_asked", 0), t.get("pct", 0)))
        return topics[0]

    learnable = [t for t in topics if t["status"] not in ("functional", "mastered")]
    if not learnable:
        return None
    learnable.sort(key=lambda t: (_STATUS_ORDER.index(t.get("status", "unknown")), t["pct"]))
    return learnable[0]


def get_next_question(topic_id: str) -> dict | None:
    """Return next question dict {type, q} for a topic."""
    topics = get_map()
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return None
    asked = topic.get("questions_asked", 0)

    corpus_q = _build_corpus_question(topic_id=topic_id, topic_name=topic.get("name", ""), asked=asked)
    if corpus_q:
        return corpus_q

    questions = _QUESTION_BANK.get(topic_id, [])
    if not questions:
        return None
    idx = asked % len(questions)
    return questions[idx]


def get_all_questions(topic_id: str) -> list[dict]:
    """Return all questions for a topic."""
    return _QUESTION_BANK.get(topic_id, [])


def _get_next_learnable(topics: list[dict]) -> dict | None:
    learnable = [t for t in topics if t["status"] not in ("functional", "mastered")]
    if not learnable:
        return None
    learnable.sort(key=lambda t: (_STATUS_ORDER.index(t.get("status", "unknown")), t["pct"]))
    return learnable[0]


def record_answer(topic_id: str, answer_text: str, reference: str = "", question_text: str = "") -> dict:
    with _lock:
        topics = _load()
        topic = next((t for t in topics if t["id"] == topic_id), None)
        if topic is None:
            return {"topic": {}, "overall_pct": 0, "next_topic": None}

        pct_before = topic["pct"]
        q_entry = _QUESTION_BANK.get(topic_id, [])
        asked_idx = topic.get("questions_asked", 0) % len(q_entry) if q_entry else 0
        question_text = question_text or (q_entry[asked_idx]["q"] if q_entry else "")

        valid = len(answer_text.strip()) >= 20
        topic["questions_asked"] = topic.get("questions_asked", 0) + 1
        if valid:
            topic["questions_answered"] = topic.get("questions_answered", 0) + 1
            topic["last_updated"] = datetime.now(timezone.utc).isoformat()
            topic["pct"] = min(100, topic["pct"] + 12)
            topic["status"] = _compute_status(topic["pct"])
        _save(topics)

        ts = datetime.now(timezone.utc).isoformat()
        _ANSWER_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _ANSWER_HISTORY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "id":          f"ans-{int(datetime.now(timezone.utc).timestamp()*1000)}",
                "ts":          ts,
                "topic_id":    topic_id,
                "topic_name":  topic["name"],
                "category":    topic.get("category", ""),
                "question":    question_text,
                "user_answer": answer_text,
                "reference":   reference,
                "pct_before":  pct_before,
                "pct_after":   topic["pct"],
                "status_after": topic["status"],
                "answer_len":  len(answer_text),
                "valid":       valid,
            }, ensure_ascii=False) + "\n")

        overall = round(sum(t["pct"] for t in topics) / len(topics)) if topics else 0
        next_t  = _get_next_learnable(topics)
        return {
            "topic":       topic,
            "overall_pct": overall,
            "next_topic":  next_t["name"] if next_t else None,
        }


def _compute_status(pct: int) -> str:
    if pct == 0:
        return "unknown"
    if pct < 20:
        return "seed"
    if pct < 50:
        return "learning"
    if pct < 70:
        return "connected"
    if pct < 90:
        return "functional"
    return "mastered"
