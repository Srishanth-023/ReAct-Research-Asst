import json
import re
import logging
from datetime import datetime, timezone
import openai
import anthropic

from config import (
    API_KEY,
    BASE_URL,
    MODEL_NAME,
    FALLBACK_BASE_URL,
    FALLBACK_MODEL_NAME,
    MAX_STEPS,
    MIN_TOOL_CALLS_BEFORE_FINISH,
)
from database.db import get_session
from models.schema import Query, TrajectoryStep, Citation, Paper
from tools.registry import TOOL_DEFINITIONS, execute_tool
from react.prompts import get_system_prompt_for_mode

logger = logging.getLogger("ReActEngine")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def format_api_error(err: Exception) -> str:
    """
    Convert raw technical API error objects/dictionaries (e.g., Error code: 429 - {'error': ...})
    into clean, user-friendly, human-understandable messages.
    """
    err_str = str(err)
    
    status_code = None
    code_match = re.search(r'Error code:\s*(\d+)', err_str, re.IGNORECASE)
    if code_match:
        status_code = int(code_match.group(1))
    elif hasattr(err, 'status_code') and err.status_code:
        status_code = err.status_code
        
    msg_clean = None
    msg_match = re.search(r"['\"]message['\"]\s*:\s*['\"]([^'\"]+)['\"]", err_str)
    if msg_match:
        msg_clean = msg_match.group(1)
    elif hasattr(err, 'message') and err.message:
        msg_clean = str(err.message)
    elif hasattr(err, 'body') and isinstance(err.body, dict):
        err_obj = err.body.get('error', {})
        if isinstance(err_obj, dict) and 'message' in err_obj:
            msg_clean = str(err_obj['message'])
        elif isinstance(err_obj, str):
            msg_clean = err_obj
            
    if status_code or msg_clean:
        if status_code == 429 or (msg_clean and ("quota" in msg_clean.lower() or "rate limit" in msg_clean.lower() or "exceeded" in msg_clean.lower() or "billing" in msg_clean.lower())):
            header = "API Quota / Rate Limit Exceeded (HTTP 429)"
            detail = msg_clean if msg_clean else "You have exceeded your current quota or rate limit on the LLM API provider. Please check your billing details or API credits."
            return f"{header}: {detail}"
        elif status_code == 401 or (msg_clean and ("incorrect api key" in msg_clean.lower() or "unauthorized" in msg_clean.lower() or "invalid api key" in msg_clean.lower() or "authentication" in msg_clean.lower())):
            header = "Authentication Failed (HTTP 401 - Invalid API Key)"
            detail = msg_clean if msg_clean else "The API key provided in .env is incorrect, expired, or unauthorized for this provider endpoint."
            return f"{header}: {detail}"
        elif status_code == 404 or (msg_clean and ("model not found" in msg_clean.lower() or "does not exist" in msg_clean.lower() or "no such model" in msg_clean.lower())):
            header = "Model or Endpoint Not Found (HTTP 404)"
            detail = msg_clean if msg_clean else "The requested model or base URL endpoint could not be found on the API provider."
            return f"{header}: {detail}"
        elif status_code == 403:
            header = "Access Forbidden (HTTP 403)"
            detail = msg_clean if msg_clean else "Your API key does not have permission to access the requested model or API resource."
            return f"{header}: {detail}"
        elif status_code in (500, 502, 503, 504):
            header = f"API Provider Server Error (HTTP {status_code})"
            detail = msg_clean if msg_clean else "The LLM API provider is currently experiencing server issues or downtime."
            return f"{header}: {detail}"
        elif msg_clean:
            prefix = f"API Error (HTTP {status_code})" if status_code else "API Error"
            return f"{prefix}: {msg_clean}"

    if "ConnectionRefusedError" in err_str or "Failed to establish a new connection" in err_str or "ConnectTimeout" in err_str or "Connection error" in err_str:
        return "Connection Error: Could not connect to the LLM API endpoint. If using a local service (Ollama/LM Studio), please ensure it is running and accessible."
        
    return f"API Communication Error: {err_str}"



def extract_and_record_citations(query_id: int, final_answer: str, session):
    """
    Scan final answer for citation patterns like (`2210.03629`, page 3)
    and record them in the Citation table.
    """
    pattern = re.compile(r'\(([`\'\"]?([a-zA-Z0-9\.\-\/]+)[`\'\"]?\s*,\s*page\s*(\d+))\)', re.IGNORECASE)
    matches = pattern.findall(final_answer or "")

    seen = set()
    for full_match, paper_id_raw, page_str in matches:
        p_id = paper_id_raw.strip('`\'"')
        try:
            page_num = int(page_str)
        except Exception:
            page_num = None

        key = (p_id, page_num)
        if key in seen:
            continue
        seen.add(key)

        paper_record = session.query(Paper).filter_by(id=p_id).first()
        if not paper_record:
            paper_record = Paper(id=p_id, title=f"Paper {p_id}", indexed_at=datetime.now(timezone.utc))
            session.add(paper_record)
            session.flush()

        citation = Citation(
            query_id=query_id,
            paper_id=p_id,
            chunk_text=f"Cited from {p_id} at page {page_num}",
            page_number=page_num
        )
        session.add(citation)


