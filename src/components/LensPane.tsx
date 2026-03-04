import type { Lens, Neutral } from '../lib/content';
import QuoteCard from './QuoteCard';
import './LensPane.css';

interface LensPaneProps {
  type: 'left' | 'neutral' | 'right';
  content: Lens | Neutral;
  coverImage?: string;
}

export default function LensPane({ type, content, coverImage }: LensPaneProps) {
  const typeColors = {
    left: 'var(--color-left)',
    neutral: 'var(--color-centre)',
    right: 'var(--color-right)',
  };

  const typeLabels = {
    left: 'Left',
    neutral: 'Centre',
    right: 'Right',
  };

  return (
    <div 
      className={`lens-pane lens-pane--${type}`}
      style={{ '--lens-color': typeColors[type] } as React.CSSProperties}
    >
      {/* Image sticks to top */}
      {type === 'neutral' && coverImage && (
        <div className="lens-centre-image">
          <img src={coverImage} alt="Story cover" />
        </div>
      )}

      <div className="lens-content">
        {'summary' in content ? (
          // Centre view - compact layout with image and summary
          <div className="lens-centre">
            <div className="lens-centre-text">
              <p className="lens-summary">{content.summary}</p>
            </div>
          </div>
        ) : (
          // Left or Right view
          <>
            <h3 className="lens-perspective-header">{typeLabels[type]} Perspective</h3>
            {content.quotes && content.quotes.length > 0 && (
              <div className="lens-quotes">
                {content.quotes.map((quote, idx) => (
                  <QuoteCard key={idx} quote={quote} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
