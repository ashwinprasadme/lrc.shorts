// Type definitions for story content
export interface Source {
  name: string;
  url: string;
  date?: string;
}

export interface Quote {
  text: string;
  speaker: string;
  sources: Source[];
}

export interface Lens {
  take: string;
  quotes: Quote[];
}

export interface Neutral {
  summary: string;
}

export interface Story {
  slug: string;
  title: string;
  topic: string;
  publishedAt: string;
  neutral: Neutral;
  left: Lens;
  right: Lens;
  sources: Source[];
  coverImage?: string; // Optional cover image URL
  meta?: {
    trendSource?: string;
    trendKeyword?: string;
    placeholder?: boolean;
  };
}

/**
 * Load all stories from the content directory
 */
export async function loadStories(): Promise<Story[]> {
  // In Astro, we can use import.meta.glob to load all JSON files
  const storyFiles = import.meta.glob<{ default: Story }>(
    '../../content/stories/*.json',
    { eager: true }
  );

  const stories: Story[] = [];

  for (const path in storyFiles) {
    const story = storyFiles[path].default;
    stories.push(story);
  }

  // Sort by publishedAt (descending - newest first)
  stories.sort((a, b) => {
    return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
  });

  return stories;
}

/**
 * Get a single story by slug
 */
export async function getStory(slug: string): Promise<Story | undefined> {
  const stories = await loadStories();
  return stories.find((s) => s.slug === slug);
}

/**
 * Get the index of a story in the sorted list
 */
export async function getStoryIndex(slug: string): Promise<number> {
  const stories = await loadStories();
  return stories.findIndex((s) => s.slug === slug);
}

/**
 * Format a date for display (e.g., "2 hours ago", "3 days ago")
 */
export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  // Fallback to formatted date
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric' 
  });
}
