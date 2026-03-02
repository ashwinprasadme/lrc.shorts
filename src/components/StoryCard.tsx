import type { Story } from '../lib/content';
import { formatTimeAgo } from '../lib/content';
import LensSwiper from './LensSwiper';
import SourcesList from './SourcesList';
import './StoryCard.css';

interface StoryCardProps {
  story: Story;
}

export default function StoryCard({ story }: StoryCardProps) {
  return (
    <div className="story-card">
      {/* Header */}
      <div className="story-header">
        <div className="story-meta">
          <span className="story-topic">{story.topic}</span>
          <span className="story-divider">•</span>
          <span className="story-time">{formatTimeAgo(story.publishedAt)}</span>
        </div>
        <h2 className="story-title">{story.title}</h2>
      </div>

      {/* Main content with horizontal swiper */}
      <div className="story-content">
        <LensSwiper story={story} />
        
        {/* Footer with sources */}
        <div className="story-footer">
          <SourcesList sources={story.sources} />
        </div>
      </div>
    </div>
  );
}
