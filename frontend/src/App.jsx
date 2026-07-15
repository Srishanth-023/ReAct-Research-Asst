import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import QueryInput from './components/QueryInput';
import TraceView from './components/TraceView';
import SourcesPanel from './components/SourcesPanel';
import HistoryModal from './components/HistoryModal';
import { streamQuery, fetchPapers, fetchQueries, fetchQueryDetails, fetchPaperChunks } from './services/api';
import { BookOpen, Sparkles } from 'lucide-react';

export default function App() {
  const [mode, setMode] = useState('react');
  const [steps, setSteps] = useState([]);
  const [finalAnswer, setFinalAnswer] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const [isSourcesOpen, setIsSourcesOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [papers, setPapers] = useState([]);
  const [queries, setQueries] = useState([]);
  const [selectedPaperChunks, setSelectedPaperChunks] = useState(null);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const refreshPapers = useCallback(async () => {
    try { setPapers(await fetchPapers() || []); } catch (e) { console.warn(e); }
  }, []);

  const refreshHistory = useCallback(async () => {
    try { setIsLoadingHistory(true); setQueries(await fetchQueries() || []); }
    catch (e) { console.warn(e); }
    finally { setIsLoadingHistory(false); }
  }, []);

  useEffect(() => { refreshPapers(); }, [refreshPapers]);

  const handleSendQuery = async (queryText) => {
    if (isStreaming) return;
    setSteps([]); setFinalAnswer(null); setIsStreaming(true);
    setStatusMessage(`Initiating ReAct agent in [${mode.toUpperCase()}] mode...`);

    await streamQuery({
      query: queryText,
      mode,
      onEvent: (evt) => {
        if (evt.type === 'status') setStatusMessage(evt.content || 'Agent active...');
        else if (['thought', 'action', 'observation', 'error'].includes(evt.type)) {
          setSteps((prev) => [...prev, evt]);
          if (evt.type === 'error') setStatusMessage('Error encountered.');
        } else if (evt.type === 'answer') {
          setFinalAnswer(evt.content);
          setStatusMessage('Completed.');
        }
      },
      onError: (err) => {
        setSteps((prev) => [...prev, { type: 'error', content: `Backend connection error (${err.message}). Is Flask running on port 5000?` }]);
        setIsStreaming(false);
      },
      onClose: () => { setIsStreaming(false); refreshPapers(); },
    });
  };

  const handleSelectPaper = async (paperId) => {
    setIsSourcesOpen(true);
    try {
      setIsLoadingChunks(true);
      const res = await fetchPaperChunks(paperId);
      const chunks = res.chunks || [];
      chunks.paper_id = paperId;
      setSelectedPaperChunks(chunks);
    } catch (e) { console.warn(e); }
    finally { setIsLoadingChunks(false); }
  };

  const handleSelectHistory = async (queryId) => {
    try {
      setStatusMessage('Loading trajectory from SQLite...');
      const d = await fetchQueryDetails(queryId);
      setMode(d.mode || 'react');
      setSteps(d.steps || []);
      setFinalAnswer(d.final_answer || null);
    } catch (e) { console.warn(e); }
  };

  return (
    <div className="app-layout">
      <Header
        mode={mode}
        setMode={setMode}
        onOpenHistory={() => { refreshHistory(); setIsHistoryOpen(true); }}
        onToggleSources={() => setIsSourcesOpen(!isSourcesOpen)}
        isSourcesOpen={isSourcesOpen}
        papersCount={papers.length}
      />

      <main className="app-main">
        {/* Hero when idle */}
        {steps.length === 0 && !finalAnswer && !isStreaming && (
          <div className="hero">
            <div className="hero-chip">
              <Sparkles size={12} style={{ color: 'var(--purple)' }} />
              <span>Full-Stack ReAct Research Engine</span>
            </div>
            <h2>
              Grounded Academic Reasoning<br />
              <span className="hero-accent">over Full-Text Literature</span>
            </h2>
            <p>
              Interleaves internal <strong>Thought</strong> with external <strong>Actions</strong> (search_arxiv, fetch_paper, retrieve_context, calculate) to eliminate hallucinations and output verifiable (paper_id, page X) prose citations.
            </p>
            <div className="hero-tags">
              <span className="hero-tag">Flask + SSE</span>
              <span className="hero-tag">ChromaDB (all-MiniLM-L6-v2)</span>
              <span className="hero-tag">SQLite (react_research.db)</span>
              <span className="hero-tag">pdfplumber + fitz</span>
            </div>
          </div>
        )}

        <TraceView
          steps={steps}
          finalAnswer={finalAnswer}
          isStreaming={isStreaming}
          statusMessage={statusMessage}
          onSelectPaper={handleSelectPaper}
        />

        <QueryInput onSendQuery={handleSendQuery} isStreaming={isStreaming} mode={mode} />
      </main>

      <SourcesPanel
        isOpen={isSourcesOpen}
        onClose={() => setIsSourcesOpen(false)}
        papers={papers}
        onSelectPaper={handleSelectPaper}
        selectedPaperChunks={selectedPaperChunks}
        isLoadingChunks={isLoadingChunks}
      />

      <HistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        queries={queries}
        onSelectHistoryQuery={handleSelectHistory}
        isLoading={isLoadingHistory}
      />

      <footer className="app-footer">
        <div className="app-footer-inner">
          <div className="app-footer-left">
            <BookOpen size={13} style={{ color: 'var(--purple)' }} />
            <span>Yao et al., ICLR 2023 (2210.03629)</span>
          </div>
          <span>React 18 + Vite · Flask REST + SSE</span>
        </div>
      </footer>
    </div>
  );
}
