"""
AI story featured-image generator.

Uses the OpenAI Images API (gpt-image-1) to create a square editorial
illustration for a news story based on:

  1. A styled text prompt (loaded from ``image_gen_prompt.md``) with the
     story's article headlines substituted in.
  2. (Optional) Locally-cached article images passed as visual references
     via the ``images.edit`` endpoint.  Falls back to ``images.generate``
     when no reference images are available.

Public function
───────────────
    generate_featured_image(story_slug, headlines, ref_image_paths)
        -> (filename | None, image_url | None)
"""

import base64
import io
import logging
from pathlib import Path

import requests as http_requests

from config import IMAGES_DIR, OPENAI_API_KEY

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "image_gen_prompt.md"
JPEG_QUALITY = 90


def _build_prompt(headlines: list[str], has_images: bool) -> str:
    """
    Load the prompt template and substitute the story headlines.

    ``<STORY_HEADLINES>`` → newline-separated list of headlines.
    ``[REFERENCE_IMAGES]`` → placeholder text indicating attached images
                             (or the whole reference section is trimmed when
                             no images are provided).
    """
    template = _PROMPT_PATH.read_text(encoding="utf-8")

    headlines_text = "\n".join(f"- {h}" for h in headlines)
    prompt = template.replace("<STORY_HEADLINES>", headlines_text)

    if has_images:
        prompt = prompt.replace("[REFERENCE_IMAGES]", "(see attached reference photos)")
    else:
        # Drop the REFERENCE PHOTOS paragraph so the model isn't confused
        lines = prompt.splitlines()
        filtered: list[str] = []
        skip = False
        for line in lines:
            if "REFERENCE PHOTOS" in line.upper():
                skip = True
            elif skip and line.strip() and not line.strip().startswith("-"):
                # Next non-empty, non-bullet line ends the skipped block
                skip = False
            if not skip:
                filtered.append(line)
        prompt = "\n".join(filtered)

    return prompt.strip()


def generate_featured_image(
    story_slug: str,
    headlines: list[str],
    ref_image_paths: list[Path],
) -> tuple[str | None, str | None]:
    """
    Generate a square editorial image for the story and save it locally.

    Parameters
    ----------
    story_slug:
        Used to derive the output filename (``{slug}-featured.jpg``).
    headlines:
        Article headlines to inject into the prompt template.
    ref_image_paths:
        Paths to locally-stored article images used as visual references.
        Only paths that actually exist on disk are used.

    Returns
    -------
    (filename, image_url)
        ``filename`` is the basename of the saved JPEG (relative to
        ``IMAGES_DIR``), or ``None`` on failure.
        ``image_url`` is the remote URL returned by the API (may be
        ``None`` for b64 responses).
    """
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError("Pillow is not installed. Run: pip install Pillow") from exc

    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "openai is not installed. Run: pip install openai"
        ) from exc

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env or environment."
        )

    # Only use image paths that exist on disk
    existing_refs = [p for p in ref_image_paths if p.exists()]

    prompt = _build_prompt(headlines, has_images=bool(existing_refs))
    logger.debug(
        "Image generation prompt for %r (%d ref images): %.200s",
        story_slug, len(existing_refs), prompt,
    )

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        if existing_refs:
            # Use edit endpoint so the model can use the reference images
            image_files = [open(p, "rb") for p in existing_refs]
            try:
                response = client.images.edit(
                    model="gpt-image-1",
                    image=image_files,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                )
            finally:
                for f in image_files:
                    f.close()
        else:
            # Text-only generation
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                n=1,
                size="1024x1024",
            )
    except Exception as exc:
        logger.error("OpenAI image API call failed for %r: %s", story_slug, exc)
        return None, None

    # Extract image data from response
    image_data = response.data[0]
    remote_url: str | None = getattr(image_data, "url", None)

    try:
        raw_bytes: bytes | None = None
        b64 = getattr(image_data, "b64_json", None)
        if b64:
            raw_bytes = base64.b64decode(b64)
        elif remote_url:
            resp = http_requests.get(remote_url, timeout=30)
            resp.raise_for_status()
            raw_bytes = resp.content

        if not raw_bytes:
            logger.error("No image data returned by OpenAI for %r", story_slug)
            return None, remote_url

        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{story_slug}-featured.jpg"
        dest = IMAGES_DIR / filename
        img.save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True)
        logger.info("Saved generated featured image for %r → %s", story_slug, filename)
        return filename, remote_url

    except Exception as exc:
        logger.error(
            "Failed to save generated image for %r: %s", story_slug, exc
        )
        return None, remote_url
