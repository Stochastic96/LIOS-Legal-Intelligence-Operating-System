"""GDPR – General Data Protection Regulation structured data."""

from __future__ import annotations

NAME = "GDPR"
FULL_NAME = "General Data Protection Regulation"
REGULATION_NUMBER = "2016/679/EU"
effective_date = "2018-05-25"
last_updated = "2018-05-25"
jurisdictions = ["EU", "DE", "AT", "FR", "NL", "BE", "PL", "ES", "IT", "SE"]

articles = [
    {
        "id": "Art.1",
        "title": "Subject matter and objectives",
        "keywords": ["subject matter", "objectives", "natural persons", "protection", "personal data", "free movement"],
        "text": (
            "This Regulation lays down rules relating to the protection of natural persons "
            "with regard to the processing of personal data and rules relating to the free "
            "movement of personal data. It protects fundamental rights and freedoms of natural "
            "persons and in particular their right to the protection of personal data."
        ),
        "topic": "scope",
    },
    {
        "id": "Art.4",
        "title": "Definitions",
        "keywords": ["definition", "personal data", "processing", "controller", "processor", "consent", "data subject"],
        "text": (
            "'Personal data' means any information relating to an identified or identifiable "
            "natural person ('data subject'). 'Processing' means any operation or set of "
            "operations performed on personal data, including collection, recording, storage, "
            "use, disclosure or erasure. 'Controller' means the natural or legal person which "
            "determines the purposes and means of the processing. 'Processor' means a natural "
            "or legal person which processes personal data on behalf of the controller. "
            "'Consent' means any freely given, specific, informed and unambiguous indication "
            "of agreement by the data subject."
        ),
        "topic": "definitions",
    },
    {
        "id": "Art.5",
        "title": "Principles relating to processing of personal data",
        "keywords": ["principles", "lawfulness", "fairness", "transparency", "purpose limitation",
                     "data minimisation", "accuracy", "storage limitation", "integrity", "confidentiality", "accountability"],
        "text": (
            "Personal data shall be: (a) processed lawfully, fairly and in a transparent manner "
            "in relation to the data subject ('lawfulness, fairness and transparency'); "
            "(b) collected for specified, explicit and legitimate purposes and not further "
            "processed in a manner incompatible with those purposes ('purpose limitation'); "
            "(c) adequate, relevant and limited to what is necessary in relation to the purposes "
            "for which they are processed ('data minimisation'); (d) accurate and where necessary "
            "kept up to date ('accuracy'); (e) kept in a form which permits identification of data "
            "subjects for no longer than necessary ('storage limitation'); (f) processed in a manner "
            "that ensures appropriate security ('integrity and confidentiality'). The controller "
            "shall be responsible for, and be able to demonstrate compliance with, these principles "
            "('accountability')."
        ),
        "topic": "principles",
    },
    {
        "id": "Art.6",
        "title": "Lawfulness of processing",
        "keywords": ["lawfulness", "legal basis", "consent", "contract", "legal obligation",
                     "vital interests", "public interest", "legitimate interests"],
        "text": (
            "Processing shall be lawful only if and to the extent that at least one of the "
            "following applies: (a) the data subject has given consent to the processing; "
            "(b) processing is necessary for the performance of a contract to which the data "
            "subject is party; (c) processing is necessary for compliance with a legal obligation "
            "to which the controller is subject; (d) processing is necessary to protect the "
            "vital interests of the data subject; (e) processing is necessary for the performance "
            "of a task carried out in the public interest; (f) processing is necessary for the "
            "purposes of the legitimate interests pursued by the controller or by a third party, "
            "except where such interests are overridden by the interests or rights of the data "
            "subject."
        ),
        "topic": "lawful_basis",
    },
    {
        "id": "Art.7",
        "title": "Conditions for consent",
        "keywords": ["consent", "conditions", "withdrawal", "freely given", "unambiguous", "burden of proof"],
        "text": (
            "Where processing is based on consent, the controller shall be able to demonstrate "
            "that the data subject has consented to the processing. The request for consent shall "
            "be presented in a manner clearly distinguishable from other matters. The data subject "
            "shall have the right to withdraw consent at any time. Withdrawal of consent shall not "
            "affect the lawfulness of processing based on consent before its withdrawal. Prior to "
            "giving consent, the data subject shall be informed thereof."
        ),
        "topic": "consent",
    },
    {
        "id": "Art.13",
        "title": "Information to be provided where personal data are collected from the data subject",
        "keywords": ["information", "transparency", "privacy notice", "data collection", "controller identity",
                     "purposes", "retention period", "rights"],
        "text": (
            "Where personal data relating to a data subject are collected from the data subject, "
            "the controller shall provide the following information: (a) the identity and contact "
            "details of the controller; (b) the purposes of the processing and the legal basis; "
            "(c) the legitimate interests pursued by the controller where processing is based on "
            "legitimate interests; (d) the recipients of the personal data; (e) the period for "
            "which the personal data will be stored; (f) the existence of the right to request "
            "access, rectification, erasure, restriction and portability; (g) where processing "
            "is based on consent, the right to withdraw consent at any time."
        ),
        "topic": "transparency",
    },
    {
        "id": "Art.17",
        "title": "Right to erasure ('right to be forgotten')",
        "keywords": ["erasure", "right to be forgotten", "deletion", "withdraw consent", "unlawful processing"],
        "text": (
            "The data subject shall have the right to obtain from the controller the erasure of "
            "personal data concerning him or her without undue delay and the controller shall have "
            "the obligation to erase personal data without undue delay where one of the following "
            "grounds applies: (a) the personal data are no longer necessary in relation to the "
            "purposes for which they were collected; (b) the data subject withdraws consent and "
            "there is no other legal ground for the processing; (c) the data subject objects to "
            "the processing and there are no overriding legitimate grounds; (d) the personal data "
            "have been unlawfully processed; (e) the personal data have to be erased for compliance "
            "with a legal obligation."
        ),
        "topic": "rights",
    },
    {
        "id": "Art.25",
        "title": "Data protection by design and by default",
        "keywords": ["privacy by design", "privacy by default", "data protection by design",
                     "technical measures", "organisational measures", "pseudonymisation"],
        "text": (
            "Taking into account the state of the art and the costs of implementation, the "
            "controller shall implement appropriate technical and organisational measures, such as "
            "pseudonymisation, which are designed to implement data-protection principles, such as "
            "data minimisation, in an effective manner and to integrate the necessary safeguards "
            "into the processing. The controller shall implement appropriate technical and "
            "organisational measures for ensuring that, by default, only personal data which are "
            "necessary for each specific purpose of the processing are processed."
        ),
        "topic": "privacy_by_design",
    },
    {
        "id": "Art.32",
        "title": "Security of processing",
        "keywords": ["security", "technical measures", "organisational measures", "encryption",
                     "pseudonymisation", "confidentiality", "integrity", "availability", "breach"],
        "text": (
            "Taking into account the state of the art, the costs of implementation and the nature, "
            "scope, context and purposes of processing, the controller and the processor shall "
            "implement appropriate technical and organisational measures to ensure a level of "
            "security appropriate to the risk, including: (a) the pseudonymisation and encryption "
            "of personal data; (b) the ability to ensure the ongoing confidentiality, integrity, "
            "availability and resilience of processing systems; (c) the ability to restore the "
            "availability and access to personal data in a timely manner in the event of a physical "
            "or technical incident; (d) a process for regularly testing and evaluating the "
            "effectiveness of technical and organisational measures."
        ),
        "topic": "security",
    },
    {
        "id": "Art.33",
        "title": "Notification of a personal data breach to the supervisory authority",
        "keywords": ["data breach", "notification", "supervisory authority", "72 hours", "breach notification"],
        "text": (
            "In the case of a personal data breach, the controller shall without undue delay and, "
            "where feasible, not later than 72 hours after having become aware of it, notify the "
            "personal data breach to the supervisory authority, unless the personal data breach "
            "is unlikely to result in a risk to the rights and freedoms of natural persons. "
            "The notification shall describe: (a) the nature of the breach; (b) the categories "
            "and approximate number of individuals and records concerned; (c) the contact details "
            "of the data protection officer; (d) the likely consequences; (e) the measures taken "
            "or proposed to address the breach."
        ),
        "topic": "breach_notification",
    },
    {
        "id": "Art.37",
        "title": "Designation of the data protection officer",
        "keywords": ["data protection officer", "DPO", "designation", "public authority", "large-scale processing"],
        "text": (
            "The controller and the processor shall designate a data protection officer where: "
            "(a) the processing is carried out by a public authority or body; (b) the core "
            "activities of the controller or the processor consist of processing operations which "
            "require regular and systematic monitoring of data subjects on a large scale; or "
            "(c) the core activities of the controller or the processor consist of processing on "
            "a large scale of special categories of data."
        ),
        "topic": "dpo",
    },
    {
        "id": "Art.83",
        "title": "General conditions for imposing administrative fines",
        "keywords": ["fine", "penalty", "administrative fine", "sanction", "20 million", "4%", "turnover",
                     "enforcement"],
        "text": (
            "Infringements of the following provisions shall be subject to administrative fines "
            "up to 20 000 000 EUR, or in the case of an undertaking, up to 4% of the total "
            "worldwide annual turnover of the preceding financial year, whichever is higher: "
            "the basic principles for processing including conditions for consent (Arts. 5, 6, 7, 9); "
            "the data subjects' rights (Arts. 12 to 22); the transfers to recipients in third "
            "countries (Arts. 44 to 49). Infringements of other obligations shall be subject "
            "to administrative fines up to 10 000 000 EUR or up to 2% of total worldwide annual "
            "turnover, whichever is higher."
        ),
        "topic": "enforcement",
    },
]
