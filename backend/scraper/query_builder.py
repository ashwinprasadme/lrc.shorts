"""
LLM-powered Google News RSS query builder.

Given a story headline and its cluster article titles, prompts an LLM (via
litellm) to produce a focused, specific search query string that is suitable
for the Google News RSS search endpoint.

Supported operators (from Google News RSS docs):
  "exact phrase"  — for proper nouns, names, places, organisations
  OR              — at least one of two terms must match (uppercase required)
  -term           — exclude a term
  when:Nh         — restrict to the last N hours (applied by the caller, not here)
"""

import logging
import re

from litellm import completion

from config import LITELLM_MODEL

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are a Google News RSS search expert.
Given a news story headline and a list of related article titles about the SAME \
story, produce a single focused Google News RSS search query string.

Supported operators — use them precisely:
- Exact phrase  "term"  — REQUIRED for all proper nouns: people, organisations, \
places, brands.  e.g. "Elon Musk", "Reserve Bank of India"
- AND (implicit) — the default; every space-separated term must appear.  \
Use this as the baseline.
- OR            — at least one of two alternatives must match (uppercase only). \
Use only when the story genuinely has two common phrasings.  \
e.g. "SpaceX" OR "Rocket Lab"
- Exclude  -term  — prepend a minus sign to remove noise terms that would \
pull in unrelated stories.  e.g. -cricket when the story is about a different sport.
- Include  +term  — prepend a plus sign to force a term that might otherwise \
be treated as optional.  Use sparingly for high-signal disambiguating words.

Rules:
- Wrap ALL proper nouns (people, places, organisations, brands) in double quotes.
- Default to AND (implicit spaces); add OR only when genuinely needed.
- Use - to exclude terms that would cause false positives.
- Use + only when a critical disambiguating term must appear in every result.
- Do NOT use intitle:, allintext:, inurl: or any other field modifier.
- Be specific enough to retrieve only articles about this exact story.
- Keep the total query under 12 words (quoted phrases count as one word each).
- Every opening " MUST have a matching closing " — never leave a quote unbalanced.
- Return ONLY the raw query string — no explanation, no surrounding quotes, \
no markdown.
"""


def _sanitize_query(query: str) -> str:
    """
    Fix mismatched/missing quote characters in an LLM-generated query.

    Handles the common failure mode where the model emits  word"  (closing
    quote present but opening quote missing) by prepending the missing ``"``.
    Also closes any phrase left open at the end of the string.
    """
    tokens = query.split()
    result: list[str] = []
    in_phrase = False

    for tok in tokens:
        starts = tok.startswith('"')
        ends   = tok.endswith('"') and tok != '"'  # ignore bare lone-quote tokens

        if not in_phrase:
            if starts and ends and len(tok) > 2:
                # Properly quoted single token: "word"
                result.append(tok)
            elif starts and not ends:
                # Opening a multi-word phrase: "United
                in_phrase = True
                result.append(tok)
            elif not starts and ends:
                # Missing opening quote: word" → "word"
                result.append('"' + tok)
            else:
                result.append(tok)
        else:
            if ends:
                in_phrase = False
            result.append(tok)

    if in_phrase:
        # Close any phrase that was never closed
        result[-1] = result[-1] + '"'

    return ' '.join(result)


def build_search_query(headline: str, article_titles: list[str]) -> str:
    """
    Ask the configured LLM to build a focused Google News RSS search query.

    Falls back to a simple quoted-headline query if the LLM call fails.
    """
    titles_block = "\n".join(f"- {t}" for t in article_titles[:8])
    user_msg = f"Headline: {headline}\n\nRelated article titles:\n{titles_block}"

    try:
        resp = completion(
            model=LITELLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            # temperature=1.0,
            # max_tokens=80,
        )
        query = resp.choices[0].message.content.strip().strip("'")
        query = _sanitize_query(query)
        logger.debug("LLM query for %r → %r", headline[:60], query)
        return query

    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM query build failed (%s); falling back to headline", exc)
        return _headline_fallback(headline)


def _headline_fallback(headline: str) -> str:
    """
    Naive fallback when LLM is unavailable.

    Quotes only the first meaningful clause (up to the first colon, dash, or
    60 characters) so the query stays matchable even for long headlines.
    """
    cleaned = re.sub(r"\s+-\s+[^-]+$", "", headline).strip()
    # Split on the first ':' or ' - ' to get the punchiest clause
    for sep in (":", " - "):
        if sep in cleaned:
            clause = cleaned.split(sep)[0].strip()
            if len(clause) >= 15:  # ignore trivially short first clauses
                return f'"{clause}"'
    # No natural split — truncate to 60 chars at a word boundary
    if len(cleaned) > 60:
        truncated = cleaned[:60].rsplit(" ", 1)[0]
        return f'"{truncated}"'
    return f'"{cleaned}"'
