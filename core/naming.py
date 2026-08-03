"""Short filename generation for TagFil.

The generated name is intentionally compact and SharePoint/Windows friendly:

    FAC-2026-ACME-014.pdf
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


MAX_FILENAME_LEN = 120
DEFAULT_SEQUENCE_WIDTH = 3
INVALID_FILENAME_CHARS = '<>:"/\\|?*\x00'

DOCUMENT_TYPE_ALIASES = {
    "acta": "ACT",
    "certificado": "CER",
    "contrato": "CON",
    "cotizacion": "COT",
    "factura": "FAC",
    "informe": "INF",
    "memorando": "MEM",
    "orden": "OC",
    "presentacion": "PPT",
    "propuesta": "PRO",
    "recibo": "REC",
    "reporte": "REP",
}


@dataclass(frozen=True)
class ShortNameParts:
    document_type: str
    year: int
    entity: str
    sequence: int
    extension: str
    qualifier: str = ""


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _compact_token(value: str, max_len: int) -> str:
    value = _strip_accents(value or "").upper()
    value = re.sub(r"[^A-Z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:max_len].strip("-")


def normalize_document_type(value: str) -> str:
    """Return a 2-5 character document type code."""
    token = _compact_token(value, 20)
    if not token:
        return "DOC"

    alias_key = token.lower().replace("-", "")
    if alias_key in DOCUMENT_TYPE_ALIASES:
        return DOCUMENT_TYPE_ALIASES[alias_key]

    if len(token) <= 5:
        return token
    return token[:5]


def normalize_entity(value: str) -> str:
    """Return a compact entity/client/vendor/area code."""
    return _compact_token(value, 12) or "SIN-ENT"


def parse_year(value: str | int | date | None) -> int:
    """Extract a year from common date inputs."""
    if value is None or value == "":
        return date.today().year
    if isinstance(value, int):
        if 1900 <= value <= 2999:
            return value
        raise ValueError("El ano debe estar entre 1900 y 2999")
    if isinstance(value, date):
        return value.year

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y"):
        try:
            return datetime.strptime(text, fmt).year
        except ValueError:
            pass

    match = re.search(r"(19|20|21)\d{2}", text)
    if match:
        return int(match.group(0))

    raise ValueError(f"No se pudo extraer el ano de: {value}")


def normalize_extension(original_path: str | Path, extension: str | None = None) -> str:
    ext = extension if extension is not None else Path(original_path).suffix
    ext = (ext or "").strip().lower()
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    ext = "".join(ch for ch in ext if ch not in INVALID_FILENAME_CHARS)
    return ext[:16]


def build_short_name(parts: ShortNameParts) -> str:
    doc_type = normalize_document_type(parts.document_type)
    entity = normalize_entity(parts.entity)
    qualifier = _compact_token(parts.qualifier, 12)
    sequence = f"{int(parts.sequence):0{DEFAULT_SEQUENCE_WIDTH}d}"

    segments = [doc_type, str(parts.year), entity]
    if qualifier:
        segments.append(qualifier)
    segments.append(sequence)

    stem = "-".join(segments)
    max_stem_len = MAX_FILENAME_LEN - len(parts.extension)
    if len(stem) > max_stem_len:
        stem = stem[:max_stem_len].rstrip("-")
    return f"{stem}{parts.extension}"


def generate_short_name(
    original_path: str | Path,
    document_type: str,
    entity: str,
    sequence: int,
    document_date: str | int | date | None = None,
    qualifier: str = "",
    extension: str | None = None,
) -> str:
    """Generate a compact file name while preserving the file extension."""
    if int(sequence) < 1:
        raise ValueError("El consecutivo debe ser mayor o igual a 1")

    parts = ShortNameParts(
        document_type=document_type,
        year=parse_year(document_date),
        entity=entity,
        sequence=int(sequence),
        qualifier=qualifier,
        extension=normalize_extension(original_path, extension),
    )
    return build_short_name(parts)


def suggest_short_path(
    original_path: str | Path,
    document_type: str,
    entity: str,
    sequence: int,
    document_date: str | int | date | None = None,
    qualifier: str = "",
) -> Path:
    """Return the suggested path next to the original file."""
    path = Path(original_path)
    return path.with_name(
        generate_short_name(
            original_path=path,
            document_type=document_type,
            entity=entity,
            sequence=sequence,
            document_date=document_date,
            qualifier=qualifier,
        )
    )

