#!/usr/bin/env python3
"""Validate story JSON files for required fields and formatting."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Get the project root directory
script_dir = Path(__file__).parent
project_root = script_dir.parent
stories_dir = project_root / "content" / "stories"

# Required fields for validation
REQUIRED_FIELDS = [
    "slug", "title", "topic", "publishedAt",
    "neutral", "left", "right", "sources"
]

REQUIRED_NEUTRAL_FIELDS = ["summary"]
REQUIRED_LENS_FIELDS = ["take", "quotes"]
REQUIRED_QUOTE_FIELDS = ["text", "speaker", "sources"]
REQUIRED_SOURCE_FIELDS = ["name", "url"]

errors: List[str] = []
warnings: List[str] = []


def validate_story(file_name: str, story: Dict[str, Any]) -> None:
    """Validate a single story object."""
    
    # Check required top-level fields
    for field in REQUIRED_FIELDS:
        if field not in story:
            errors.append(f"{file_name}: Missing required field '{field}'")
    
    # Validate slug format (URL-safe)
    if "slug" in story:
        if not re.match(r'^[a-z0-9-]+$', story["slug"]):
            errors.append(f"{file_name}: Slug must be lowercase alphanumeric with hyphens only")
    
    # Validate publishedAt is a valid ISO date
    if "publishedAt" in story:
        try:
            datetime.fromisoformat(story["publishedAt"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            errors.append(f"{file_name}: Invalid publishedAt date format")
    
    # Validate neutral lens
    if "neutral" in story:
        for field in REQUIRED_NEUTRAL_FIELDS:
            if field not in story["neutral"]:
                errors.append(f"{file_name}: Missing neutral.{field}")
    
    # Validate left and right lenses
    for side in ["left", "right"]:
        if side not in story:
            continue
        
        for field in REQUIRED_LENS_FIELDS:
            if field not in story[side]:
                errors.append(f"{file_name}: Missing {side}.{field}")
        
        # Validate quotes
        if "quotes" in story[side]:
            quotes = story[side]["quotes"]
            
            if not isinstance(quotes, list):
                errors.append(f"{file_name}: {side}.quotes must be an array")
            elif len(quotes) == 0:
                warnings.append(f"{file_name}: {side}.quotes is empty")
            else:
                for idx, quote in enumerate(quotes):
                    for field in REQUIRED_QUOTE_FIELDS:
                        if field not in quote:
                            errors.append(f"{file_name}: Missing {side}.quotes[{idx}].{field}")
                    
                    # Validate quote sources
                    if "sources" in quote:
                        quote_sources = quote["sources"]
                        
                        if not isinstance(quote_sources, list):
                            errors.append(f"{file_name}: {side}.quotes[{idx}].sources must be an array")
                        else:
                            for sidx, source in enumerate(quote_sources):
                                for field in REQUIRED_SOURCE_FIELDS:
                                    if field not in source:
                                        errors.append(
                                            f"{file_name}: Missing {side}.quotes[{idx}].sources[{sidx}].{field}"
                                        )
                                
                                # Validate URL format
                                if "url" in source and not source["url"].startswith("http"):
                                    errors.append(
                                        f"{file_name}: {side}.quotes[{idx}].sources[{sidx}].url must start with http"
                                    )
    
    # Validate sources
    if "sources" in story:
        sources = story["sources"]
        
        if not isinstance(sources, list):
            errors.append(f"{file_name}: sources must be an array")
        elif len(sources) == 0:
            warnings.append(f"{file_name}: sources is empty")
        else:
            for idx, source in enumerate(sources):
                for field in REQUIRED_SOURCE_FIELDS:
                    if field not in source:
                        errors.append(f"{file_name}: Missing sources[{idx}].{field}")
                
                # Validate URL format
                if "url" in source and not source["url"].startswith("http"):
                    errors.append(f"{file_name}: sources[{idx}].url must start with http")
    
    # Check content length recommendations
    if "neutral" in story and "summary" in story["neutral"]:
        summary_len = len(story["neutral"]["summary"])
        if summary_len > 250:
            warnings.append(
                f"{file_name}: neutral.summary is quite long ({summary_len} chars), "
                "consider shortening for mobile"
            )
    
    for side in ["left", "right"]:
        if side in story and "take" in story[side]:
            take_len = len(story[side]["take"])
            if take_len > 250:
                warnings.append(
                    f"{file_name}: {side}.take is quite long ({take_len} chars), "
                    "consider shortening for mobile"
                )


def main():
    """Main validation routine."""
    
    # Check if stories directory exists
    if not stories_dir.exists():
        print(f"❌ Stories directory not found: {stories_dir}")
        sys.exit(1)
    
    # Find all JSON files
    json_files = list(stories_dir.glob("*.json"))
    
    if not json_files:
        print("⚠️  No story files found. Run 'npm run make:stubs' to generate test data.")
        sys.exit(0)
    
    print(f"🔍 Validating {len(json_files)} story files...\n")
    
    # Validate each file
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                story = json.load(f)
            validate_story(file_path.name, story)
        except json.JSONDecodeError as e:
            errors.append(f"{file_path.name}: Failed to parse JSON - {e.msg}")
        except Exception as e:
            errors.append(f"{file_path.name}: Error reading file - {str(e)}")
    
    # Report results
    if errors:
        print("❌ ERRORS:\n")
        for err in errors:
            print(f"  • {err}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS:\n")
        for warn in warnings:
            print(f"  • {warn}")
        print()
    
    if not errors:
        print("✅ All stories validated successfully!")
        if warnings:
            print(f"   ({len(warnings)} warnings to review)")
        sys.exit(0)
    else:
        print(f"❌ Validation failed with {len(errors)} error(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
