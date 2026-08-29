"""Mixed-language line scanning for macaronic word/phrase insertion.

When a line in the poem's main (host) language deliberately drops in a
word or short phrase from another (guest) language -- a Latin tag inside
an otherwise-Spanish sonnet line, an English word inside a Spanish poem,
a Spanish word inside an English one -- running the *whole* line through
the host phonology backend silently mis-scans the guest span:
`SpanishPhonology` doesn't know English orthography, `EnglishPhonology`
doesn't know Latin, and so on. `scan_mixed_line` scans the host and guest
spans separately, through their own backends, and stitches the results
back together in the original word order.

Scope (v1, mid-line-only macaronic insertion): the guest word/phrase is
assumed *not* to be the line's final word -- rhyme extraction
(`rhyme_key`) still runs on the unmodified line through the host backend
alone and is untouched by this module. Cross-language rhyme (the guest
word itself as the rhyme word) is a separate, harder problem, deferred
until there's a real need for it.

Known limitation: sinalefa/elision effects *across* the host/guest
boundary (e.g. a host word ending in a vowel butting against a guest
word starting with one) aren't modelled -- each span is scanned in
isolation. For a single dropped-in word or short phrase this is a minor
syllable-count approximation, not the kind of error that would silently
mis-score a line by more than one syllable.
"""

from __future__ import annotations

import re

from poesia.phonology.base import PhonologyBackend, ScanResult


def scan_mixed_line(
    line: str,
    guest_word: str,
    host: PhonologyBackend,
    guest: PhonologyBackend,
) -> ScanResult:
    """Scan `line` as host-language text with one guest-language span.

    Splits `line` on the first case-insensitive, word-boundary match of
    `guest_word`; scans the host-language text before/after it with
    `host.scan_line`, scans `guest_word` itself with `guest.scan_line`,
    then combines syllable counts and stress patterns in original order.

    Falls back to a plain `host.scan_line(line)` if `guest_word` isn't
    actually present in `line` -- callers should already only reach for
    this once they know the guest word landed, but this keeps the
    function safe to call speculatively.
    """
    match = re.search(rf"\b{re.escape(guest_word)}\b", line, re.IGNORECASE)
    if match is None:
        return host.scan_line(line)

    before, guest_span, after = line[: match.start()], match.group(0), line[match.end() :]

    host_before = host.scan_line(before) if before.strip() else None
    guest_scan = guest.scan_line(guest_span)
    host_after = host.scan_line(after) if after.strip() else None

    ordered = [s for s in (host_before, guest_scan, host_after) if s is not None]

    total_syllables = sum(s.metrical_syllable_count for s in ordered)
    stress_pattern = tuple(st for s in ordered for st in s.stress_pattern)
    violations = [v for s in ordered for v in s.violations]

    return ScanResult(
        line=line,
        metrical_syllable_count=total_syllables,
        stress_pattern=stress_pattern,
        is_valid=all(s.is_valid for s in ordered) and total_syllables > 0,
        violations=violations,
    )
