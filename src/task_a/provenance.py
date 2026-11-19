"""Group documents that copy the same original text.

Five outlets reprinting one press release are one source, not five. Web
documents carry no hand-made provenance label, so the server groups the
documents an agent has read by how much of their body text they share.

Measure: containment of character 8-gram shingles over normalised text,
|A ∩ B| / min(|A|, |B|). Containment rather than Jaccard, because a reprint
usually adds an outlet name, a byline or a paragraph, which lowers Jaccard but
leaves most of the shorter text inside the longer one. Groups are the
connected components of pairs at or above the threshold.

Known blind spot: a reprint rewritten in different words shares few shingles
and ends up in its own group. That is the hard case for this method.
"""

from __future__ import annotations

import re

SHINGLE = 8
THRESHOLD = 0.4
_KEEP = re.compile(r"[0-9a-z가-힣]+")


def normalise(text: str) -> str:
    return "".join(_KEEP.findall((text or "").lower()))


def shingles(text: str, n: int = SHINGLE) -> frozenset[str]:
    norm = normalise(text)
    if len(norm) <= n:
        return frozenset({norm}) if norm else frozenset()
    return frozenset(norm[i:i + n] for i in range(len(norm) - n + 1))


def containment(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


#: Text that says it is passing on someone else's report. Such a document is a
#: secondary copy and does not count as an independent source. "관계자에 따르면"
#: (a source told the reporter) is deliberately not matched.
_DERIVATIVE = re.compile(
    r"(보도|기사)(에|를)?\s*(따르면|인용|옮기)|according to (a |the )?(report|article)|"
    r"as reported by|first reported by", re.IGNORECASE)


def is_derivative(text: str) -> bool:
    return bool(_DERIVATIVE.search(text or ""))


def group_documents(texts: dict[str, str], threshold: float = THRESHOLD) -> dict[str, str]:
    """Map each document id to a group label 'auto-1', 'auto-2', ... in input order."""
    ids = list(texts)
    sh = {i: shingles(texts[i]) for i in ids}
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a_idx, a in enumerate(ids):
        for b in ids[a_idx + 1:]:
            if containment(sh[a], sh[b]) >= threshold:
                parent[find(b)] = find(a)

    labels: dict[str, str] = {}
    out = {}
    for i in ids:
        root = find(i)
        labels.setdefault(root, f"auto-{len(labels) + 1}")
        out[i] = labels[root]
    return out
