"""
Representative article selector.

Layered strategy
────────────────
1. Always keep the lead article (is_lead=True).
2. Fuzzy-dedup: collapse near-identical titles using Jaccard similarity on
   word tokens, keeping the first seen (leads have priority).
3. MMR (Maximum Marginal Relevance): greedily fill remaining slots by picking
   the candidate that best balances relevance-to-story with diversity-from-
   already-selected, using TF-IDF cosine similarity on titles.
4. Publisher cap: integrated into MMR — skip a candidate whose publisher
   already has `source_cap` items in the selected set.  If every remaining
   candidate is capped, the cap is relaxed for that round as a fallback.

Entry point:  select_articles(articles, story_headline, target, source_cap)
"""

import re
from collections import Counter
from math import log, sqrt


# ── Tokenisation ──────────────────────────────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens (≥2 chars)."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 2]


def _token_set(text: str) -> set[str]:
    return set(_tokenize(text))


# ── Jaccard similarity ────────────────────────────────────────────────────────


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── TF-IDF with cosine similarity ─────────────────────────────────────────────


def _build_tfidf_vectors(docs: list[list[str]]) -> list[dict[int, float]]:
    """
    Build L2-normalised TF-IDF vectors for a list of tokenised documents.
    Returns a list of sparse vectors {term_index: weight}.
    """
    vocab: dict[str, int] = {}
    for tokens in docs:
        for t in tokens:
            if t not in vocab:
                vocab[t] = len(vocab)

    n = len(docs)
    df: Counter[int] = Counter()
    for tokens in docs:
        for t in set(tokens):
            if t in vocab:
                df[vocab[t]] += 1

    # IDF with add-1 smoothing so unseen terms still get meaningful weight
    idf: dict[int, float] = {
        idx: log((n + 1) / (cnt + 1)) + 1.0 for idx, cnt in df.items()
    }

    vectors: list[dict[int, float]] = []
    for tokens in docs:
        tf: Counter[int] = Counter(vocab[t] for t in tokens if t in vocab)
        vec = {idx: cnt * idf.get(idx, 1.0) for idx, cnt in tf.items()}
        norm = sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({idx: v / norm for idx, v in vec.items()})

    return vectors


def _cosine(a: dict[int, float], b: dict[int, float]) -> float:
    """Dot product of two L2-normalised sparse vectors = cosine similarity."""
    if not a or not b:
        return 0.0
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    return sum(v * large.get(k, 0.0) for k, v in small.items())


# ── Public API ────────────────────────────────────────────────────────────────


def select_articles(
    articles: list[dict],
    story_headline: str,
    target: int,
    source_cap: int,
) -> list[dict]:
    """
    Select up to `target` representative articles from `articles`.

    Parameters
    ----------
    articles:
        Full article list (may be ~100 items).  Each dict must contain at
        minimum the keys: 'title', 'url', 'source_name', 'is_lead'.
    story_headline:
        Parent story headline — used as the MMR relevance anchor so that
        selected articles are topically on-point, not just mutually diverse.
    target:
        Maximum number of articles to return.
    source_cap:
        Maximum articles from the same publisher allowed in the result.

    Returns
    -------
    List of selected articles, lead(s) first, then in MMR selection order.
    If ``len(articles) <= target``, returns the full list unchanged.
    """
    if len(articles) <= target:
        return list(articles)

    # ── Step 1: separate leads ────────────────────────────────────────────────
    leads = [a for a in articles if a.get("is_lead")]
    non_leads = [a for a in articles if not a.get("is_lead")]

    # ── Step 2: fuzzy-dedup non-leads (Jaccard on word tokens) ───────────────
    DEDUP_THRESHOLD = 0.65
    survived: list[dict] = []
    survived_token_sets: list[set[str]] = []

    for art in non_leads:
        tok = _token_set(art["title"])
        if all(_jaccard(tok, st) < DEDUP_THRESHOLD for st in survived_token_sets):
            survived.append(art)
            survived_token_sets.append(tok)

    # ── Steps 3 & 4: MMR selection with integrated publisher cap ─────────────
    remaining_slots = max(0, target - len(leads))
    if remaining_slots == 0 or not survived:
        return leads[:target]

    # Build TF-IDF over story headline (index 0) + all survived article titles
    all_docs = [_tokenize(story_headline)] + [
        _tokenize(a["title"]) for a in survived
    ]
    vectors = _build_tfidf_vectors(all_docs)
    story_vec = vectors[0]
    candidate_vecs = vectors[1:]  # aligned index-for-index with `survived`

    # Initialise publisher counts from leads that are already committed
    source_counts: Counter[str] = Counter(
        lead.get("source_name") or "" for lead in leads
    )
    selected_indices: list[int] = []
    remaining: set[int] = set(range(len(survived)))

    for _ in range(remaining_slots):
        if not remaining:
            break

        best_idx: int | None = None
        best_score = float("-inf")

        # Separate fallback (ignores cap) in case all candidates are blocked
        fallback_idx: int | None = None
        fallback_score = float("-inf")

        for idx in remaining:
            src = survived[idx].get("source_name") or ""
            rel = _cosine(candidate_vecs[idx], story_vec)

            if selected_indices:
                max_sim = max(
                    _cosine(candidate_vecs[idx], candidate_vecs[j])
                    for j in selected_indices
                )
            else:
                max_sim = 0.0

            # λ=0.6 weights relevance slightly more than diversity
            score = 0.6 * rel - 0.4 * max_sim

            if score > fallback_score:
                fallback_score = score
                fallback_idx = idx

            if source_counts[src] < source_cap and score > best_score:
                best_score = score
                best_idx = idx

        # If publisher cap blocked every remaining candidate, relax it
        chosen = best_idx if best_idx is not None else fallback_idx
        if chosen is None:
            break

        selected_indices.append(chosen)
        remaining.discard(chosen)
        src = survived[chosen].get("source_name") or ""
        source_counts[src] += 1

    return leads + [survived[i] for i in selected_indices]
