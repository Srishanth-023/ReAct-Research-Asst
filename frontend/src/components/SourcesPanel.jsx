import React, { useState } from 'react';
import { X, ExternalLink, FileText, CheckCircle, Search, Layers } from 'lucide-react';

export default function SourcesPanel({ isOpen, onClose, papers, onSelectPaper, selectedPaperChunks, isLoadingChunks }) {
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
            <Layers size={16} style={{ color: 'var(--purple)' }} />
            <div>
              <div className="panel-header-title">Sources &amp; RAG Index</div>
              <div className="panel-header-sub">ChromaDB prose chunks (all-MiniLM-L6-v2)</div>
            </div>
          </div>
          <button type="button" className="btn-icon" onClick={onClose}><X size={16} /></button>
        </div>

        {/* Tabs */}
        <div className="panel-tabs">
          <button
            type="button"
            className={`panel-tab ${activeTab === 'papers' ? 'active' : ''}`}
            onClick={() => setActiveTab('papers')}
          >Papers ({papers?.length || 0})</button>
          <button
            type="button"
            className={`panel-tab ${activeTab === 'chunks' ? 'active' : ''}`}
            onClick={() => setActiveTab('chunks')}
          >Chunks ({selectedPaperChunks ? selectedPaperChunks.length : 0})</button>
        </div>

        {/* Search */}
        {activeTab === 'papers' && (
          <div className="panel-search">
            <div className="panel-search-wrap">
              <Search size={13} className="panel-search-icon" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by title or ID..."
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
                <FileText size={28} style={{ opacity: 0.3, marginBottom: 8 }} />
                <div>No indexed papers yet.</div>
                <p>When fetch_paper runs, PDFs are chunked and listed here.</p>
              </div>
            ) : filtered.map((p) => (
              <div
                key={p.id}
                className={`paper-card ${selectedPaperChunks?.paper_id === p.id ? 'selected' : ''}`}
                onClick={() => { onSelectPaper(p.id); setActiveTab('chunks'); }}
              >
                <div className="paper-card-top">
                  <div className="paper-title">{p.title || p.id}</div>
                  <span className="badge badge-purple" style={{ fontSize: 9, fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
                    {p.chunk_count || 0} Chunks
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
                        arXiv <ExternalLink size={10} style={{ display: 'inline' }} />
                      </a>
                    )}
                    {p.pdf_path && (
                      <span style={{ color: 'var(--emerald)', display: 'flex', alignItems: 'center', gap: 3 }}>
                        <CheckCircle size={11} /> Cached
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}

          {activeTab === 'chunks' && (
            isLoadingChunks ? (
              <div className="panel-empty anim-pulse">Loading prose passages from ChromaDB...</div>
            ) : !selectedPaperChunks || selectedPaperChunks.length === 0 ? (
              <div className="panel-empty">Select a paper from the Papers tab to inspect its chunks.</div>
            ) : selectedPaperChunks.map((c, i) => (
              <div key={i} className="chunk-card">
                <div className="chunk-card-header">
                  <span className="chunk-section">{c.metadata.section_guess || 'Body Text'}</span>
                  <span className="chunk-page">Page {c.metadata.page_number || '?'}</span>
                </div>
                <div className="chunk-text">"{c.text}"</div>
              </div>
            ))
          )}
        </div>

        <div className="panel-footer">ChromaDB · all-MiniLM-L6-v2</div>
      </div>
    </>
  );
}
