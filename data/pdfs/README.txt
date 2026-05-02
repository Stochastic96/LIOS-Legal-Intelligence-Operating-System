Place your manually-downloaded regulation PDF files here.
LIOS will scan this folder automatically when you run:

    python scripts/ingest_pdfs.py

Supported file naming conventions (regulation is inferred from the filename):

    csrd_directive.pdf      → CSRD
    esrs_standards.pdf      → ESRS
    eu_taxonomy_*.pdf       → EU_TAXONOMY
    sfdr_*.pdf              → SFDR
    gdpr_*.pdf              → GDPR
    lksg_*.pdf              → LkSG
    any_other_name.pdf      → uses the filename stem as-is

Where to download PDFs:
    CSRD     https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022L2464
    ESRS     https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023R2772
    Taxonomy https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32020R0852
    SFDR     https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32019R2088
    GDPR     https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32016R0679
    LkSG     https://www.gesetze-im-internet.de/lksg/

This folder is intentionally kept empty in the repository.
