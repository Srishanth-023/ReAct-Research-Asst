import React from 'react';
import { Sparkles, History, Database, Layers, CheckCircle2 } from 'lucide-react';

const MODES = [
  { id: 'react',    label: 'ReAct',     badge: 'Default',   desc: 'Thought → Action → Observation sequence loops to search literature and ground claims.' },
  { id: 'cot',      label: 'CoT-only',  badge: 'Ablation',    desc: 'Reasoning chain without external searches or tools.' },
  { id: 'act',      label: 'Act-only',  badge: 'Ablation',    desc: 'Tool execution steps without internal reasoning thought processes.' },
  { id: 'standard', label: 'Standard',  badge: 'Direct',      desc: 'Direct response generation.' },
];

export default function Header({ mode, setMode, onOpenHistory, onToggleSources, isSourcesOpen, papersCount }) {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-brand">
          <div className="header-logo">
            <Sparkles size={13} />
          </div>
          <span className="header-title">Research Assistant</span>
        </div>

        <div className="mode-switcher">
          <span className="mode-label">
            <Layers size={10} style={{ color: 'var(--purple)' }} />
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
              {mode === m.id && <CheckCircle2 size={10} style={{ color: 'var(--purple)' }} />}
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
            <History size={13} style={{ color: 'var(--purple)' }} />
            History
          </button>
          <button
            type="button"
            onClick={onToggleSources}
            className={`btn btn-ghost ${isSourcesOpen ? 'active' : ''}`}
          >
            <Database size={13} style={{ color: 'var(--blue)' }} />
            Index
            <span className="badge badge-purple" style={{ marginLeft: 2, fontSize: 9 }}>
              {papersCount || 0}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}
