import React, { useState } from 'react';
import { Zap, Copy, Check } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

export default function SuperSummary({ summary }) {
  const [copied, setCopied] = useState(false);

  if (!summary) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="super-summary-card anim-fade-in">
      <div className="super-summary-header">
        <div className="super-summary-header-left">
          <div className="super-summary-icon">
            <Zap size={14} />
          </div>
          <div>
            <div className="super-summary-title">Super Summary</div>
            <div className="super-summary-subtitle">Synthesized from all research findings</div>
          </div>
        </div>
        <button type="button" className="btn btn-ghost" onClick={handleCopy}>
          {copied
            ? <><Check size={12} style={{ color: 'var(--emerald)' }} /> Copied</>
            : <><Copy size={12} /> Copy</>
          }
        </button>
      </div>
      <div className="super-summary-body">
        <MarkdownRenderer text={summary} />
      </div>
    </div>
  );
}
