import json
import re
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
)
from database.db import get_session
from models.schema import Query, TrajectoryStep, Citation, Paper
from tools.registry import TOOL_DEFINITIONS, execute_tool
from react.prompts import get_system_prompt_for_mode


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


def resolve_model_name(client, model_param, is_anthropic=False):
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
                for preferred in ["gpt-4o", "grok", "deepseek", "llama", "mistral"]:
                    matching = [mid for mid in model_ids if preferred in mid.lower()]
                    if matching:
                        return matching[0]
                return model_ids[0]
        except Exception:
            pass
        return "gpt-4o"  # Ultimate default
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
            actual_model = resolve_model_name(cl, target_model, is_anthropic=True)
            return cl, actual_model, True
        else:
            if not is_fallback and (not target_key or "api_key" in target_key):
                raise ValueError("API key is not configured.")
            # OpenAI-compatible client wrapper
            url = target_url.strip() if target_url else None
            cl = openai.OpenAI(api_key=target_key or "free-fallback", base_url=url)
            actual_model = resolve_model_name(cl, target_model, is_anthropic=False)
            return cl, actual_model, False

    # Set up initial client
    client = None
    model_name = ""
    is_anthropic = False
    is_using_fallback = False

    try:
        client, model_name, is_anthropic = build_client(API_KEY, BASE_URL, MODEL_NAME)
        yield {
            "type": "status",
            "content": f"Connected to primary API endpoint. Model resolved to: {model_name}"
        }
    except Exception as e:
        # Primary provider setup failed. Fallback immediately to local fallback.
        yield {
            "type": "status",
            "content": f"Primary API setup failed: {e}. Falling back to local endpoint ({FALLBACK_BASE_URL})..."
        }
        is_using_fallback = True
        try:
            client, model_name, is_anthropic = build_client("", FALLBACK_BASE_URL, FALLBACK_MODEL_NAME, is_fallback=True)
            yield {
                "type": "status",
                "content": f"Connected to local fallback. Model resolved to: {model_name}"
            }
        except Exception as fallback_err:
            yield {
                "type": "error",
                "content": f"Primary setup failed, and fallback initialization failed: {fallback_err}"
            }
            return

    step_num = 1
    last_tool_signature = None

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
            if not is_using_fallback:
                yield {
                    "type": "status",
                    "content": f"Primary API call failed: {e}. Retrying zero-shot query via local fallback..."
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
                    yield {"type": "error", "content": f"Primary API failed, and local fallback failed: {fallback_err}"}
                    return
            else:
                yield {"type": "error", "content": f"API Error: {e}"}
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
            if not is_using_fallback:
                yield {
                    "type": "status",
                    "content": f"Primary API call failed: {e}. Retrying CoT query via local fallback..."
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
                    yield {"type": "error", "content": f"Primary API failed, and local fallback failed: {fallback_err}"}
                    return
            else:
                yield {"type": "error", "content": f"API Error: {e}"}
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
        try:
            if not is_anthropic:
                response = client.chat.completions.create(
                    model=model_name,
                    max_tokens=2500,
                    messages=openai_messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto"
                )
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
                    max_tokens=2500,
                    system=system_prompt,
                    tools=anthropic_tools,
                    messages=anthropic_messages
                )
        except Exception as e:
            if not is_using_fallback:
                yield {
                    "type": "status",
                    "content": f"Primary API failed: {e}. Continuing loop via local fallback endpoint..."
                }
                is_using_fallback = True
                try:
                    client, model_name, is_anthropic = build_client("", FALLBACK_BASE_URL, FALLBACK_MODEL_NAME, is_fallback=True)
                except Exception as fallback_err:
                    yield {"type": "error", "content": f"Local fallback setup failed: {fallback_err}"}
                    return
                if not openai_messages or len(openai_messages) <= 2:
                    openai_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ]
                continue
            else:
                err_msg = f"API Error at step {step_num}: {e}"
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
            return

    # If MAX_STEPS reached
    timeout_answer = (
        f"### Stopping Condition Reached (Max {MAX_STEPS} Steps)\n"
        f"The agent reached the maximum allowed reasoning steps before invoking `finish`. "
        f"Here is a summary of the latest reasoning observations from the trace above."
    )
    with get_session() as session:
        step_ans = TrajectoryStep(query_id=query_id, step_number=step_num, step_type="answer", content=timeout_answer)
        session.add(step_ans)
        q = session.query(Query).filter_by(id=query_id).first()
        if q:
            q.final_answer = timeout_answer
    yield {"type": "answer", "content": timeout_answer, "step": step_num}
