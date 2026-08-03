# Short Name Rules

TagFil separates the compact filename from the long description. The compact
filename should be stable, readable, and friendly to Windows, OneDrive, and
SharePoint path limits.

## Format

```text
TYPE-YEAR-ENTITY-SEQUENCE.ext
TYPE-YEAR-ENTITY-QUALIFIER-SEQUENCE.ext
```

Examples:

```text
FAC-2026-ACME-014.pdf
CON-2026-BETA-SAS-LEGAL-002.docx
INF-2026-CONTABILIDAD-008.xlsx
```

## Fields

`TYPE` is a compact document type code. Common aliases:

```text
factura     -> FAC
contrato    -> CON
informe     -> INF
certificado -> CER
cotizacion  -> COT
reporte     -> REP
```

`YEAR` comes from the document date, not necessarily from the file creation
date.

`ENTITY` is the client, vendor, department, area, or project. Accents and
symbols are normalized.

`QUALIFIER` is optional. Use it only when it adds real disambiguation, for
example `LEGAL`, `RRHH`, `BOGOTA`, or `RENOVACION`.

`SEQUENCE` is zero-padded to three digits: `001`, `014`, `120`.

## Stored Metadata

When a file is saved from the metadata dialog, TagFil stores these structured
fields in SQLite:

```text
original_name
short_name
document_type
entity
document_date
sequence_number
qualifier
provider
```

These fields are searchable and are intended to map cleanly to future
OneDrive/SharePoint metadata.

## CLI

```powershell
py main.py suggest-name "C:\Docs\Factura renovacion licencias ACME.pdf" --type factura --entity ACME --date 2026-06-15 --seq 14 --name-only
```

Output:

```text
FAC-2026-ACME-014.pdf
```
