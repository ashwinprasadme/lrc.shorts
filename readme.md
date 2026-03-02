# LensReels — Left / Centre / Right News Perspectives

A mobile-first, ultra-fast static site where users browse trending news like Instagram Reels:
- **Swipe up/down** to move between stories
- **Swipe left/right** within a story to switch **Left ↔ Centre ↔ Right** perspectives
- Each perspective is **concise**, **casual but civil**
- Left/Right views include **quotes** from political figures + **source links**
- Centre view shows neutral summary with cover image

Built with **Astro** + **React** + **Swiper.js** for a snappy, app-like experience.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- Python 3.x (for helper scripts)

### Installation

```bash
# Install dependencies
npm install

# Generate sample story data
npm run make:stubs

# Start dev server
npm run dev
```

The app will be available at **http://localhost:4321**

To expose to your local network (for mobile testing):
```bash
# Server runs with --host flag automatically
# Access via http://YOUR_LOCAL_IP:4321
```

### Build for Production

```bash
npm run build
npm run preview
```

---

## 📱 Features

### Current Implementation (Phase 1 Complete)

✅ **Vertical Story Feed**
- Swipe up/down to navigate between news stories
- Smooth Reels-like transitions
- URL updates as you swipe

✅ **Horizontal Perspective Switcher**
- Swipe left/right for different viewpoints
- Left (Blue) - progressive perspective with quotes
- Centre (Purple) - neutral summary with cover image
- Right (Red) - conservative perspective with quotes

✅ **Clean, Professional Design**
- Light theme optimized for readability
- Compact layouts that maximize content
- Round favicon indicators for sources
- Sticky headers with perspective badges

✅ **Deep Linking**
- Each story has a shareable URL: `/story/<slug>/`
- Direct links open the feed at the specific story

✅ **Mobile-First**
- Safe area support for notched devices
- Optimized touch interactions
- No conflicts between horizontal/vertical gestures

---

## 🗂️ Project Structure

```
.
├── src/
│   ├── pages/
│   │   ├── index.astro              # Main feed
│   │   └── story/[slug].astro       # Deep-link route
│   ├── components/
│   │   ├── ReelFeed.tsx             # Vertical swiper (stories)
│   │   ├── StoryCard.tsx            # Story wrapper (header/footer)
│   │   ├── LensSwiper.tsx           # Horizontal swiper (perspectives)
│   │   ├── LensPane.tsx             # Individual perspective view
│   │   ├── QuoteCard.tsx            # Quote display with sources
│   │   └── SourcesList.tsx          # Favicon-based source links
│   ├── lib/
│   │   └── content.ts               # Story loader & types
│   └── styles/
│       └── global.css               # App-wide styles
│
├── content/
│   └── stories/
│       └── *.json                   # Story data files
│
├── scripts/
│   ├── make-stubs.py                # Generate test stories
│   └── validate-stories.py          # Validate story JSON
│
├── public/                          # Static assets
├── package.json
├── astro.config.mjs
└── tsconfig.json
```

---

## 📝 Content Format

Each story is a JSON file in `content/stories/<slug>.json`:

```json
{
  "slug": "story-slug-here",
  "title": "Story Title",
  "topic": "Category name",
  "publishedAt": "2026-03-01T06:30:00Z",
  "coverImage": "https://example.com/image.jpg",
  
  "neutral": {
    "summary": "Neutral description of what happened (1-2 sentences)."
  },
  
  "left": {
    "take": "Progressive perspective (casual but civil).",
    "quotes": [
      {
        "text": "Quote from political figure.",
        "speaker": "Person Name",
        "sources": [
          {
            "name": "Source Name",
            "url": "https://example.com/article",
            "date": "2026-02-28"
          }
        ]
      }
    ]
  },
  
  "right": {
    "take": "Conservative perspective (casual but civil).",
    "quotes": [
      {
        "text": "Quote from political figure.",
        "speaker": "Person Name",
        "sources": [
          {
            "name": "Source Name",
            "url": "https://example.com/article",
            "date": "2026-02-28"
          }
        ]
      }
    ]
  },
  
  "sources": [
    { "name": "News Outlet", "url": "https://example.com" }
  ],
  
  "meta": {
    "trendSource": "google_trends",
    "trendKeyword": "keyword",
    "placeholder": true
  }
}
```

### Content Guidelines

- **Slug**: Lowercase, URL-safe, unique identifier
- **Title**: Short headline (max 60 chars recommended)
- **Cover Image**: 5:4 aspect ratio (e.g., 800x640px)
- **Centre Summary**: Neutral, factual, 1-2 sentences
- **Left/Right Takes**: Concise perspectives, 1-3 sentences
- **Quotes**: Short, impactful, always sourced
- **Sources**: Valid URLs for favicon extraction

---

## 🛠️ Development Scripts

```bash
# Development
npm run dev              # Start dev server with network access
npm run build            # Build for production
npm run preview          # Preview production build

# Content Management
npm run make:stubs       # Generate 5 sample stories
npm run validate:stories # Validate all story JSON files
```

---

## 🎨 Design System

### Colors

```css
--color-bg: #ffffff           /* Background */
--color-text: #1a1a1a         /* Primary text */
--color-text-muted: #666666   /* Secondary text */
--color-left: #2563eb         /* Blue - Progressive */
--color-centre: #9333ea       /* Purple - Neutral */
--color-right: #dc2626        /* Red - Conservative */
--color-border: #e5e5e5       /* Borders */
```

### Spacing

Uses a consistent scale: `xs`, `sm`, `md`, `lg`, `xl` (0.5rem - 2rem)

### Typography

System fonts for performance:
- Base: 16px (1rem)
- Large text: 18px (1.125rem)
- Headlines: 24px-32px (1.5rem-2rem)

---

## 🚢 Deployment

Designed for **Vercel** static deployment:

1. Connect your GitHub repo to Vercel
2. Framework preset: **Astro**
3. Build command: `npm run build`
4. Output directory: `dist`
5. Install command: `npm install`

### Content Updates

Add/update stories by:
1. Creating/editing JSON files in `content/stories/`
2. Run `npm run validate:stories` to check
3. Commit and push to trigger rebuild

---

## 🔮 Roadmap

### Phase 2 - Content Enhancement
- [ ] Real content pipeline integration
- [ ] Image optimization
- [ ] Story archiving (limit to latest N stories)

### Phase 3 - PWA Features
- [ ] Web manifest
- [ ] Service worker for offline support
- [ ] Add to home screen prompt
- [ ] Share API integration

### Phase 4 - Engagement
- [ ] Story reactions/feedback
- [ ] Topic filtering
- [ ] Search functionality
- [ ] Analytics integration

---

## 📄 License

[Your license here]

## 🤝 Contributing

Contributions welcome! Please ensure all story JSON passes validation before submitting PRs.

---

## 🐛 Troubleshooting

**Swipes not working?**
- Ensure you're swiping in the correct direction (vertical = stories, horizontal = perspectives)
- Check browser console for errors

**Images not loading?**
- Verify image URLs are accessible
- Check CORS headers if serving from external domains

**Build fails?**
- Run `npm run validate:stories` to check for content errors
- Ensure all required fields are present in story JSON

**Dev server not accessible on phone?**
- Check firewall settings allow port 4321
- Ensure devices are on the same network
- Use your computer's local IP (not localhost)
