import React, { useState } from 'react';
import { Sparkles, Copy, Check, ExternalLink, Award } from 'lucide-react';

export default function FinalAnswer({ answer, onSelectPaper }) {
  const [copied, setCopied] = useState(false);
  if (!answer) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const highlightCitations = (str) => {
    const regex = /\(([`'""]?([a-zA-Z0-9.\-\/]+)[`'""]?\s*,\s*page\s*(\d+))\)/gi;
    const parts = [];
    let lastIdx = 0;
    let match;
    while ((match = regex.exec(str)) !== null) {
      if (match.index > lastIdx) parts.push(str.substring(lastIdx, match.index));
      const paperId = match[2];
      const pageNum = match[3];
      parts.push(
        <button
          key={`${match.index}-${paperId}`}
          type="button"
          onClick={() => onSelectPaper && onSelectPaper(paperId)}
          className="citation-pill"
          title={`Inspect paper '${paperId}' in Sources panel`}
        >
          <span>{paperId} (p.{pageNum})</span>
          <ExternalLink size={10} />
        </button>
      );
      lastIdx = regex.lastIndex;
    }
    if (lastIdx < str.length) parts.push(str.substring(lastIdx));
    return parts.length > 0 ? parts : str;
  };

  const renderAnswer = (text) => {
    return text.split('\n').map((line, i) => {
      if (line.startsWith('### ')) return (
        <h3 key={i} className="answer-body">
          <Award size={14} style={{ color: 'var(--purple)', flexShrink: 0 }} />
          {line.replace('### ', '')}
        </h3>
      );
      if (line.startsWith('## ')) return <h2 key={i}>{line.replace('## ', '')}</h2>;
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return <li key={i}>{highlightCitations(line.replace(/^[-*]\s+/, ''))}</li>;
      }
      if (!line.trim()) return <div key={i} style={{ height: 8 }} />;
      return <p key={i}>{highlightCitations(line)}</p>;
    });
  };

  return (
    <div className="answer-card">
      <div className="answer-header">
        <div className="answer-header-left">
          <div className="answer-icon"><Sparkles size={14} /></div>
          <div>
            <div className="answer-title">Synthesized Final Answer &amp; Citations</div>
            <div className="answer-subtitle">Verified &amp; Grounded over Full-Text Scientific Prose</div>
          </div>
        </div>
        <button type="button" className="btn btn-ghost" onClick={handleCopy}>
          {copied ? <><Check size={14} style={{ color: 'var(--emerald)' }} /> Copied</> : <><Copy size={14} /> Copy</>}
        </button>
      </div>
      <div className="answer-body">{renderAnswer(answer)}</div>
    </div>
  );
}
