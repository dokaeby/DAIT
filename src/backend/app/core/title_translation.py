"""Local, evidence-based disambiguation for bilingual news titles; no network I/O."""

import re

_POLITICS = re.compile(
    r"\b(?:elections?|congress(?:ional)?|senat(?:e|ors?)|democrats?|"
    r"republicans?|voters?|ballots?|gop|politic(?:s|al))\b"
    r"|중간\s*선거|민주당|공화당|유권자|의회",
    re.I,
)
_MIDTERMS = re.compile(r"\bmidterms?\b(?!\s+elections?\b)", re.I)


def contextualize_title(title: str, context: str) -> str:
    """Inspect complete supplied article evidence locally, not just the title/teaser."""
    if _MIDTERMS.search(title) and _POLITICS.search(title + " " + context):
        return _MIDTERMS.sub("midterm elections", title)
    return title


def repair_contextual_title(title: str, context: str) -> str:
    """Repair a stored exam mistranslation only with explicit political evidence.

    No DB rewrite or external translation is performed. Academic context without
    political evidence and titles lacking a stored Korean translation are preserved.
    """
    original, separator, translated = title.partition(" ||| ")
    if (
        separator
        and re.search(r"\bmidterms?\b", original, re.I)
        and _POLITICS.search(original + " " + context)
    ):
        corrected = re.sub(r"중간\s*고사", "중간선거", translated)
        return original + separator + corrected
    return title
