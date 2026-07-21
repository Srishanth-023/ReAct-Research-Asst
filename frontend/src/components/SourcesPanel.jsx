import React, { useState } from 'react';
import { X, ExternalLink, FileText, CheckCircle, Search, Layers, Trash2, BookOpen } from 'lucide-react';

export default function SourcesPanel({ isOpen, onClose, papers, onSelectPaper, selectedPaperChunks, isLoadingChunks, onClearPapers }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('papers');

  if (!isOpen) return null;

  const filtered = (papers || []).filter(p =>
    (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.source_query || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Build arXiv link from paper ID
  const getArxivLink = (paper) => {
    const id = paper.arxiv_id || paper.id || '';
    // Check if ID looks like an arXiv ID (e.g. 2210.03629 or cs/0001234)
    if (/^\d{4}\.\d{4,5}(v\d+)?$/.test(id) || /^[a-z-]+\/\d+$/.test(id)) {
      return `https://arxiv.org/abs/${id}`;
    }
    return null;
  };

  // Build Semantic Scholar link
  const getS2Link = (paper) => {
    if (paper.semantic_scholar_id) {
      return `https://www.semanticscholar.org/paper/${paper.semantic_scholar_id}`;
    }
    if (paper.s2_id && paper.s2_id !== 'N/A') {
      return `https://www.semanticscholar.org/paper/${paper.s2_id}`;
    }
    return null;
  };

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
                placeholder="Search papers or queries..."
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
                <div>No papers discovered yet.</div>
                <div style={{ fontSize: 9, marginTop: 4, color: 'var(--text-tertiary)' }}>
                  Papers will appear here as the agent searches.
                </div>
              </div>
            ) : filtered.map((p) => (
              <div
                key={p.id}
                className={`paper-card ${selectedPaperChunks?.paper_id === p.id ? 'selected' : ''}`}
                onClick={() => { onSelectPaper(p.id); setActiveTab('chunks'); }}
              >
                <div className="paper-card-top">
                  <div className="paper-title">{p.title || p.id}</div>
                  <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                    {!p.is_discovered && (
                      <span className="badge badge-emerald" style={{ fontSize: 9 }}>
                        <CheckCircle size={8} /> Indexed
                      </span>
                    )}
                    {p.is_discovered && (
                      <span className="badge badge-amber" style={{ fontSize: 9 }}>
                        <BookOpen size={8} /> Found
                      </span>
                    )}
                  </div>
                </div>

                {/* Authors */}
                <div className="paper-authors">
                  {p.authors?.length > 0
                    ? (Array.isArray(p.authors) ? p.authors.join(', ') : p.authors)
                    : 'Authors Unknown'
                  } ({p.year || 'n.d.'})
                </div>

                {/* Source query context */}
                {p.source_query && (
                  <div className="paper-source-query">
                    <Search size={8} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span>Found for: "{p.source_query}"</span>
                  </div>
                )}

                {/* Bottom: ID + Links */}
                <div className="paper-card-bottom">
                  <span className="paper-id-tag">{p.id}</span>
                  <div className="paper-links" onClick={(e) => e.stopPropagation()}>
                    {getArxivLink(p) && (
                      <a href={getArxivLink(p)} target="_blank" rel="noopener noreferrer" className="paper-ext-link">
                        arXiv <ExternalLink size={8} />
                      </a>
                    )}
                    {getS2Link(p) && (
                      <a href={getS2Link(p)} target="_blank" rel="noopener noreferrer" className="paper-ext-link">
                        S2 <ExternalLink size={8} />
                      </a>
                    )}
                    {p.pdf_url && (
                      <a href={p.pdf_url} target="_blank" rel="noopener noreferrer" className="paper-ext-link">
                        PDF <ExternalLink size={8} />
                      </a>
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
