import json
from tools.search_tools import search_arxiv_tool, search_semantic_scholar_tool
from tools.paper_tools import fetch_paper_tool
from tools.rag_tools import retrieve_context_tool, retrieve_context_all_tool
from tools.math_tools import calculate_tool

# OpenAI function-calling format (tools array with type: "function")
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": "Query arXiv API for academic papers. Returns top candidate papers with titles, arXiv IDs, abstracts, and publication years.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords or topic (e.g. 'ReAct language models reasoning acting')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_semantic_scholar",
            "description": "Query Semantic Scholar API for academic papers, full-text availability status, and citation metadata. Use when arXiv search is insufficient or when checking if a paper has openAccessPdf.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords, paper title, or author names"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_paper",
            "description": "Download a research paper PDF, parse its complete prose body, chunk by section heuristics, and index into the local ChromaDB vector store. This action is idempotent (skips download if already indexed). MUST be called before using retrieve_context on a paper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The primary paper identifier (e.g. arXiv ID like '2210.03629' or Semantic Scholar ID)"
                    },
                    "pdf_url": {
                        "type": "string",
                        "description": "Optional direct PDF download URL if known"
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional paper title for metadata indexing"
                    }
                },
                "required": ["paper_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_context",
            "description": "Semantic RAG search within a specific indexed paper's chunks. Retrieves top relevant passages of prose, section names (Intro/Methodology/Results/etc.), and page numbers. Use this to find evidence, exact claims, and citations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The paper identifier that was previously indexed using fetch_paper"
                    },
                    "query": {
                        "type": "string",
                        "description": "Semantic search query over the paper prose (e.g. 'what methodology did they use for measuring efficiency' or 'limitations and failure modes')"
                    }
                },
                "required": ["paper_id", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_context_all",
            "description": "Semantic RAG search across ALL indexed papers in the current session vector DB. Useful for cross-paper synthesis and comparing claims across multiple papers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Semantic search query to match against all indexed research papers"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Safely evaluate symbolic or numeric mathematical expressions using Sympy. Use whenever verifying numeric claims, computing percentages, efficiency improvements, or statistical ratios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression string (e.g. '(85.2 - 78.4) / 78.4 * 100' or '2**10')"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Terminate the ReAct reasoning loop and output the final synthesized answer. You must include full citations (paper_id, page_number) for all qualitative and quantitative claims in the final answer text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The comprehensive, well-reasoned final answer synthesizing findings across retrieved papers, formatted in markdown with explicit citations."
                    }
                },
                "required": ["answer"]
            }
        }
    }
]

def execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a registered tool by name with provided arguments dict."""
    try:
        if tool_name == "search_arxiv":
            return search_arxiv_tool(
                query=tool_args.get("query", ""),
                max_results=tool_args.get("max_results", 4)
            )
        elif tool_name == "search_semantic_scholar":
            return search_semantic_scholar_tool(
                query=tool_args.get("query", ""),
                max_results=tool_args.get("max_results", 4)
            )
        elif tool_name == "fetch_paper":
            return fetch_paper_tool(
                paper_id=tool_args.get("paper_id", ""),
                pdf_url=tool_args.get("pdf_url"),
                title=tool_args.get("title")
            )
        elif tool_name == "retrieve_context":
            return retrieve_context_tool(
                paper_id=tool_args.get("paper_id", ""),
                query=tool_args.get("query", "")
            )
        elif tool_name == "retrieve_context_all":
            return retrieve_context_all_tool(
                query=tool_args.get("query", "")
            )
        elif tool_name == "calculate":
            return calculate_tool(
                expression=tool_args.get("expression", "")
            )
        elif tool_name == "finish":
            return tool_args.get("answer", "Task completed.")
        else:
            return f"Observation Error: Unknown tool `{tool_name}`."
    except Exception as e:
        return f"Observation Error executing `{tool_name}`: {str(e)}"
