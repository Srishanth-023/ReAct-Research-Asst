import React, { useState } from 'react';
import { Brain, Terminal, FileText, Check, Copy, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';

export default function StepCard({ step }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [copied, setCopied] = useState(false);

  const { type, content, tool_name, tool_args, step: stepNum } = step;

  const handleCopy = () => {
    const text = type === 'action'
      ? `${tool_name}(${JSON.stringify(tool_args, null, 2)})`
      : content || '';
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (type === 'error') {
    return (
      <div className="step-error anim-fade-in">
        <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2, color: 'var(--rose)' }} />
        <div>{content}</div>
      </div>
    );
  }

  if (type === 'thought') {
    return (
      <div className="step-card thought anim-fade-in">
        <div className="step-card-header">
          <div className="step-card-header-left">
            <span className="step-icon purple"><Brain size={12} /></span>
            <span className="step-label purple">Thought {stepNum ? `#${stepNum}` : ''}</span>
          </div>
          <button type="button" className="btn-icon" onClick={handleCopy} title="Copy thought">
            {copied ? <Check size={14} style={{ color: 'var(--emerald)' }} /> : <Copy size={14} />}
          </button>
        </div>
        <div className="step-thought-text">{content}</div>
      </div>
    );
  }

  if (type === 'action') {
    const argsStr = typeof tool_args === 'object' ? JSON.stringify(tool_args, null, 2) : tool_args;
    return (
      <div className="step-card action anim-fade-in">
        <div className="step-card-header">
          <div className="step-card-header-left">
            <span className="step-icon blue"><Terminal size={12} /></span>
            <span className="step-label blue">Action {stepNum ? `#${stepNum}` : ''}</span>
            <span className="badge badge-blue mono" style={{ fontSize: 10, fontFamily: 'var(--font-mono)' }}>{tool_name}</span>
          </div>
          <div className="step-card-actions">
            <button type="button" className="step-toggle" onClick={() => setIsExpanded(!isExpanded)}>
              {isExpanded ? 'Collapse' : 'Expand'}
              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            <button type="button" className="btn-icon" onClick={handleCopy} title="Copy args">
              {copied ? <Check size={14} style={{ color: 'var(--emerald)' }} /> : <Copy size={14} />}
            </button>
          </div>
        </div>
        {isExpanded && <pre className="step-code-block"><code>{argsStr}</code></pre>}
      </div>
    );
  }

  if (type === 'observation') {
    return (
      <div className="step-card observation anim-fade-in">
        <div className="step-card-header">
          <div className="step-card-header-left">
            <span className="step-icon green"><FileText size={12} /></span>
            <span className="step-label green">Observation {stepNum ? `#${stepNum}` : ''}</span>
            {tool_name && <span className="step-via-tag">via {tool_name}</span>}
          </div>
          <div className="step-card-actions">
            <button type="button" className="step-toggle" onClick={() => setIsExpanded(!isExpanded)}>
              {isExpanded ? 'Collapse' : 'Expand'}
              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            <button type="button" className="btn-icon" onClick={handleCopy} title="Copy observation">
              {copied ? <Check size={14} style={{ color: 'var(--emerald)' }} /> : <Copy size={14} />}
            </button>
          </div>
        </div>
        {isExpanded && <div className="step-observation-text">{content}</div>}
      </div>
    );
  }

  return null;
}
