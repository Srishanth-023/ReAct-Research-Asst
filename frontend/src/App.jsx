import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import QueryInput from './components/QueryInput';
import TraceView from './components/TraceView';
import SourcesPanel from './components/SourcesPanel';
import HistoryModal from './components/HistoryModal';
import { 
  streamQuery, 
  fetchPapers, 
  fetchQueries, 
  fetchQueryDetails, 
  fetchPaperChunks,
  clearHistory,
  clearIndexedPapers
} from './services/api';
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
    setStatusMessage('Initiating academic search agent...');

    await streamQuery({
      query: queryText,
      mode,
      onEvent: (evt) => {
        if (evt.type === 'status') setStatusMessage(evt.content || 'Active...');
        else if (['thought', 'action', 'observation', 'error'].includes(evt.type)) {
          setSteps((prev) => [...prev, evt]);
          if (evt.type === 'error') {
            setStatusMessage('Error encountered.');
            setIsStreaming(false);
          }
        } else if (evt.type === 'answer') {
          setFinalAnswer(evt.content);
          setStatusMessage('Completed.');
        }
      },
      onError: (err) => {
        setSteps((prev) => [...prev, { type: 'error', content: `API connection failed. Make sure the backend server is running.` }]);
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
      setStatusMessage('Loading query history...');
      const d = await fetchQueryDetails(queryId);
      setMode(d.mode || 'react');
      setSteps(d.steps || []);
      setFinalAnswer(d.final_answer || null);
    } catch (e) { console.warn(e); }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Are you sure you want to clear all query history?")) return;
    try {
      await clearHistory();
      setSteps([]);
      setFinalAnswer(null);
      await refreshHistory();
    } catch (e) {
      console.warn("Failed to clear history:", e);
    }
  };

  const handleClearPapers = async () => {
    if (!window.confirm("Are you sure you want to clear all indexed papers and vector storage?")) return;
    try {
      await clearIndexedPapers();
      setSelectedPaperChunks(null);
      await refreshPapers();
    } catch (e) {
      console.warn("Failed to clear index:", e);
    }
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
        <div className="container">
          {/* Hero when idle */}
          {steps.length === 0 && !finalAnswer && !isStreaming && (
            <div className="hero">
              <div className="hero-chip">
                <Sparkles size={11} style={{ color: 'var(--purple)' }} />
                <span>Academic Search Engine</span>
              </div>
              <h2>
                Iterative Literature Search &amp;<br />
                <span className="hero-accent">Grounded Reasoning</span>
              </h2>
              <p>
                An assistant that queries literature database indices, parses target texts, and highlights qualitative claims with verifiable inline source citations.
              </p>
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
        </div>
      </main>

      <SourcesPanel
        isOpen={isSourcesOpen}
        onClose={() => setIsSourcesOpen(false)}
        papers={papers}
        onSelectPaper={handleSelectPaper}
        selectedPaperChunks={selectedPaperChunks}
        isLoadingChunks={isLoadingChunks}
        onClearPapers={handleClearPapers}
      />

      <HistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        queries={queries}
        onSelectHistoryQuery={handleSelectHistory}
        isLoading={isLoadingHistory}
        onClearHistory={handleClearHistory}
      />

      <footer className="app-footer">
        <div className="app-footer-inner">
          <div className="app-footer-left">
            <BookOpen size={12} style={{ color: 'var(--purple)' }} />
            <span>Interactive Academic Literature Research</span>
          </div>
          <span>Local Indexing Database</span>
        </div>
      </footer>
    </div>
  );
}
