"""Knowledge map — tracks LIOS learning progress across EU and German law topics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_MAP_FILE = Path("data/memory/knowledge_map.json")
_ANSWER_HISTORY_FILE = Path("data/memory/answer_history.jsonl")
_lock = Lock()

_STATUS_ORDER = ["unknown", "seed", "learning", "connected", "functional", "mastered"]

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


def get_next_learn_topic() -> dict | None:
    topics = get_map()
    learnable = [t for t in topics if t["status"] not in ("functional", "mastered")]
    if not learnable:
        return None
    learnable.sort(key=lambda t: (_STATUS_ORDER.index(t.get("status", "unknown")), t["pct"]))
    return learnable[0]


def get_next_question(topic_id: str) -> dict | None:
    """Return next question dict {type, q} for a topic."""
    questions = _QUESTION_BANK.get(topic_id, [])
    if not questions:
        return None
    topics = get_map()
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return None
    asked = topic.get("questions_asked", 0)
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


def record_answer(topic_id: str, answer_text: str, reference: str = "") -> dict:
    with _lock:
        topics = _load()
        topic = next((t for t in topics if t["id"] == topic_id), None)
        if topic is None:
            return {"topic": {}, "overall_pct": 0, "next_topic": None}

        pct_before = topic["pct"]
        q_entry = _QUESTION_BANK.get(topic_id, [])
        asked_idx = topic.get("questions_asked", 0) % len(q_entry) if q_entry else 0
        question_text = q_entry[asked_idx]["q"] if q_entry else ""

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
