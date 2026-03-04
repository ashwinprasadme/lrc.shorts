import type { Quote } from '../lib/content';
import './QuoteCard.css';

interface QuoteCardProps {
  quote: Quote;
}

function getFaviconUrl(url: string): string {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return '';
  }
}

export default function QuoteCard({ quote }: QuoteCardProps) {
  const displaySources = quote.sources?.slice(0, 2) || [];
  
  return (
    <div className="quote-card">
      <div className="quote-main">
        <blockquote className="quote-text">
          {quote.text}
        </blockquote>
        <div className="quote-footer">
          <span className="quote-speaker">{quote.speaker}</span>
          {displaySources.length > 0 && (
            <div className="quote-sources">
              {displaySources.map((source, idx) => (
                <a
                  key={idx}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="quote-source-link"
                  title={source.name}
                >
                  <img 
                    src={getFaviconUrl(source.url)} 
                    alt={source.name}
                    className="quote-source-favicon"
                  />
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
