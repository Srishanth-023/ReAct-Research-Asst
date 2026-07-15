import React, { useRef, useEffect } from 'react';
import StepCard from './StepCard';
import FinalAnswer from './FinalAnswer';
import { Activity, Sparkles, Loader2 } from 'lucide-react';

export default function TraceView({ steps, finalAnswer, isStreaming, statusMessage, onSelectPaper }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [steps, finalAnswer, statusMessage]);

  if (steps.length === 0 && !isStreaming && !finalAnswer) return null;

  return (
    <div className="trace-section">
      <div className="trace-header">
        <div className="trace-header-left">
          <Activity size={14} style={{ color: 'var(--purple)' }} />
          <span className="trace-title">Reasoning &amp; Search History</span>
          {isStreaming && (
            <span className="trace-live-badge">
              <Loader2 size={10} className="anim-spin" />
              Active
            </span>
          )}
        </div>
        <span className="trace-count">{steps.length} {steps.length === 1 ? 'Entry' : 'Entries'}</span>
      </div>

      {statusMessage && isStreaming && (
        <div className="trace-status anim-fade-in">
          <Sparkles size={12} className="anim-bounce" style={{ color: 'var(--purple)', marginRight: 2 }} />
          <span>{statusMessage}</span>
        </div>
      )}

      <div>
        {steps.map((step, i) => (
          <StepCard key={i} step={step} />
        ))}
      </div>

      {finalAnswer && <FinalAnswer answer={finalAnswer} onSelectPaper={onSelectPaper} />}

      <div ref={scrollRef} style={{ height: 24 }} />
    </div>
  );
}
