import React from 'react';
import { X, History, Clock, CheckCircle2, ChevronRight } from 'lucide-react';

export default function HistoryModal({ isOpen, onClose, queries, onSelectHistoryQuery, isLoading }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-left">
            <div className="modal-header-icon"><History size={14} /></div>
            <div>
              <div className="modal-title">Query Trajectory History</div>
              <div className="modal-subtitle">Stored in react_research.db (SQLite)</div>
            </div>
          </div>
          <button type="button" className="btn-icon" onClick={onClose}><X size={16} /></button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {isLoading ? (
            <div className="panel-empty anim-pulse">Loading saved trajectories...</div>
          ) : !queries || queries.length === 0 ? (
            <div className="panel-empty">
              <History size={28} style={{ opacity: 0.3, marginBottom: 8 }} />
              <div>No past research queries yet.</div>
              <p>Run your first ReAct query to start recording traces.</p>
            </div>
          ) : queries.map((q) => (
            <div
              key={q.id}
              className="history-card"
              onClick={() => { onSelectHistoryQuery(q.id); onClose(); }}
            >
              <div className="history-card-body">
                <div className="history-card-meta">
                  <span className="badge badge-purple" style={{ fontSize: 9, fontFamily: 'var(--font-mono)' }}>#{q.id}</span>
                  <span className="badge badge-blue" style={{ fontSize: 9, textTransform: 'uppercase', fontFamily: 'var(--font-mono)' }}>{q.mode}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: 3, marginLeft: 'auto', fontFamily: 'var(--font-mono)' }}>
                    <Clock size={11} />
                    {q.created_at ? new Date(q.created_at).toLocaleString() : 'Just now'}
                  </span>
                </div>
                <div className="history-card-query">{q.user_query}</div>
                {q.final_answer && (
                  <div className="history-card-answer">
                    <span style={{ color: 'var(--emerald)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 3, marginRight: 4 }}>
                      <CheckCircle2 size={11} /> Answered:
                    </span>
                    {q.final_answer.replace(/###?\s*/g, '').substring(0, 120)}…
                  </div>
                )}
              </div>
              <ChevronRight size={16} className="history-card-arrow" />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <span>SQLAlchemy + SQLite</span>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
