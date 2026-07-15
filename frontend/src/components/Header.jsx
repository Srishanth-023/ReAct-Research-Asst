import React from 'react';
import { Sparkles, History, Database, Layers, CheckCircle2 } from 'lucide-react';

const MODES = [
  { id: 'react',    label: 'ReAct',     badge: 'Synergistic', desc: 'Yao et al. (2023) full loop: alternates reasoning (Thought) and external actions (Action → Observation) for high accuracy and grounded citations.' },
  { id: 'cot',      label: 'CoT-only',  badge: 'Ablation',    desc: 'Chain-of-Thought reasoning ONLY without external tool actions. Demonstrates vulnerability to numerical or factual hallucinations.' },
  { id: 'act',      label: 'Act-only',  badge: 'Ablation',    desc: 'Executes external actions directly without intermediate reasoning traces (Thought). Leads to unguided search.' },
  { id: 'standard', label: 'Standard',  badge: 'Zero-shot',   desc: 'Direct zero-shot parametric generation without tools or Chain-of-Thought reasoning steps.' },
];

export default function Header({ mode, setMode, onOpenHistory, onToggleSources, isSourcesOpen, papersCount }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-brand">
          <div className="header-logo">
            <Sparkles size={14} />
          </div>
          <span className="header-title">ReAct Research Assistant</span>
          <span className="header-badge">ICLR 2023</span>
        </div>

        <div className="mode-switcher">
          <span className="mode-label">
            <Layers size={12} style={{ color: 'var(--purple)' }} />
            Mode
          </span>
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setMode(m.id)}
              className={`mode-btn ${mode === m.id ? 'active' : ''}`}
            >
              {m.label}
              {mode === m.id && <CheckCircle2 size={12} style={{ color: 'var(--purple)' }} />}
              <div className="mode-tooltip">
                <div className="mode-tooltip-title">
                  {m.label}
                  <span className="mode-tooltip-badge">{m.badge}</span>
                </div>
                <div className="mode-tooltip-desc">{m.desc}</div>
              </div>
            </button>
          ))}
        </div>

        <div className="header-actions">
          <button type="button" onClick={onOpenHistory} className="btn btn-ghost">
            <History size={14} style={{ color: 'var(--purple)' }} />
            History
          </button>
          <button
            type="button"
            onClick={onToggleSources}
            className={`btn btn-ghost ${isSourcesOpen ? 'active' : ''}`}
          >
            <Database size={14} style={{ color: 'var(--blue)' }} />
            Sources
            <span className="badge badge-purple" style={{ marginLeft: 2, fontSize: 10, fontFamily: 'var(--font-mono)' }}>
              {papersCount || 0}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
