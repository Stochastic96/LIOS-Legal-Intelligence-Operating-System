"""BGB – German Civil Code (Bürgerliches Gesetzbuch) structured data."""

from __future__ import annotations

NAME = "BGB"
FULL_NAME = "German Civil Code (Bürgerliches Gesetzbuch)"
effective_date = "2002-01-01"
last_updated = "2024-01-01"
jurisdictions = ["DE"]

articles = [
    {
        "id": "§1",
        "title": "Legal capacity",
        "keywords": ["legal capacity", "person", "birth", "rights", "natural person"],
        "text": (
            "The legal capacity of a human being begins at the completion of birth. "
            "Every natural person has legal capacity, i.e. the capacity to have rights and "
            "duties under private law."
        ),
        "topic": "persons",
    },
    {
        "id": "§104",
        "title": "Incapacity to contract",
        "keywords": ["incapacity", "contract", "minors", "mental disorder", "void", "legal transaction"],
        "text": (
            "A person is incapable of contracting if they: (1) have not yet reached the age "
            "of seven; (2) are in a state of pathological mental disturbance that excludes "
            "free determination of will, unless the state is by its nature a temporary one. "
            "Legal transactions by a person incapable of contracting are void."
        ),
        "topic": "legal_capacity",
    },
    {
        "id": "§106",
        "title": "Limited contractual capacity of a minor",
        "keywords": ["minor", "limited capacity", "7 years", "18 years", "legal transaction",
                     "guardian", "assent"],
        "text": (
            "A minor who has reached the age of seven has limited contractual capacity as "
            "provided in §§ 107 to 113. A minor who has not yet reached the age of 18 requires "
            "the assent of their legal representative for a legal transaction, unless the "
            "transaction is solely to their legal advantage."
        ),
        "topic": "legal_capacity",
    },
    {
        "id": "§119",
        "title": "Voidability for mistake",
        "keywords": ["mistake", "voidable", "error", "declaration of intent", "rescission", "content", "identity"],
        "text": (
            "A person who, when making a declaration of intent, was mistaken about its content "
            "or who had no intention whatsoever of making a declaration with this content, may "
            "rescind the declaration if it is to be assumed that he would not have made the "
            "declaration with knowledge of the factual position and with a sensible assessment "
            "of the case. A mistake concerning such characteristics of a person or a thing as "
            "are customarily regarded as essential is also deemed to be a mistake as to the "
            "content of the declaration."
        ),
        "topic": "declarations_of_intent",
    },
    {
        "id": "§133",
        "title": "Interpretation of a declaration of intent",
        "keywords": ["interpretation", "declaration of intent", "actual will", "literal meaning"],
        "text": (
            "When interpreting a declaration of intent, it is necessary to ascertain the actual "
            "intention rather than adhering to the literal meaning of the declaration."
        ),
        "topic": "interpretation",
    },
    {
        "id": "§242",
        "title": "Performance in good faith",
        "keywords": ["good faith", "performance", "obligation", "usage", "bona fide"],
        "text": (
            "An obligor has a duty to perform according to the requirements of good faith, "
            "ordinary usage being taken into consideration."
        ),
        "topic": "obligations",
    },
    {
        "id": "§280",
        "title": "Damages for breach of duty",
        "keywords": ["damages", "breach", "duty", "obligation", "compensation", "liability", "harm"],
        "text": (
            "If the obligor breaches a duty arising from the obligation, the obligee may demand "
            "compensation for the damage caused thereby. This does not apply if the obligor is "
            "not responsible for the breach of duty. The obligee may demand compensation for "
            "damage caused by delay only if the additional requirements of § 286 are met. "
            "The obligee may demand compensation for damage instead of performance only if the "
            "additional requirements of § 281, § 282 or § 283 are met."
        ),
        "topic": "breach_of_contract",
    },
    {
        "id": "§286",
        "title": "Default of the obligor",
        "keywords": ["default", "delay", "obligor", "notice", "reminder", "damages", "mora"],
        "text": (
            "If the obligor, following a warning notice by the obligee that is made after "
            "the obligation has fallen due, fails to perform, the obligor is in default as a "
            "result of the warning notice. A warning notice is not required if a time period "
            "is determined by the calendar; the obligor goes into default without a warning "
            "notice if they fail to perform at the relevant time."
        ),
        "topic": "default",
    },
    {
        "id": "§305",
        "title": "Inclusion of general terms and conditions in a contract",
        "keywords": ["general terms and conditions", "AGB", "standard terms", "inclusion", "contract",
                     "consumer", "express reference"],
        "text": (
            "General terms and conditions are all pre-formulated contractual conditions for a "
            "multitude of contracts which one party (the user) presents to the other party on "
            "conclusion of the contract. General terms and conditions are only incorporated into "
            "a contract if, when entering into the contract, the user refers to them expressly "
            "or, where explicit reference would only be possible with disproportionate difficulty, "
            "by a clearly visible notice and if the other party has the opportunity to obtain "
            "knowledge of their content, and agrees to their validity."
        ),
        "topic": "standard_terms",
    },
    {
        "id": "§307",
        "title": "Review of contents",
        "keywords": ["unfair terms", "AGB", "review", "unreasonable disadvantage", "void",
                     "good faith", "consumer"],
        "text": (
            "Provisions in general terms and conditions are ineffective if, contrary to the "
            "requirement of good faith, they unreasonably disadvantage the other party to the "
            "contract with the user. An unreasonable disadvantage may also arise from the "
            "provision not being clear and comprehensible. In case of doubt, an unreasonable "
            "disadvantage is presumed if a provision is incompatible with essential principles "
            "of the statutory provision from which it deviates, or restricts essential rights "
            "or duties inherent in the nature of the contract to such an extent that attainment "
            "of the contractual purpose is jeopardised."
        ),
        "topic": "unfair_terms",
    },
    {
        "id": "§433",
        "title": "Typical duties in a contract of sale",
        "keywords": ["sale", "purchase", "seller", "buyer", "ownership", "goods", "price", "delivery"],
        "text": (
            "Under a contract of sale, the seller of a thing is obliged to deliver the thing "
            "to the buyer and to procure ownership of the thing for the buyer. The seller must "
            "procure the thing for the buyer free from material and legal defects. The buyer "
            "is obliged to pay the seller the agreed purchase price and to accept delivery of "
            "the thing purchased."
        ),
        "topic": "sale",
    },
    {
        "id": "§434",
        "title": "Material defect",
        "keywords": ["defect", "material defect", "conformity", "agreed quality", "fitness for purpose",
                     "warranty", "sale of goods"],
        "text": (
            "The thing is free from material defects if, upon the passing of risk, it has the "
            "agreed quality. To the extent that the quality has not been agreed, the thing is "
            "free from material defects if it is suitable for the use assumed under the contract "
            "or for the customary use and has a quality which is usual in things of the same "
            "type and which the buyer can expect given the type of thing. A deviation that is "
            "immaterial is disregarded."
        ),
        "topic": "warranty",
    },
    {
        "id": "§611",
        "title": "Typical duties in an employment contract",
        "keywords": ["employment", "service", "employer", "employee", "remuneration", "work", "duties"],
        "text": (
            "Under an employment contract, the person promising services is obliged to render "
            "the agreed services. The services may be of any type. The other party is obliged "
            "to pay the agreed remuneration."
        ),
        "topic": "employment",
    },
    {
        "id": "§823",
        "title": "Liability in damages",
        "keywords": ["tort", "liability", "damages", "unlawful", "body", "health", "property",
                     "negligence", "intentional", "statutory provision"],
        "text": (
            "A person who, intentionally or negligently, unlawfully injures the life, body, "
            "health, freedom, property or another right of another person is liable to make "
            "compensation to the other party for the damage arising from this. The same duty "
            "is held by a person who commits a breach of a statute that is intended to protect "
            "another person. If, according to the contents of the statute, it may also be "
            "breached without fault, then liability to compensate only exists in the event of "
            "fault."
        ),
        "topic": "tort",
    },
    {
        "id": "§985",
        "title": "Claim for delivery",
        "keywords": ["property", "ownership", "possession", "claim", "rei vindicatio", "delivery"],
        "text": (
            "The owner may require the possessor to return the thing."
        ),
        "topic": "property",
    },
]
