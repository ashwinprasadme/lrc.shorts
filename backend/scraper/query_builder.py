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

Rules:
- Wrap specific proper nouns (people, places, organisations) in double quotes.
- Terms separated by a space are implicitly AND — use this as the default.
- Use OR (uppercase) only when an alternate phrasing is genuinely needed.
- Do NOT use intitle:, allintext:, inurl: or any other field modifier.
- Be specific enough to retrieve only articles about this exact story.
- Keep the total query under 12 words (quoted phrases count as one word).
- Return ONLY the raw query string — no explanation, no surrounding quotes, \
no markdown.
"""


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
        query = resp.choices[0].message.content.strip().strip('"\'')
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