def parse_text_action(text: str):
    """
    Fallback parser to extract action names and arguments from the model's text response
    when it doesn't use the API's native tool calling framework.
    Supports standard Action format, markdown code blocks, and raw JSON dict formats.
    """
    # 1. First, check for standard ReAct Action patterns: e.g., Action: search_arxiv({"query": "..."})
    pattern = re.compile(
        r'Action\s*\d*\s*:\s*`?([a-zA-Z0-9_-]+)`?\s*(?:\((.*?)\)|(\{.*?\}))',
        re.IGNORECASE | re.DOTALL
    )
    match = pattern.search(text)
    if match:
        tool_name = match.group(1).strip()
        args_str = match.group(2) or match.group(3)
        args_str = args_str.strip()
        try:
            tool_args = json.loads(args_str)
        except Exception:
            try:
                clean_args = args_str.replace("'", '"')
                tool_args = json.loads(clean_args)
            except Exception:
                tool_args = {"query": args_str}
        return tool_name, tool_args

    # 2. Next, check for JSON/Python block matching tool call structure:
    # e.g., {"name": "search_arxiv", "parameters": {"query": "..."}} or {"name": "...", "arguments": ...}
    # Using a brace-counting algorithm to safely extract dictionaries including nested ones
    for i in range(len(text)):
        if text[i] == '{':
            brace_count = 1
            for j in range(i + 1, len(text)):
                if text[j] == '{':
                    brace_count += 1
                elif text[j] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        candidate = text[i:j+1]
                        try:
                            # Clean up single quotes
                            candidate_clean = candidate.replace("'", '"')
                            data = json.loads(candidate_clean)
                            if isinstance(data, dict) and "name" in data:
                                name = data["name"]
                                args = data.get("parameters") or data.get("arguments") or data.get("args") or {}
                                if isinstance(args, dict):
                                    return name, args
                                elif isinstance(args, str):
                                    try:
                                        return name, json.loads(args)
                                    except Exception:
                                        return name, {"query": args}
                        except Exception:
                            pass
                        break
                        
    return None, None


def parse_papers_from_observation(tool_name: str, obs_text: str, source_query: str = "") -> list:
    """
    Parse structured paper data from search_arxiv or search_semantic_scholar observation text.
    Returns a list of dicts with keys: id, title, authors, year, pdf_url, source_query, source_tool.
    """
    if tool_name not in ("search_arxiv", "search_semantic_scholar"):
        return []
    
    papers = []
    # Pattern: [N] ID: <id> (S2: <s2_id>)? | Year: <year>
    #          Title: <title>
    #          Authors: <authors>
    #          Abstract snippet: <abstract>
    #          PDF URL: <url> or Download Status: <status>
    blocks = re.split(r'\n\[(\d+)\]\s*', obs_text)
    # blocks[0] is header, then alternating: block_number, block_content
    for i in range(1, len(blocks), 2):
        block = blocks[i + 1] if i + 1 < len(blocks) else ""
        paper = {"source_query": source_query, "source_tool": tool_name}
        
        # Extract ID
        id_match = re.search(r'ID:\s*([^\s|]+)', block)
        if id_match:
            paper["id"] = id_match.group(1).strip().rstrip(')')
        
        # Extract S2 ID if present
        s2_match = re.search(r'\(S2:\s*([^)]+)\)', block)
        if s2_match:
            paper["s2_id"] = s2_match.group(1).strip()
        
        # Extract Year
        year_match = re.search(r'Year:\s*(\d{4}|Unknown)', block)
        if year_match and year_match.group(1) != 'Unknown':
            paper["year"] = int(year_match.group(1))
        
        # Extract Title
        title_match = re.search(r'Title:\s*(.+?)(?:\n|$)', block)
        if title_match:
            paper["title"] = title_match.group(1).strip()
        
        # Extract Authors
        authors_match = re.search(r'Authors:\s*(.+?)(?:\n|$)', block)
        if authors_match:
            paper["authors"] = authors_match.group(1).strip()
        
        # Extract Abstract
        abstract_match = re.search(r'Abstract snippet:\s*(.+?)(?:\n|$)', block, re.DOTALL)
        if abstract_match:
            paper["abstract"] = abstract_match.group(1).strip().rstrip('...')
        
        # Extract PDF URL
        pdf_match = re.search(r'PDF URL:\s*(http\S+)', block)
        if pdf_match:
            paper["pdf_url"] = pdf_match.group(1).strip()
        
        if paper.get("id"):
            papers.append(paper)
    
    return papers


