import React, { useState } from 'react';
import { Send, Sparkles, Loader2 } from 'lucide-react';

export default function QueryInput({ onSendQuery, isStreaming, mode }) {
  const [queryText, setQueryText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!queryText.trim() || isStreaming) return;
    onSendQuery(queryText);
    setQueryText('');
  };

  return (
    <div className="query-section">
      <form onSubmit={handleSubmit} className="query-input-card">
        <textarea
          className="query-textarea"
          rows={3}
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e); }}
          placeholder="Enter a research topic, question, or arXiv ID..."
          disabled={isStreaming}
        />
        <div className="query-footer">
          <div className="query-footer-left">
            <span className="query-mode-pill">
              <Sparkles size={9} style={{ color: 'var(--purple)' }} />
              {mode}
            </span>
          </div>
          <button type="submit" disabled={!queryText.trim() || isStreaming} className="btn btn-primary">
            {isStreaming ? (
              <><Loader2 size={12} className="anim-spin" /> Running...</>
            ) : (
              <>Search &amp; Analyze <Send size={12} /></>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
