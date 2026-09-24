"""Deterministic PII detection and placeholder replacement (FR-001, FR-002; research R5, R6).

Nothing here calls a model. The same detectors serve three purposes: the first scrubbing pass,
the re-scan after model suggestions, and the final privacy guard on everything written out.
"""

import re
from dataclasses import dataclass

from claim_intake.contracts import PiiType

PLACEHOLDER = re.compile(r"\[[A-Z_]+_\d+\]")

# Optional words between a context word and its value, e.g. "policy number: ".
_FILLER = r"(?:\s*(?:number|num|no\.?|#|is|was|:))*\s*"
_HAS_DIGIT = r"(?=[A-Za-z0-9-]*\d)"
_STREET_SUFFIX = (
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court|"
    r"Pl|Place|Pkwy|Parkway|Hwy|Highway|Cir|Circle|Ter|Terrace)"
)


def _luhn_valid(value: str) -> bool:
    digits = [int(d) for d in value if d.isdigit()]
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit = digit * 2 - 9 if digit > 4 else digit * 2
        total += digit
    return total % 10 == 0


@dataclass(frozen=True)
class _Detector:
    pii_type: PiiType
    pattern: re.Pattern[str]
    validate: object = None  # optional callable(value) -> bool


# Order matters only as a tie-breaker: the most specific digit patterns come first.
_DETECTORS = [
    _Detector(
        PiiType.SSN,
        re.compile(r"(?<!\d)(?P<value>(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4})(?!\d)"),
    ),
    _Detector(
        PiiType.SSN,
        re.compile(
            r"\b(?:SSN|social security)" + _FILLER + r"(?P<value>(?!000|666|9\d\d)\d{9})(?!\d)",
            re.IGNORECASE,
        ),
    ),
    _Detector(
        PiiType.CARD,
        re.compile(r"(?<!\d)(?P<value>\d(?:[ -]?\d){12,18})(?!\d)"),
        _luhn_valid,
    ),
    _Detector(PiiType.EMAIL, re.compile(r"(?P<value>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)")),
    _Detector(
        PiiType.PHONE,
        re.compile(
            r"(?<![\w+])(?P<value>(?:\+?1[ .-]?)?(?:\(\d{3}\)\s?|\d{3}[ .-])\d{3}[ .-]\d{4}"
            r"|\d{10})(?!\d)"
        ),
    ),
    _Detector(
        PiiType.VIN,
        re.compile(
            r"\b(?P<value>(?=[A-HJ-NPR-Z0-9]*\d)(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])"
            r"[A-HJ-NPR-Z0-9]{17})\b"
        ),
    ),
    _Detector(
        PiiType.DOB,
        re.compile(
            r"\b(?:born(?: on)?|DOB|date of birth|birthday)" + _FILLER
            + r"(?P<value>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Z][a-z]+ \d{1,2},? \d{4})",
            re.IGNORECASE,
        ),
    ),
    _Detector(
        PiiType.POLICY_NUMBER,
        re.compile(
            r"\bpolicy" + _FILLER + _HAS_DIGIT + r"(?P<value>[A-Z0-9][A-Z0-9-]{4,14})\b",
            re.IGNORECASE,
        ),
    ),
    _Detector(
        PiiType.PLATE,
        re.compile(
            r"\b(?:licen[cs]e plate|plate|registration)" + _FILLER
            + r"(?=[A-Za-z0-9 -]{0,9}\d)(?P<value>[A-Z0-9]{1,4}(?:[ -]?[A-Z0-9]{1,4})?)\b",
            re.IGNORECASE,
        ),
    ),
    _Detector(
        PiiType.DRIVER_LICENSE,
        re.compile(
            r"\b(?:driver'?s? licen[cs]e|licen[cs]e|DL)" + _FILLER + _HAS_DIGIT
            + r"(?P<value>[A-Z0-9][A-Z0-9-]{4,14})\b",
            re.IGNORECASE,
        ),
    ),
    _Detector(
        PiiType.ADDRESS,
        re.compile(r"\b(?P<value>\d{1,6}\s+(?:[A-Z][a-z]+\s+){1,4}" + _STREET_SUFFIX + r")\b"),
    ),
]


@dataclass(frozen=True)
class _Match:
    start: int
    end: int
    pii_type: PiiType
    value: str


def _find_matches(text: str) -> list[_Match]:
    """All non-overlapping PII values; earliest start wins, then longest, then detector order."""
    candidates = []
    for priority, detector in enumerate(_DETECTORS):
        for m in detector.pattern.finditer(text):
            value = m.group("value")
            if detector.validate and not detector.validate(value):
                continue
            candidates.append((m.start("value"), -len(value), priority, detector.pii_type, value))
    chosen: list[_Match] = []
    for start, neg_len, _, pii_type, value in sorted(candidates):
        end = start - neg_len
        if chosen and start < chosen[-1].end:
            continue
        chosen.append(_Match(start, end, pii_type, value))
    return chosen


def _sorted_types(types) -> list[PiiType]:
    return sorted(set(types))


def find_pii(text: str) -> list[PiiType]:
    """The types of any PII still present. Placeholders never match."""
    return _sorted_types(m.pii_type for m in _find_matches(text))


def _next_number(text: str, pii_type: PiiType) -> int:
    used = [int(n) for n in re.findall(rf"\[{pii_type}_(\d+)\]", text)]
    return max(used, default=0) + 1


def scrub_patterns(text: str) -> tuple[str, list[PiiType]]:
    """Replace every pattern-detectable value with a stable, numbered placeholder."""
    matches = _find_matches(text)
    placeholders: dict[tuple[PiiType, str], str] = {}
    counters: dict[PiiType, int] = {}
    for m in matches:
        key = (m.pii_type, m.value)
        if key not in placeholders:
            counters[m.pii_type] = counters.get(m.pii_type, _next_number(text, m.pii_type) - 1) + 1
            placeholders[key] = f"[{m.pii_type}_{counters[m.pii_type]}]"
    for m in reversed(matches):
        text = text[: m.start] + placeholders[(m.pii_type, m.value)] + text[m.end :]
    return text, _sorted_types(m.pii_type for m in matches)



def replace_outside_placeholders(text: str, value: str, replacement: str) -> str:
    """Replace `value` everywhere except inside existing placeholders."""
    parts = PLACEHOLDER.split(text)
    kept = PLACEHOLDER.findall(text)
    out = [parts[0].replace(value, replacement)]
    for placeholder, part in zip(kept, parts[1:], strict=True):
        out.append(placeholder)
        out.append(part.replace(value, replacement))
    return "".join(out)


def appears_outside_placeholders(text: str, value: str) -> bool:
    return any(value in part for part in PLACEHOLDER.split(text))
