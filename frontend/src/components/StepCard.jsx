import React, { useState } from 'react';
import { Brain, Terminal, FileText, Check, Copy, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

export default function StepCard({ step }) {
  const [isExpanded, setIsExpanded] = useState(false);
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
        <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2, color: 'var(--rose)' }} />
        <div>{content}</div>
      </div>
    );
  }

  if (type === 'thought' || type === 'thought_stream') {
    return (
      <div className="step-card thought anim-fade-in">
        <div className="step-card-header">
          <div className="step-card-header-left">
            <span className="step-icon purple"><Brain size={12} /></span>
            <span className="step-label purple">Thought</span>
          </div>
          <button type="button" className="btn-icon" onClick={handleCopy} title="Copy thought">
            {copied ? <Check size={12} style={{ color: 'var(--emerald)' }} /> : <Copy size={12} />}
          </button>
        </div>
        <div className="step-thought-text"><MarkdownRenderer text={content} /></div>
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
            <span className="step-label blue">Search / Query</span>
            <span className="badge badge-blue">{tool_name}</span>
          </div>
          <div className="step-card-actions">
            <button type="button" className="step-toggle" onClick={() => setIsExpanded(!isExpanded)}>
              {isExpanded ? 'Hide Details' : 'Show Details'}
              {isExpanded ? <ChevronUp size={12} style={{ marginLeft: 2 }} /> : <ChevronDown size={12} style={{ marginLeft: 2 }} />}
            </button>
            <button type="button" className="btn-icon" onClick={handleCopy} title="Copy details">
              {copied ? <Check size={12} style={{ color: 'var(--emerald)' }} /> : <Copy size={12} />}
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
            <span className="step-label green">Source Passage Retrieved</span>
            {tool_name && <span className="step-via-tag">{tool_name}</span>}
          </div>
          <div className="step-card-actions">
            <button type="button" className="step-toggle" onClick={() => setIsExpanded(!isExpanded)}>
              {isExpanded ? 'Hide Passage' : 'View Passage'}
              {isExpanded ? <ChevronUp size={12} style={{ marginLeft: 2 }} /> : <ChevronDown size={12} style={{ marginLeft: 2 }} />}
            </button>
            <button type="button" className="btn-icon" onClick={handleCopy} title="Copy passage">
              {copied ? <Check size={12} style={{ color: 'var(--emerald)' }} /> : <Copy size={12} />}
            </button>
          </div>
        </div>
        {isExpanded && <div className="step-observation-text">{content}</div>}
      </div>
    );
  }

  return null;
}
