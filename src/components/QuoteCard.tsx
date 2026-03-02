import type { Quote } from '../lib/content';
import './QuoteCard.css';

interface QuoteCardProps {
  quote: Quote;
}

export default function QuoteCard({ quote }: QuoteCardProps) {
  return (
    <div className="quote-card">
      <blockquote className="quote-text">
        "{quote.text}"
      </blockquote>
      <div className="quote-attribution">
        <span className="quote-speaker">{quote.speaker}</span>
        {quote.sources && quote.sources.length > 0 && (
          <div className="quote-sources">
            {quote.sources.map((source, idx) => (
              <a
                key={idx}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="quote-source-link"
              >
                {source.name}
                {source.date && (
                  <span className="quote-source-date"> • {new Date(source.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                )}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
