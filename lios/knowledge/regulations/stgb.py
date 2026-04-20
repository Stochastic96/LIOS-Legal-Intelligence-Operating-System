"""StGB – German Criminal Code (Strafgesetzbuch) structured data."""

from __future__ import annotations

NAME = "StGB"
FULL_NAME = "German Criminal Code (Strafgesetzbuch)"
effective_date = "1998-11-13"
last_updated = "2024-10-01"
jurisdictions = ["DE"]

articles = [
    {
        "id": "§1",
        "title": "No punishment without law (Nulla poena sine lege)",
        "keywords": ["nulla poena", "legality", "punishment", "law", "offence", "principle"],
        "text": (
            "An act may only be punished if its punishability was established by law before "
            "the act was committed. The law in force at the time the act is committed is to "
            "be applied. If the law is amended after the act, the most lenient law is to be "
            "applied."
        ),
        "topic": "general_principles",
    },
    {
        "id": "§15",
        "title": "Intentional and negligent acts",
        "keywords": ["intent", "negligence", "dolus", "fault", "criminal liability", "mens rea"],
        "text": (
            "Unless the law expressly provides for punishment of negligent conduct, only "
            "intentional conduct is punishable. Intentional conduct means acting with "
            "knowledge and will to bring about the elements of a criminal offence. "
            "Negligent conduct means failing to observe the required degree of care."
        ),
        "topic": "mental_element",
    },
    {
        "id": "§17",
        "title": "Mistake of law",
        "keywords": ["mistake of law", "legal error", "prohibition", "unavoidable", "culpability"],
        "text": (
            "If at the time of committing the act the offender lacks the awareness that they "
            "are acting unlawfully, they act without guilt if the mistake was unavoidable. "
            "If the mistake was avoidable, the punishment may be mitigated pursuant to § 49(1)."
        ),
        "topic": "defences",
    },
    {
        "id": "§32",
        "title": "Self-defence",
        "keywords": ["self-defence", "Notwehr", "defence", "justification", "attack", "unlawful"],
        "text": (
            "A person who commits an act in self-defence does not act unlawfully. "
            "Self-defence means any defensive action that is necessary to avert an imminent "
            "unlawful attack on oneself or another."
        ),
        "topic": "justifications",
    },
    {
        "id": "§34",
        "title": "Necessity",
        "keywords": ["necessity", "Notstand", "justifying necessity", "danger", "proportionality"],
        "text": (
            "A person who, faced with an imminent danger to life, limb, freedom, honour, "
            "property or another legal interest which cannot otherwise be averted, commits "
            "an act to avert the danger from themselves or another does not act unlawfully "
            "if, upon weighing the conflicting interests, in particular the affected legal "
            "interests and the degree of the danger threatening them, the protected interest "
            "substantially outweighs the one interfered with."
        ),
        "topic": "justifications",
    },
    {
        "id": "§185",
        "title": "Insult",
        "keywords": ["insult", "Beleidigung", "honour", "defamation", "slander", "criminal"],
        "text": (
            "Insult shall be punished with imprisonment of not more than one year or a fine "
            "and, if the insult is committed by means of an assault, with imprisonment of "
            "not more than two years or a fine."
        ),
        "topic": "honour_offences",
    },
    {
        "id": "§202a",
        "title": "Data espionage",
        "keywords": ["data espionage", "hacking", "computer", "data", "access", "security",
                     "cybercrime", "unauthorised"],
        "text": (
            "Whoever, without authorisation, obtains data for themselves or another that was "
            "not intended for them and was especially protected against unauthorised access, "
            "if they have overcome the security protection, shall be punished with imprisonment "
            "of not more than three years or a fine."
        ),
        "topic": "computer_offences",
    },
    {
        "id": "§223",
        "title": "Causing bodily harm",
        "keywords": ["bodily harm", "Körperverletzung", "assault", "injury", "physical", "health"],
        "text": (
            "Whoever physically assaults another person or causes harm to that person's health "
            "shall be punished with imprisonment of not more than five years or a fine."
        ),
        "topic": "bodily_harm",
    },
    {
        "id": "§242",
        "title": "Theft",
        "keywords": ["theft", "Diebstahl", "movable property", "unlawful appropriation", "intent"],
        "text": (
            "Whoever takes movable property belonging to another from another with the intention "
            "of unlawfully appropriating it for themselves or a third party shall be punished "
            "with imprisonment of not more than five years or a fine."
        ),
        "topic": "property_offences",
    },
    {
        "id": "§263",
        "title": "Fraud",
        "keywords": ["fraud", "Betrug", "deception", "financial damage", "enrichment", "false pretences"],
        "text": (
            "Whoever, with the intent of obtaining an unlawful material benefit for themselves "
            "or a third party, causes damage to the assets of another by inducing or maintaining "
            "a mistaken belief by false pretences or by distorting or suppressing true facts "
            "shall be punished with imprisonment of not more than five years or a fine."
        ),
        "topic": "fraud",
    },
    {
        "id": "§266",
        "title": "Breach of fiduciary duty",
        "keywords": ["breach of fiduciary duty", "Untreue", "fiduciary", "assets", "duty of care",
                     "management", "misappropriation"],
        "text": (
            "Whoever abuses the power to dispose of the assets of another or to enter into "
            "obligations on behalf of another, which is granted by law, by governmental "
            "authority or by a legal transaction, or whoever breaches the duty to safeguard "
            "the financial interests of another incumbent upon them by virtue of law, "
            "governmental authority, legal transaction or a relationship of trust, and thereby "
            "causes damage to the assets of the person whose interests they should be "
            "safeguarding, shall be punished with imprisonment of not more than five years or "
            "a fine."
        ),
        "topic": "property_offences",
    },
    {
        "id": "§299",
        "title": "Bribery and corruption in commercial practice",
        "keywords": ["bribery", "corruption", "commercial", "Bestechung", "advantage", "employee",
                     "unfair competition"],
        "text": (
            "Whoever, as an employee or agent of a business, demands, has themselves promised, "
            "or accepts an advantage for themselves or a third party in connection with that "
            "employment or position as consideration for the fact that they have, in an undue "
            "manner, advantaged another in the purchase of goods or commercial services in "
            "domestic or foreign competition, shall be punished with imprisonment of not more "
            "than three years or a fine."
        ),
        "topic": "corruption",
    },
    {
        "id": "§303a",
        "title": "Data alteration",
        "keywords": ["data alteration", "computer data", "delete", "suppress", "render unusable",
                     "cybercrime"],
        "text": (
            "Whoever unlawfully deletes, suppresses, renders unusable or alters data shall be "
            "punished with imprisonment of not more than two years or a fine."
        ),
        "topic": "computer_offences",
    },
]
