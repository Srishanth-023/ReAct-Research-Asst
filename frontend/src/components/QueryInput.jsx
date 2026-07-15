import React, { useState } from 'react';
import { Send, Sparkles, Lightbulb, PlayCircle, Loader2 } from 'lucide-react';

const SAMPLE_QUERIES = [
  { title: 'ReAct Methodology & HotpotQA Boost', query: 'What core methodology does the ReAct paper (2210.03629) propose, how does it interleave reasoning and acting, and what is its Exact Match performance improvement over standard CoT on HotpotQA? Calculate the relative percentage boost.' },
  { title: 'Limitations & Failure Modes', query: 'Fetch the ReAct paper (2210.03629) and retrieve its discussion section. What are the primary failure modes or limitations documented for ReAct when external retrieval returns noisy or missing passages?' },
  { title: 'Cross-Paper Citation Synthesis', query: 'Search arXiv for recent papers on agentic tool use and Chain of Thought reasoning. Ingest the top 2 candidate papers and synthesize what common architectural challenges they highlight regarding hallucination vs external grounding.' },
  { title: 'Token Efficiency & Cost Tradeoffs', query: 'According to Yao et al. (2210.03629), how many actions and tokens on average does ReAct consume compared to Chain of Thought on ALFWorld, and what does the calculation show about its efficiency vs accuracy tradeoff?' },
];

export default function QueryInput({ onSendQuery, isStreaming, mode }) {
  const [queryText, setQueryText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!queryText.trim() || isStreaming) return;
    onSendQuery(queryText);
  };

  return (
    <div className="query-section">
      {/* Samples */}
      <div className="query-samples-label">
        <Lightbulb size={14} style={{ color: 'var(--amber)' }} />
        <span>Suggested Research Queries</span>
      </div>
      <div className="query-samples-grid">
        {SAMPLE_QUERIES.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setQueryText(s.query)}
            disabled={isStreaming}
            className="query-sample-card"
          >
            <div className="query-sample-title">
              <PlayCircle size={13} style={{ color: 'var(--purple)', flexShrink: 0 }} />
              {s.title}
            </div>
            <div className="query-sample-text">{s.query}</div>
          </button>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="query-input-card">
        <textarea
          className="query-textarea"
          rows={3}
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e); }}
          placeholder="Ask an academic research question (e.g., 'What methodology does ReAct use and what is its EM accuracy on HotpotQA?')..."
          disabled={isStreaming}
        />
        <div className="query-footer">
          <div className="query-footer-left">
            <span className="query-mode-pill">
              <Sparkles size={10} style={{ color: 'var(--purple)' }} />
              {mode}
            </span>
            <span>Press <kbd>Ctrl+Enter</kbd> to submit</span>
          </div>
          <button type="submit" disabled={!queryText.trim() || isStreaming} className="btn btn-primary">
            {isStreaming ? (
              <><Loader2 size={14} className="anim-spin" /> Reasoning...</>
            ) : (
              <>Run Query <Send size={14} /></>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
