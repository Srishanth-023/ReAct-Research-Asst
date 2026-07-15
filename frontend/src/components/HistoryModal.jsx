import React from 'react';
import { X, History, Clock, CheckCircle2, ChevronRight, Trash2 } from 'lucide-react';

export default function HistoryModal({ isOpen, onClose, queries, onSelectHistoryQuery, isLoading, onClearHistory }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-left">
            <div className="modal-header-icon"><History size={14} /></div>
            <div>
              <div className="modal-title">Query History</div>
            </div>
          </div>
          <button type="button" className="btn-icon" onClick={onClose}><X size={14} /></button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {isLoading ? (
            <div className="panel-empty anim-pulse">Loading past queries...</div>
          ) : !queries || queries.length === 0 ? (
            <div className="panel-empty">
              <History size={24} style={{ opacity: 0.3, marginBottom: 6 }} />
              <div>No past queries.</div>
            </div>
          ) : queries.map((q) => (
            <div
              key={q.id}
              className="history-card"
              onClick={() => { onSelectHistoryQuery(q.id); onClose(); }}
            >
              <div className="history-card-body">
                <div className="history-card-meta">
                  <span className="badge badge-purple" style={{ fontSize: 8 }}>#{q.id}</span>
                  <span className="badge badge-blue" style={{ fontSize: 8, textTransform: 'uppercase' }}>{q.mode}</span>
                  <span style={{ fontSize: 9, color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: 2, marginLeft: 'auto', fontFamily: 'var(--font-mono)' }}>
                    <Clock size={10} />
                    {q.created_at ? new Date(q.created_at).toLocaleDateString() : 'Today'}
                  </span>
                </div>
                <div className="history-card-query">{q.user_query}</div>
                {q.final_answer && (
                  <div className="history-card-answer">
                    <span style={{ color: 'var(--emerald)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 2, marginRight: 3 }}>
                      <CheckCircle2 size={10} /> Answered:
                    </span>
                    {q.final_answer.replace(/###?\s*/g, '').substring(0, 100)}…
                  </div>
                )}
              </div>
              <ChevronRight size={14} className="history-card-arrow" />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          {queries && queries.length > 0 ? (
            <button
              type="button"
              className="btn btn-ghost"
              style={{ color: 'var(--rose)', borderColor: 'rgba(190, 18, 60, 0.2)', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={onClearHistory}
            >
              <Trash2 size={12} /> Clear History
            </button>
          ) : <span />}
          <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
