import React from 'react';

/**
 * Lightweight markdown-to-JSX renderer.
 * Handles: headings (###, ##), bold (**), italic (*), inline code (`),
 * code blocks (```), and list items (- / *).
 * Also supports citation pills via an optional onSelectPaper callback.
 */
export default function MarkdownRenderer({ text, onSelectPaper }) {
  if (!text) return null;

  // Process citation highlights
  const highlightCitations = (str) => {
    if (!onSelectPaper) return str;
    const regex = /\(([`'"""]?([a-zA-Z0-9.\-\/]+)[`'"""]?\s*,\s*page\s*(\d+))\)/gi;
    const parts = [];
    let lastIdx = 0;
    let match;
    while ((match = regex.exec(str)) !== null) {
      if (match.index > lastIdx) parts.push(str.substring(lastIdx, match.index));
      const paperId = match[2];
      const pageNum = match[3];
      parts.push(
        <button
          key={`${match.index}-${paperId}`}
          type="button"
          onClick={() => onSelectPaper(paperId)}
          className="citation-pill"
          title={`Inspect paper '${paperId}' page ${pageNum}`}
        >
          <span>{paperId} (p.{pageNum})</span>
        </button>
      );
      lastIdx = regex.lastIndex;
    }
    if (lastIdx < str.length) parts.push(str.substring(lastIdx));
    return parts.length > 0 ? parts : str;
  };

  // Process inline formatting: bold, italic, inline code
  const processInline = (str) => {
    if (typeof str !== 'string') return str;

    const tokens = [];
    // Regex matches: **bold**, *italic*, `code`
    const inlineRegex = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g;
    let lastIdx = 0;
    let match;

    while ((match = inlineRegex.exec(str)) !== null) {
      // Push text before match
      if (match.index > lastIdx) {
        const before = str.substring(lastIdx, match.index);
        const cited = highlightCitations(before);
        if (Array.isArray(cited)) tokens.push(...cited);
        else tokens.push(cited);
      }

      if (match[2]) {
        // **bold**
        tokens.push(<strong key={`b-${match.index}`} className="md-bold">{highlightCitations(match[2])}</strong>);
      } else if (match[3]) {
        // *italic*
        tokens.push(<em key={`i-${match.index}`} className="md-italic">{highlightCitations(match[3])}</em>);
      } else if (match[4]) {
        // `code`
        tokens.push(<code key={`c-${match.index}`} className="md-inline-code">{match[4]}</code>);
      }

      lastIdx = inlineRegex.lastIndex;
    }

    // Remaining text
    if (lastIdx < str.length) {
      const rest = str.substring(lastIdx);
      const cited = highlightCitations(rest);
      if (Array.isArray(cited)) tokens.push(...cited);
      else tokens.push(cited);
    }

    return tokens.length > 0 ? tokens : highlightCitations(str);
  };

  // Split text into lines and process
  const lines = text.split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code blocks: ```...```
    if (line.trim().startsWith('```')) {
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre key={`code-${i}`} className="md-code-block">
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
      continue;
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="md-heading md-h3">{processInline(line.slice(4))}</h3>
      );
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="md-heading md-h2">{processInline(line.slice(3))}</h2>
      );
      i++;
      continue;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="md-heading md-h1">{processInline(line.slice(2))}</h1>
      );
      i++;
      continue;
    }

    // List items
    if (/^[-*]\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        listItems.push(
          <li key={`li-${i}`} className="md-list-item">{processInline(lines[i].replace(/^[-*]\s+/, ''))}</li>
        );
        i++;
      }
      elements.push(<ul key={`ul-${i}`} className="md-list">{listItems}</ul>);
      continue;
    }

    // Empty lines
    if (!line.trim()) {
      elements.push(<div key={`sp-${i}`} style={{ height: 6 }} />);
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={`p-${i}`} className="md-paragraph">{processInline(line)}</p>
    );
    i++;
  }

  return <div className="md-rendered">{elements}</div>;
}
