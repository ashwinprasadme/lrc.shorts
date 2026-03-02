#!/usr/bin/env python3
"""Generate stub story data for frontend development."""

import json
import os
from pathlib import Path

# Get the project root directory
script_dir = Path(__file__).parent
project_root = script_dir.parent
stories_dir = project_root / "content" / "stories"

# Ensure the stories directory exists
stories_dir.mkdir(parents=True, exist_ok=True)

stub_stories = [
    {
        "slug": "ai-chip-export-rules-tighten",
        "title": "AI chip export rules tighten",
        "topic": "Tech & geopolitics",
        "publishedAt": "2026-03-01T06:30:00Z",
        "coverImage": "https://picsum.photos/seed/ai-chip/800/640",
        "neutral": {
            "summary": "The U.S. government announced new restrictions on AI chip exports to certain countries, aiming to maintain technological advantage in artificial intelligence development."
        },
        "left": {
            "take": "These restrictions show the need for global cooperation on AI development. Hoarding technology won't make us safer - it just widens the digital divide.",
            "quotes": [
                {
                    "text": "Technology should unite us, not divide us along geopolitical lines.",
                    "speaker": "Sen. Maria Chen",
                    "sources": [
                        {
                            "name": "Senate Floor Speech",
                            "url": "https://example.com/senate-speech",
                            "date": "2026-02-28"
                        }
                    ]
                }
            ]
        },
        "right": {
            "take": "Smart move. We can't let adversaries use our own innovations to threaten national security. America first means protecting our tech edge.",
            "quotes": [
                {
                    "text": "Our technological leadership is not negotiable - it's a matter of national security.",
                    "speaker": "Rep. John Crawford",
                    "sources": [
                        {
                            "name": "Press Conference",
                            "url": "https://example.com/press-conf",
                            "date": "2026-02-28"
                        }
                    ]
                }
            ]
        },
        "sources": [
            {"name": "Reuters", "url": "https://example.com/reuters"},
            {"name": "Bloomberg", "url": "https://example.com/bloomberg"}
        ],
        "meta": {
            "trendSource": "google_trends",
            "trendKeyword": "AI chip export",
            "placeholder": True
        }
    },
    {
        "slug": "downtown-housing-project-approved",
        "title": "Downtown housing project approved",
        "topic": "Urban development",
        "publishedAt": "2026-03-01T05:00:00Z",
        "coverImage": "https://picsum.photos/seed/housing/800/640",
        "neutral": {
            "summary": "City council voted 7-4 to approve a new 500-unit housing development in the downtown district, including 100 affordable units."
        },
        "left": {
            "take": "A step forward, but 20% affordable housing is not nearly enough when rent is crushing working families. We need bolder action on the housing crisis.",
            "quotes": [
                {
                    "text": "Housing is a human right, not a luxury for the wealthy.",
                    "speaker": "Councilwoman Sarah Martinez",
                    "sources": [
                        {
                            "name": "City Council Meeting",
                            "url": "https://example.com/council",
                            "date": "2026-02-28"
                        }
                    ]
                }
            ]
        },
        "right": {
            "take": "Great news for property owners and the tax base. The free market works when we get out of the way and let developers build.",
            "quotes": [
                {
                    "text": "This project will create jobs and boost our economy without burdening taxpayers.",
                    "speaker": "Mayor Tom Williams",
                    "sources": [
                        {
                            "name": "Mayor's Statement",
                            "url": "https://example.com/mayor",
                            "date": "2026-02-28"
                        }
                    ]
                }
            ]
        },
        "sources": [
            {"name": "Local News 5", "url": "https://example.com/local5"},
            {"name": "City Times", "url": "https://example.com/citytimes"}
        ],
        "meta": {
            "trendSource": "local_news",
            "trendKeyword": "housing development",
            "placeholder": True
        }
    },
    {
        "slug": "electric-vehicle-sales-surge",
        "title": "Electric vehicle sales surge",
        "topic": "Climate & business",
        "publishedAt": "2026-02-28T20:00:00Z",
        "coverImage": "https://picsum.photos/seed/ev-cars/800/640",
        "neutral": {
            "summary": "Electric vehicle sales jumped 45% in the last quarter, driven by new models and expanded charging infrastructure across major cities."
        },
        "left": {
            "take": "Good progress, but we need stronger emissions standards and more public transit investment. Can't rely on individual car purchases to save the planet.",
            "quotes": [
                {
                    "text": "EVs are part of the solution, but public transportation is the real answer to climate change.",
                    "speaker": "Climate Activist Jamie Lee",
                    "sources": [
                        {
                            "name": "Environmental Summit",
                            "url": "https://example.com/summit",
                            "date": "2026-02-27"
                        }
                    ]
                }
            ]
        },
        "right": {
            "take": "The market is working exactly as it should. Innovation and consumer choice - not government mandates - are driving the transition.",
            "quotes": [
                {
                    "text": "American innovation proves that free markets solve problems better than bureaucrats.",
                    "speaker": "Auto Industry Analyst Mike Stevens",
                    "sources": [
                        {
                            "name": "Industry Report",
                            "url": "https://example.com/report",
                            "date": "2026-02-27"
                        }
                    ]
                }
            ]
        },
        "sources": [
            {"name": "Auto News Daily", "url": "https://example.com/autonews"},
            {"name": "Green Tech Today", "url": "https://example.com/greentech"}
        ],
        "meta": {
            "trendSource": "google_trends",
            "trendKeyword": "electric vehicles",
            "placeholder": True
        }
    },
    {
        "slug": "school-funding-debate-heats-up",
        "title": "School funding debate heats up",
        "topic": "Education policy",
        "publishedAt": "2026-02-28T18:00:00Z",
        "coverImage": "https://picsum.photos/seed/school/800/640",
        "neutral": {
            "summary": "State legislators are divided over a proposal to increase education funding by $2 billion, with debates focusing on property tax implications."
        },
        "left": {
            "take": "Investing in our kids is investing in our future. The wealthy can afford to pay their fair share so every child gets a quality education.",
            "quotes": [
                {
                    "text": "We cannot continue to underfund our schools while giving tax breaks to corporations.",
                    "speaker": "Rep. Lisa Thompson",
                    "sources": [
                        {
                            "name": "State Legislature Hearing",
                            "url": "https://example.com/hearing",
                            "date": "2026-02-27"
                        }
                    ]
                }
            ]
        },
        "right": {
            "take": "More money doesn't automatically mean better schools. We need accountability and school choice, not higher taxes on homeowners.",
            "quotes": [
                {
                    "text": "Parents, not bureaucrats, should decide where their children go to school.",
                    "speaker": "Sen. Robert Hayes",
                    "sources": [
                        {
                            "name": "Town Hall Meeting",
                            "url": "https://example.com/townhall",
                            "date": "2026-02-27"
                        }
                    ]
                }
            ]
        },
        "sources": [
            {"name": "Education Weekly", "url": "https://example.com/edweekly"},
            {"name": "State Capitol News", "url": "https://example.com/capitol"}
        ],
        "meta": {
            "trendSource": "twitter_trending",
            "trendKeyword": "school funding",
            "placeholder": True
        }
    },
    {
        "slug": "border-security-bill-advances",
        "title": "Border security bill advances",
        "topic": "Immigration & security",
        "publishedAt": "2026-02-28T15:00:00Z",
        "coverImage": "https://picsum.photos/seed/border/800/640",
        "neutral": {
            "summary": "A bipartisan border security bill passed the House committee, allocating funds for technology upgrades and additional personnel at border crossings."
        },
        "left": {
            "take": "Security is important, but this bill ignores the humanitarian crisis. We need comprehensive immigration reform, not just more enforcement.",
            "quotes": [
                {
                    "text": "We can secure our borders while treating people with dignity and compassion.",
                    "speaker": "Rep. Carlos Rivera",
                    "sources": [
                        {
                            "name": "Committee Statement",
                            "url": "https://example.com/committee",
                            "date": "2026-02-27"
                        }
                    ]
                }
            ]
        },
        "right": {
            "take": "Finally, some common sense! Secure borders are not optional - every nation has the right to control who enters and enforce its laws.",
            "quotes": [
                {
                    "text": "Border security is national security. This bill is long overdue.",
                    "speaker": "Rep. Jennifer Walsh",
                    "sources": [
                        {
                            "name": "House Floor Speech",
                            "url": "https://example.com/floor-speech",
                            "date": "2026-02-27"
                        }
                    ]
                }
            ]
        },
        "sources": [
            {"name": "Washington Post", "url": "https://example.com/wapo"},
            {"name": "Fox News", "url": "https://example.com/fox"}
        ],
        "meta": {
            "trendSource": "news_api",
            "trendKeyword": "border security",
            "placeholder": True
        }
    }
]

# Write stub stories to disk
for story in stub_stories:
    file_path = stories_dir / f"{story['slug']}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(story, f, indent=2, ensure_ascii=False)
    print(f"✅ Created: {story['slug']}.json")

print(f"\n✨ Generated {len(stub_stories)} stub stories in content/stories/")
