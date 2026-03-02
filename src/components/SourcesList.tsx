import type { Source } from '../lib/content';
import './SourcesList.css';

interface SourcesListProps {
  sources: Source[];
}

function getFaviconUrl(url: string): string {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  } catch {
    return '';
  }
}

export default function SourcesList({ sources }: SourcesListProps) {
  if (!sources || sources.length === 0) {
    return null;
  }

  return (
    <div className="sources-list">
      <h4 className="sources-title">Sources</h4>
      <ul className="sources-items">
        {sources.map((source, idx) => (
          <li key={idx} className="source-item">
            <a 
              href={source.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="source-link"
              title={source.name}
            >
              <img 
                src={getFaviconUrl(source.url)} 
                alt={source.name}
                className="source-favicon"
              />
              <span className="source-icon">↗</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
