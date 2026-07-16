import React, { useState } from 'react';
import { X, ExternalLink, FileText, CheckCircle, Search, Layers, Trash2 } from 'lucide-react';

export default function SourcesPanel({ isOpen, onClose, papers, onSelectPaper, selectedPaperChunks, isLoadingChunks, onClearPapers }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('papers');

  if (!isOpen) return null;

  const filtered = (papers || []).filter(p =>
    (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.id || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      <div className="sources-overlay" onClick={onClose} />
      <div className="sources-panel">
        {/* Header */}
        <div className="panel-header">
          <div className="panel-header-left">
            <Layers size={14} style={{ color: 'var(--purple)' }} />
            <div>
              <div className="panel-header-title">Literature Index</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {papers && papers.length > 0 && (
              <button
                type="button"
                className="btn-icon"
                title="Clear Index"
                style={{ color: 'var(--rose)' }}
                onClick={onClearPapers}
              >
                <Trash2 size={13} />
              </button>
            )}
            <button type="button" className="btn-icon" onClick={onClose}><X size={14} /></button>
          </div>
        </div>

        {/* Tabs */}
        <div className="panel-tabs">
          <button
            type="button"
            className={`panel-tab ${activeTab === 'papers' ? 'active' : ''}`}
            onClick={() => setActiveTab('papers')}
          >Documents ({papers?.length || 0})</button>
          <button
            type="button"
            className={`panel-tab ${activeTab === 'chunks' ? 'active' : ''}`}
            onClick={() => setActiveTab('chunks')}
          >Passages ({selectedPaperChunks ? selectedPaperChunks.length : 0})</button>
        </div>

        {/* Search */}
        {activeTab === 'papers' && (
          <div className="panel-search">
            <div className="panel-search-wrap">
              <Search size={12} className="panel-search-icon" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search index..."
                className="panel-search-input"
              />
            </div>
          </div>
        )}

        {/* Body */}
        <div className="panel-body">
          {activeTab === 'papers' && (
            filtered.length === 0 ? (
              <div className="panel-empty">
                <FileText size={24} style={{ opacity: 0.3, marginBottom: 6 }} />
                <div>Index is currently empty.</div>
              </div>
            ) : filtered.map((p) => (
              <div
                key={p.id}
                className={`paper-card ${selectedPaperChunks?.paper_id === p.id ? 'selected' : ''}`}
                onClick={() => { onSelectPaper(p.id); setActiveTab('chunks'); }}
              >
                <div className="paper-card-top">
                  <div className="paper-title">{p.title || p.id}</div>
                  <span className="badge badge-purple" style={{ fontSize: 9, flexShrink: 0 }}>
                    {p.chunk_count || 0} pgs
                  </span>
                </div>
                <div className="paper-authors">
                  {p.authors?.length > 0 ? p.authors.join(', ') : 'Authors Unknown'} ({p.year || 'n.d.'})
                </div>
                <div className="paper-card-bottom">
                  <span className="paper-id-tag">{p.id}</span>
                  <div className="paper-links" onClick={(e) => e.stopPropagation()}>
                    {p.arxiv_id && (
                      <a href={`https://arxiv.org/abs/${p.arxiv_id}`} target="_blank" rel="noopener noreferrer">
                        Link <ExternalLink size={8} style={{ display: 'inline', marginLeft: 1 }} />
                      </a>
                    )}
                    {p.pdf_path && (
                      <span style={{ color: 'var(--emerald)', display: 'flex', alignItems: 'center', gap: 2 }}>
                        <CheckCircle size={10} /> Indexed
                        <a href={`http://localhost:8000/api/papers/pdf/${p.pdf_path.split(/[\\\\/]/).pop()}`} target="_blank" rel="noopener noreferrer" style={{ display: 'flex', alignItems: 'center', gap: 2, marginLeft: '8px', color: 'var(--purple)', textDecoration: 'none' }}>
                          PDF <ExternalLink size={8} />
                        </a>
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}

          {activeTab === 'chunks' && (
            isLoadingChunks ? (
              <div className="panel-empty anim-pulse">Retrieving passages...</div>
            ) : !selectedPaperChunks || selectedPaperChunks.length === 0 ? (
              <div className="panel-empty">Select a document to view indexed passages.</div>
            ) : selectedPaperChunks.map((c, i) => (
              <div key={i} className="chunk-card">
                <div className="chunk-card-header">
                  <span className="chunk-section">{c.metadata.section_guess || 'Text Content'}</span>
                  <span className="chunk-page">Page {c.metadata.page_number || '?'}</span>
                </div>
                <div className="chunk-text">"{c.text}"</div>
              </div>
            ))
          )}
        </div>

        <div className="panel-footer">Local Semantic Database</div>
      </div>
    </>
  );
}