def generate_super_summary(client, model_name, is_anthropic, observations, final_answer, user_query):
    """
    Make an additional LLM call to synthesize all observations and the final answer
    into a comprehensive super summary.
    """
    obs_text = "\n\n---\n\n".join(
        f"[Observation from {obs.get('tool_name', 'unknown')}]:\n{obs.get('content', '')[:1500]}"
        for obs in observations
    )
    
    synthesis_prompt = f"""You are a research synthesis assistant. The user asked: "{user_query}"

An AI research agent has gathered the following observations from multiple papers and tools:

{obs_text}

The agent's individual answer was:
{final_answer[:3000]}

Your task: Write a comprehensive SUPER SUMMARY that synthesizes ALL the findings above into a single, cohesive, well-structured overview. This should:
1. Identify the key themes and findings across all papers
2. Highlight agreements and disagreements between sources
3. Provide a unified narrative that connects all the evidence
4. Note any gaps or areas needing further research

Write in clean prose paragraphs. Use section headings as plain text on their own line (no # or ** symbols). Keep it concise but comprehensive (3-5 paragraphs)."""

    try:
        if not is_anthropic:
            response = client.chat.completions.create(
                model=model_name,
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": "You are a concise academic research synthesis assistant. Write in clean prose without markdown formatting symbols."},
                    {"role": "user", "content": synthesis_prompt}
                ]
            )
            return response.choices[0].message.content or ""
        else:
            response = client.messages.create(
                model=model_name,
                max_tokens=2000,
                system="You are a concise academic research synthesis assistant. Write in clean prose without markdown formatting symbols.",
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            return response.content[0].text if response.content else ""
    except Exception as e:
        logger.error(f"[Super Summary] Failed to generate: {e}")
        return ""


def resolve_model_name(client, model_param, is_anthropic=False, is_fallback=False):
    """
    If the model name is 'auto' or empty, query the models endpoint to select the first active model.
    """
    if not model_param or model_param.lower() == "auto":
        if is_anthropic:
            return "claude-3-5-sonnet-20241022"
        try:
            models_data = client.models.list()
            model_ids = [m.id for m in models_data.data]
            if model_ids:
                # Prioritize high-performance or common agent models if found in IDs
                for preferred in ["gpt-4o", "grok", "deepseek", "llama", "mistral", "qwen"]:
                    matching = [mid for mid in model_ids if preferred in mid.lower()]
                    if matching:
                        logger.info(f"[Model Resolution] Auto-detected preferred model '{matching[0]}' from API provider.")
                        return matching[0]
                logger.info(f"[Model Resolution] Auto-detected model '{model_ids[0]}' from API provider.")
                return model_ids[0]
        except Exception as e:
            if not is_fallback:
                clean_err = format_api_error(e)
                logger.error(f"[Model Resolution Error] Failed to query /models list from endpoint '{client.base_url}': {clean_err}")
                logger.debug("[Model Resolution Traceback]", exc_info=True)
                # If /models query failed because of an API error (401 invalid key, 429 quota, connection refused, 403), raise it!
                if hasattr(e, 'status_code') or "Error code:" in str(e) or "Connection" in str(e):
                    raise e
            # Fallback defaults based on whether it is local (Ollama) or custom remote
            if is_fallback or (client.base_url and "11434" in str(client.base_url)):
                return "llama3.1"
            if client.base_url and "api.openai.com" not in str(client.base_url):
                url_lower = str(client.base_url).lower()
                if "deepseek" in url_lower:
                    return "deepseek-chat"
                elif "x.ai" in url_lower:
                    return "grok-beta"
                return "default-model"
            return "gpt-4o"  # Ultimate default only for standard OpenAI
    return model_param


def run_agent_trace(user_query: str, mode: str = "react", query_id: int = None):
    """
    Generator yielding SSE event dictionaries while running the ReAct loop.
    Supports any OpenAI-compatible custom base URL and automatic model resolution.
    If the primary API fails, it automatically falls back to local free endpoint (Ollama).
    """
    mode_clean = mode.lower().strip()
    system_prompt = get_system_prompt_for_mode(mode_clean)

    # Initialize SQLite query record
    with get_session() as session:
        if not query_id:
            query_record = Query(user_query=user_query, mode=mode_clean)
            session.add(query_record)
            session.flush()
            query_id = query_record.id
        else:
            query_record = session.query(Query).filter_by(id=query_id).first()
            if query_record:
                query_record.mode = mode_clean

    # ── Client Builder Helper ──
    def build_client(target_key, target_url, target_model, is_fallback=False):
        # Determine if key is Anthropic format
        is_anthropic = target_key.startswith("sk-ant-")
        if is_anthropic:
            if not target_key or "api_key" in target_key:
                raise ValueError("Anthropic API key is not configured.")
            cl = anthropic.Anthropic(api_key=target_key)
            actual_model = resolve_model_name(cl, target_model, is_anthropic=True, is_fallback=is_fallback)
            return cl, actual_model, True
        else:
            if not is_fallback and (not target_key or "api_key" in target_key or target_key == "free-fallback"):
                raise ValueError("API key is not configured.")
            # OpenAI-compatible client wrapper
            url = target_url.strip() if target_url else None
            cl = openai.OpenAI(api_key=target_key or "free-fallback", base_url=url)
            actual_model = resolve_model_name(cl, target_model, is_anthropic=False, is_fallback=is_fallback)
            return cl, actual_model, False

    # Set up initial client
    client = None
    model_name = ""
    is_anthropic = False
    is_using_fallback = False

    try:
        logger.info(f"[API Setup] Initializing primary API connection (URL: '{BASE_URL or 'https://api.openai.com/v1'}', Model requested: '{MODEL_NAME}')")
        client, model_name, is_anthropic = build_client(API_KEY, BASE_URL, MODEL_NAME)
        logger.info(f"[API Setup] Connected to primary API endpoint (`{BASE_URL or 'OpenAI Default'}`). Active Model: '{model_name}'")
        yield {
            "type": "status",
            "content": f"Connected to primary API endpoint (`{BASE_URL or 'OpenAI Default'}`). Active Model: `{model_name}`"
        }
    except Exception as e:
        clean_err = format_api_error(e)
        logger.error(f"[PRIMARY API ERROR] Failed during primary API setup/communication: {clean_err}")
        logger.debug("[PRIMARY API ERROR Traceback]", exc_info=True)
        
        logger.info(f"[API Fallback] Primary API ({BASE_URL or 'Default'}) encountered an issue: '{clean_err}'. Automatically switching to local Ollama (`{FALLBACK_BASE_URL}`)...")
        yield {
            "type": "status",
            "content": f"Primary API error (`{clean_err}`). Automatically switching to local Ollama fallback (`{FALLBACK_BASE_URL}`)..."
        }
        is_using_fallback = True
        try:
            client, model_name, is_anthropic = build_client("", FALLBACK_BASE_URL, FALLBACK_MODEL_NAME, is_fallback=True)
            logger.info(f"[API Fallback] Connected to local Ollama endpoint (`{FALLBACK_BASE_URL}`). Active Model: '{model_name}'")
            yield {
                "type": "status",
                "content": f"Connected to local Ollama (`{FALLBACK_BASE_URL}`). Active Model: `{model_name}`"
            }
        except Exception as fallback_err:
            clean_fallback_err = format_api_error(fallback_err)
            logger.error(f"[FALLBACK SETUP ERROR] Could not initialize local Ollama fallback: {clean_fallback_err}", exc_info=True)
            yield {
                "type": "error",
                "content": f"API Connection Failed: Primary API error (`{clean_err}`) and local Ollama server (`{FALLBACK_BASE_URL}`) is unreachable or returned (`{clean_fallback_err}`). Please verify your API key/billing or ensure Ollama is running (`ollama serve`)."
            }
            return

    step_num = 1
    last_tool_signature = None
    tool_call_count = 0          # Track total tool executions for premature-finish guard
    collected_observations = []  # Collect observations for super summary generation

    # ── 1. Run Standard Mode (Zero-shot) ──
    if mode_clean == "standard":
        try:
            if not is_anthropic:
                response = client.chat.completions.create(
                    model=model_name,
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ]
                )
                answer_text = response.choices[0].message.content or "No response generated."
            else:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_query}]
                )
                answer_text = response.content[0].text if response.content else "No response generated."

            with get_session() as session:
                step = TrajectoryStep(query_id=query_id, step_number=1, step_type="answer", content=answer_text)
                session.add(step)
                q = session.query(Query).filter_by(id=query_id).first()
                if q:
                    q.final_answer = answer_text
            yield {"type": "answer", "content": answer_text, "step": step_num}
            return
        except Exception as e:
            clean_err = format_api_error(e)
            logger.error(f"[API ERROR - Standard Mode] API call failed on endpoint '{BASE_URL or 'OpenAI Default'}' (Model: '{model_name}'): {clean_err}")
            logger.debug("[API ERROR - Standard Mode Traceback]", exc_info=True)
            if not is_using_fallback:
                yield {
                    "type": "status",
                    "content": f"Primary API error (`{clean_err}`). Automatically switching to local Ollama fallback (`{FALLBACK_BASE_URL}`)..."
                }
                is_using_fallback = True
                try:
                    client, model_name, is_anthropic = build_client("", FALLBACK_BASE_URL, FALLBACK_MODEL_NAME, is_fallback=True)
                    response = client.chat.completions.create(
                        model=model_name,
                        max_tokens=2048,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ]
                    )
                    answer_text = response.choices[0].message.content or "No response generated."
                    with get_session() as session:
                        step = TrajectoryStep(query_id=query_id, step_number=1, step_type="answer", content=answer_text)
                        session.add(step)
                        q = session.query(Query).filter_by(id=query_id).first()
                        if q:
                            q.final_answer = answer_text
                    yield {"type": "answer", "content": answer_text, "step": step_num}
                    return
                except Exception as fallback_err:
                    clean_fallback = format_api_error(fallback_err)
                    logger.error(f"[FALLBACK ERROR - Standard Mode] {clean_fallback}", exc_info=True)
                    yield {"type": "error", "content": f"Primary API failed (`{clean_err}`) and local Ollama server (`{FALLBACK_BASE_URL}`) is unreachable (`{clean_fallback}`). Please verify your API credentials/billing or ensure Ollama is running (`ollama serve`)."}
                    return
            else:
                yield {"type": "error", "content": f"API Error (`{BASE_URL or 'OpenAI Default'}` - `{model_name}`): {clean_err}", "step": step_num}
                return

    # ── 2. Run CoT Mode (Reasoning Only) ──
    elif mode_clean == "cot":
        try:
            if not is_anthropic:
                response = client.chat.completions.create(
                    model=model_name,
                    max_tokens=3000,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ]
                )
                full_text = response.choices[0].message.content or ""
            else:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=3000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_query}]
                )
                full_text = response.content[0].text if response.content else ""
        except Exception as e:
            clean_err = format_api_error(e)
            logger.error(f"[API ERROR - CoT Mode] API call failed on endpoint '{BASE_URL or 'OpenAI Default'}' (Model: '{model_name}'): {clean_err}")
            logger.debug("[API ERROR - CoT Mode Traceback]", exc_info=True)
            if not is_using_fallback:
                yield {
                    "type": "status",
                    "content": f"Primary API error (`{clean_err}`). Automatically switching to local Ollama fallback (`{FALLBACK_BASE_URL}`)..."
                }
                is_using_fallback = True
                try:
                    client, model_name, is_anthropic = build_client("", FALLBACK_BASE_URL, FALLBACK_MODEL_NAME, is_fallback=True)
                    response = client.chat.completions.create(
                        model=model_name,
                        max_tokens=3000,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ]
                    )
                    full_text = response.choices[0].message.content or ""
                except Exception as fallback_err:
                    clean_fallback = format_api_error(fallback_err)
                    logger.error(f"[FALLBACK ERROR - CoT Mode] {clean_fallback}", exc_info=True)
                    yield {"type": "error", "content": f"Primary API failed (`{clean_err}`) and local Ollama server (`{FALLBACK_BASE_URL}`) is unreachable (`{clean_fallback}`). Please verify your API credentials/billing or ensure Ollama is running (`ollama serve`)."}
                    return
            else:
                yield {"type": "error", "content": f"API Error (`{BASE_URL or 'OpenAI Default'}` - `{model_name}`): {clean_err}", "step": step_num}
                return

        parts = full_text.split("\n\nFinal Answer:") if "\n\nFinal Answer:" in full_text else full_text.split("### Final Answer")
        if len(parts) > 1:
            thought_text = parts[0].strip()
            answer_text = parts[-1].strip()
        else:
            thought_text = full_text.strip()
            answer_text = full_text.strip()

        with get_session() as session:
            step_t = TrajectoryStep(query_id=query_id, step_number=1, step_type="thought", content=thought_text)
            step_a = TrajectoryStep(query_id=query_id, step_number=2, step_type="answer", content=answer_text)
            session.add(step_t)
            session.add(step_a)
            q = session.query(Query).filter_by(id=query_id).first()
            if q:
                q.final_answer = answer_text

        yield {"type": "thought", "content": thought_text, "step": 1}
        yield {"type": "answer", "content": answer_text, "step": 2}
        return

    # ── 3. ReAct / Act Modes (Iterative loops with tool selection) ──
    openai_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]
    anthropic_messages = [{"role": "user", "content": user_query}]

    while step_num <= MAX_STEPS:
        yield {
            "type": "status",
            "content": f"Step {step_num}: Model is thinking and reasoning..."
        }
        try:
            if not is_anthropic:
                kwargs = {
                    "model": model_name,
                    "max_tokens": 3500,
                    "messages": openai_messages,
                }
                
                if is_using_fallback:
                    # ── Local Ollama Enhancements ──
                    # 1. Optimize context window to 4096 so it runs 3x faster on local CPU/GPU hardware.
                    kwargs["extra_body"] = {"options": {"num_ctx": 4096}}
                    # 2. Omit native tools schema to massively speed up prompt evaluation time.
                    # The text-based fallback parser handles the tools naturally via the system prompt text.
                    kwargs["stream"] = True
                else:
                    kwargs["tools"] = TOOL_DEFINITIONS
                    kwargs["tool_choice"] = "auto"
                    
                response = client.chat.completions.create(**kwargs)
            else:
                anthropic_tools = []
                for t in TOOL_DEFINITIONS:
                    fn = t["function"]
                    anthropic_tools.append({
                        "name": fn["name"],
                        "description": fn["description"],
                        "input_schema": fn["parameters"]
                    })
                response = client.messages.create(
                    model=model_name,
                    max_tokens=3500,
                    system=system_prompt,
                    tools=anthropic_tools,
                    messages=anthropic_messages
                )
        except Exception as e:
            clean_err = format_api_error(e)
            logger.error(f"[API ERROR - ReAct Step {step_num}] API call failed on endpoint '{BASE_URL or 'OpenAI Default'}' (Model: '{model_name}'): {clean_err}")
            logger.debug(f"[API ERROR - ReAct Step {step_num} Traceback]", exc_info=True)
            
            if not is_using_fallback:
                yield {
                    "type": "status",
                    "content": f"Primary API error (`{clean_err}`). Automatically switching to local Ollama fallback (`{FALLBACK_BASE_URL}`)..."
                }
                is_using_fallback = True
                try:
                    client, model_name, is_anthropic = build_client("", FALLBACK_BASE_URL, FALLBACK_MODEL_NAME, is_fallback=True)
                except Exception as fallback_err:
                    clean_fallback = format_api_error(fallback_err)
                    logger.error(f"[FALLBACK SETUP ERROR - ReAct Step {step_num}] {clean_fallback}", exc_info=True)
                    yield {"type": "error", "content": f"Primary API failed (`{clean_err}`) and local Ollama server (`{FALLBACK_BASE_URL}`) is unreachable (`{clean_fallback}`). Please verify your API credentials/billing or ensure Ollama is running (`ollama serve`)."}
                    return
                if not openai_messages or len(openai_messages) <= 2:
                    openai_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ]
                continue
            else:
                err_msg = f"API Error (`{BASE_URL or 'OpenAI Default'}` - `{model_name}`): {clean_err}"
                with get_session() as session:
                    step = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="error", content=err_msg)
                    session.add(step)
                yield {"type": "error", "content": err_msg, "step": step_num}
                return

        # ── Process Success Response ──
        thought_text = ""
        tool_calls = []
        tool_use_blocks = []

        if not is_anthropic:
            if is_using_fallback:
                for chunk in response:
                    token = chunk.choices[0].delta.content or ""
                    if token:
                        thought_text += token
                        yield {"type": "stream_chunk", "content": token}
            else:
                choice = response.choices[0]
                assistant_msg = choice.message
                thought_text = assistant_msg.content or ""
                tool_calls = assistant_msg.tool_calls or []
        else:
            for block in response.content:
                if block.type == "text":
                    if block.text and block.text.strip():
                        thought_text += block.text.strip() + "\n"
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

        # Record thought if any
        if thought_text.strip() and mode_clean != "act":
            with get_session() as session:
                step_rec = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="thought", content=thought_text.strip())
                session.add(step_rec)
            yield {"type": "thought", "content": thought_text.strip(), "step": step_num}
            step_num += 1

        # Check for termination
        if (not is_anthropic and not tool_calls) or (is_anthropic and not tool_use_blocks):
            fallback_tool_name, fallback_tool_args = parse_text_action(thought_text)
            if fallback_tool_name:
                args_json_str = json.dumps(fallback_tool_args, sort_keys=True)
                current_signature = (fallback_tool_name, args_json_str)

                # ── Premature Finish Guard ──
                if fallback_tool_name == "finish" and tool_call_count < MIN_TOOL_CALLS_BEFORE_FINISH:
                    logger.info(f"[Premature Finish Guard] Agent tried to finish after only {tool_call_count} tool calls (minimum: {MIN_TOOL_CALLS_BEFORE_FINISH}). Redirecting.")
                    redirect_msg = (
                        f"You have only executed {tool_call_count} tool calls so far. "
                        f"This is insufficient for a comprehensive research answer. "
                        f"You must search for more papers, fetch and index them, and retrieve context from their full text "
                        f"before calling finish. Continue your research with more tool calls."
                    )
                    if not is_anthropic:
                        openai_messages.append({"role": "assistant", "content": thought_text})
                        openai_messages.append({"role": "user", "content": f"Observation: {redirect_msg}"})
                    else:
                        anthropic_messages.append({"role": "assistant", "content": thought_text})
                        anthropic_messages.append({"role": "user", "content": f"Observation: {redirect_msg}"})
                    yield {"type": "observation", "content": redirect_msg, "tool_name": "system_guard", "step": step_num}
                    step_num += 1
                    continue

                # Yield tool execution status
                yield {
                    "type": "status",
                    "content": f"Step {step_num}: Executing tool '{fallback_tool_name}'..."
                }

                # Repetition Guard
                if current_signature == last_tool_signature:
                    obs_result = (
                        f"Observation Repetition Guard: You just executed tool `{fallback_tool_name}` with identical arguments "
                        f"in your previous step and received the exact same observation. To prevent reasoning loops, "
                        f"you MUST NOT repeat this exact call. Please try a different query or fetch a new paper."
                    )
                else:
                    last_tool_signature = current_signature
                    obs_result = execute_tool(fallback_tool_name, fallback_tool_args)

                if fallback_tool_name == "finish":
                    finished_answer = obs_result

                tool_call_count += 1

                # Record Action step
                with get_session() as session:
                    step_act = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="action", tool_name=fallback_tool_name, tool_args=args_json_str)
                    session.add(step_act)
                yield {"type": "action", "tool_name": fallback_tool_name, "tool_args": fallback_tool_args, "step": step_num}
                step_num += 1

                # Record Observation step
                if fallback_tool_name != "finish":
                    with get_session() as session:
                        step_obs = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="observation", content=obs_result, tool_name=fallback_tool_name)
                        session.add(step_obs)
                    yield {"type": "observation", "content": obs_result, "tool_name": fallback_tool_name, "step": step_num}
                    step_num += 1

                    # Collect observation for super summary
                    collected_observations.append({"tool_name": fallback_tool_name, "content": obs_result})

                    # ── Emit papers_found for search tools ──
                    source_query = fallback_tool_args.get("query", "")
                    found_papers = parse_papers_from_observation(fallback_tool_name, obs_result, source_query)
                    if found_papers:
                        yield {"type": "papers_found", "papers": found_papers, "source_query": source_query, "step": step_num}

                    # Append tool result (OpenAI / Anthropic format)
                    if not is_anthropic:
                        openai_messages.append({"role": "assistant", "content": thought_text})
                        openai_messages.append({"role": "user", "content": f"Observation: {obs_result}"})
                    else:
                        anthropic_messages.append({"role": "assistant", "content": thought_text})
                        anthropic_messages.append({"role": "user", "content": f"Observation: {obs_result}"})

                if finished_answer is not None:
                    with get_session() as session:
                        step_ans = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="answer", content=finished_answer)
                        session.add(step_ans)
                        q = session.query(Query).filter_by(id=query_id).first()
                        if q:
                            q.final_answer = finished_answer
                        extract_and_record_citations(query_id, finished_answer, session)
                    yield {"type": "answer", "content": finished_answer, "step": step_num}

                    # ── Generate Super Summary ──
                    if collected_observations and mode_clean in ("react", "act"):
                        yield {"type": "status", "content": "Generating comprehensive super summary..."}
                        super_summary = generate_super_summary(client, model_name, is_anthropic, collected_observations, finished_answer, user_query)
                        if super_summary:
                            yield {"type": "super_summary", "content": super_summary, "step": step_num + 1}
                    return

                continue
            else:
                final_ans = thought_text.strip() or "No tools invoked or text generated."
                with get_session() as session:
                    step_rec = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="answer", content=final_ans)
                    session.add(step_rec)
                    q = session.query(Query).filter_by(id=query_id).first()
                    if q:
                        q.final_answer = final_ans
                    extract_and_record_citations(query_id, final_ans, session)
                yield {"type": "answer", "content": final_ans, "step": step_num}
                return

        # Execute tools
        finished_answer = None

        if not is_anthropic:
            openai_messages.append(assistant_msg.model_dump())
            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {"raw": tc.function.arguments}

                tool_call_id = tc.id
                args_json_str = json.dumps(tool_args, sort_keys=True)
                current_signature = (tool_name, args_json_str)

                # ── Premature Finish Guard ──
                if tool_name == "finish" and tool_call_count < MIN_TOOL_CALLS_BEFORE_FINISH:
                    logger.info(f"[Premature Finish Guard] Agent tried to finish after only {tool_call_count} tool calls (minimum: {MIN_TOOL_CALLS_BEFORE_FINISH}). Redirecting.")
                    obs_result = (
                        f"You have only executed {tool_call_count} tool calls so far. "
                        f"This is insufficient for a comprehensive research answer. "
                        f"You must search for more papers, fetch and index them, and retrieve context from their full text "
                        f"before calling finish. Continue your research with more tool calls."
                    )
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": obs_result
                    })
                    yield {"type": "observation", "content": obs_result, "tool_name": "system_guard", "step": step_num}
                    step_num += 1
                    continue

                # Yield tool execution status
                yield {
                    "type": "status",
                    "content": f"Step {step_num}: Executing tool '{tool_name}'..."
                }

                # Repetition Guard
                if current_signature == last_tool_signature:
                    obs_result = (
                        f"Observation Repetition Guard: You just executed tool `{tool_name}` with identical arguments "
                        f"in your previous step and received the exact same observation. To prevent reasoning loops, "
                        f"you MUST NOT repeat this exact call. Please try a different query or fetch a new paper."
                    )
                else:
                    last_tool_signature = current_signature
                    obs_result = execute_tool(tool_name, tool_args)

                if tool_name == "finish":
                    finished_answer = obs_result

                tool_call_count += 1

                # Record Action step
                with get_session() as session:
                    step_act = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="action", tool_name=tool_name, tool_args=args_json_str)
                    session.add(step_act)
                yield {"type": "action", "tool_name": tool_name, "tool_args": tool_args, "step": step_num}
                step_num += 1

                # Record Observation step
                if tool_name != "finish":
                    with get_session() as session:
                        step_obs = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="observation", content=obs_result, tool_name=tool_name)
                        session.add(step_obs)
                    yield {"type": "observation", "content": obs_result, "tool_name": tool_name, "step": step_num}
                    step_num += 1

                    # Collect observation for super summary
                    collected_observations.append({"tool_name": tool_name, "content": obs_result})

                    # ── Emit papers_found for search tools ──
                    source_query = tool_args.get("query", "")
                    found_papers = parse_papers_from_observation(tool_name, obs_result, source_query)
                    if found_papers:
                        yield {"type": "papers_found", "papers": found_papers, "source_query": source_query, "step": step_num}

                # Append tool result (OpenAI format)
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": obs_result
                })

        else:
            anthropic_messages.append({"role": "assistant", "content": response.content})
            tool_results_content = []

            for t_block in tool_use_blocks:
                tool_name = t_block.name
                tool_args = t_block.input
                tool_use_id = t_block.id

                args_json_str = json.dumps(tool_args, sort_keys=True)
                current_signature = (tool_name, args_json_str)

                # ── Premature Finish Guard ──
                if tool_name == "finish" and tool_call_count < MIN_TOOL_CALLS_BEFORE_FINISH:
                    logger.info(f"[Premature Finish Guard] Agent tried to finish after only {tool_call_count} tool calls (minimum: {MIN_TOOL_CALLS_BEFORE_FINISH}). Redirecting.")
                    obs_result = (
                        f"You have only executed {tool_call_count} tool calls so far. "
                        f"This is insufficient for a comprehensive research answer. "
                        f"You must search for more papers, fetch and index them, and retrieve context from their full text "
                        f"before calling finish. Continue your research with more tool calls."
                    )
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": obs_result
                    })
                    yield {"type": "observation", "content": obs_result, "tool_name": "system_guard", "step": step_num}
                    step_num += 1
                    continue

                # Yield tool execution status
                yield {
                    "type": "status",
                    "content": f"Step {step_num}: Executing tool '{tool_name}'..."
                }

                # Repetition Guard
                if current_signature == last_tool_signature:
                    obs_result = (
                        f"Observation Repetition Guard: You just executed tool `{tool_name}` with identical arguments "
                        f"in your previous step and received the exact same observation. To prevent reasoning loops, "
                        f"you MUST NOT repeat this exact call. Please try a different query or fetch a new paper."
                    )
                else:
                    last_tool_signature = current_signature
                    obs_result = execute_tool(tool_name, tool_args)

                if tool_name == "finish":
                    finished_answer = obs_result

                tool_call_count += 1

                # Record Action step
                with get_session() as session:
                    step_act = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="action", tool_name=tool_name, tool_args=args_json_str)
                    session.add(step_act)
                yield {"type": "action", "tool_name": tool_name, "tool_args": tool_args, "step": step_num}
                step_num += 1

                # Record Observation step
                if tool_name != "finish":
                    with get_session() as session:
                        step_obs = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="observation", content=obs_result, tool_name=tool_name)
                        session.add(step_obs)
                    yield {"type": "observation", "content": obs_result, "tool_name": tool_name, "step": step_num}
                    step_num += 1

                    # Collect observation for super summary
                    collected_observations.append({"tool_name": tool_name, "content": obs_result})

                    # ── Emit papers_found for search tools ──
                    source_query = tool_args.get("query", "") if isinstance(tool_args, dict) else ""
                    found_papers = parse_papers_from_observation(tool_name, obs_result, source_query)
                    if found_papers:
                        yield {"type": "papers_found", "papers": found_papers, "source_query": source_query, "step": step_num}

                # Append tool result (Anthropic format)
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": obs_result
                })

            anthropic_messages.append({"role": "user", "content": tool_results_content})

        if finished_answer is not None:
            with get_session() as session:
                step_ans = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="answer", content=finished_answer)
                session.add(step_ans)
                q = session.query(Query).filter_by(id=query_id).first()
                if q:
                    q.final_answer = finished_answer
                extract_and_record_citations(query_id, finished_answer, session)
            yield {"type": "answer", "content": finished_answer, "step": step_num}

            # ── Generate Super Summary ──
            if collected_observations and mode_clean in ("react", "act"):
                yield {"type": "status", "content": "Generating comprehensive super summary..."}
                super_summary = generate_super_summary(client, model_name, is_anthropic, collected_observations, finished_answer, user_query)
                if super_summary:
                    yield {"type": "super_summary", "content": super_summary, "step": step_num + 1}
            return

    # If MAX_STEPS reached
    timeout_answer = (
        f"Stopping Condition Reached (Max {MAX_STEPS} Steps)\n"
        f"The agent reached the maximum allowed reasoning steps before invoking finish. "
        f"Here is a summary of the latest reasoning observations from the trace above."
    )
    with get_session() as session:
        step_ans = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="answer", content=timeout_answer)
        session.add(step_ans)
        q = session.query(Query).filter_by(id=query_id).first()
        if q:
            q.final_answer = timeout_answer
    yield {"type": "answer", "content": timeout_answer, "step": step_num}

    # ── Generate Super Summary even on timeout ──
    if collected_observations and mode_clean in ("react", "act"):
        yield {"type": "status", "content": "Generating comprehensive super summary..."}
        super_summary = generate_super_summary(client, model_name, is_anthropic, collected_observations, timeout_answer, user_query)
        if super_summary:
            yield {"type": "super_summary", "content": super_summary, "step": step_num + 1}

