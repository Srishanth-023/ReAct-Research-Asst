import React, { useState } from 'react';
import { Sparkles, Copy, Check } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

export default function FinalAnswer({ answer, onSelectPaper }) {
  const [copied, setCopied] = useState(false);
  if (!answer) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="answer-card">
      <div className="answer-header">
        <div className="answer-header-left">
          <div className="answer-icon"><Sparkles size={13} /></div>
          <div>
            <div className="answer-title">Synthesized Answer &amp; Citations</div>
            <div className="answer-subtitle">Grounded in literature index</div>
          </div>
        </div>
        <button type="button" className="btn btn-ghost" onClick={handleCopy}>
          {copied ? <><Check size={12} style={{ color: 'var(--emerald)' }} /> Copied</> : <><Copy size={12} /> Copy</>}
        </button>
      </div>
      <div className="answer-body">
        <MarkdownRenderer text={answer} onSelectPaper={onSelectPaper} />
      </div>
    </div>
  );
}
