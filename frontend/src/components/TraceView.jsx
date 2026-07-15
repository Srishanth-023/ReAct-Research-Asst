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
          <Activity size={16} style={{ color: 'var(--purple)' }} />
          <span className="trace-title">Reasoning &amp; Acting Trajectory</span>
          {isStreaming && (
            <span className="trace-live-badge">
              <Loader2 size={10} className="anim-spin" />
              Live
            </span>
          )}
        </div>
        <span className="trace-count">{steps.length} {steps.length === 1 ? 'Step' : 'Steps'}</span>
      </div>

      {statusMessage && isStreaming && (
        <div className="trace-status anim-fade-in">
          <Sparkles size={14} className="anim-bounce" style={{ color: 'var(--purple)' }} />
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
