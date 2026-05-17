"""
Paper Reader Agent — Core Loop

This is the heart of the agent: a simple while loop that calls the LLM,
executes tools when requested, and continues until the model is done.
"""

import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI

from config import API_KEY, BASE_URL, MODEL, MAX_ITERATIONS, TEMPERATURE
from tools import TOOL_DEFINITIONS, execute_tool
from mcp_local.client import init_mcp_servers, call_mcp_tool, get_mcp_tool_names, shutdown_mcp_servers

# 白名单工具：模型调用这些工具时无需用户确认，直接执行；其他工具调用时会提示用户确认（因为可能有副作用）
# Tools in this set run without asking; all others require confirmation.
AUTO_APPROVE_TOOLS = {
    "web_search",
    "fetch_arxiv",
    "read_file",
    "read_pdf",
    "list_files",
    "query_paper_index",
    "git_clone",
}

# Directories
SESSION_DIR = Path(__file__).parent / "output" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR = Path(__file__).parent / "skills"


def load_system_prompt() -> str:
    """Load the system prompt from prompts/system.md, with knowledge base injected."""
    prompt_path = Path(__file__).parent / "prompts" / "system.md"
    base_prompt = prompt_path.read_text(encoding="utf-8")

    # Inject paper knowledge base if it exists
    papers_path = Path(__file__).parent / "knowledge" / "papers.json"
    if papers_path.exists():
        try:
            papers = json.loads(papers_path.read_text(encoding="utf-8"))
            if papers:
                kb_section = "\n\n## Your Knowledge Base (papers you've read before)\n\n"
                for p in papers:
                    kb_section += f"- **{p.get('title', '?')}** [{p.get('arxiv_id', '?')}] ({p.get('category', '?')}, {p.get('year', '?')})\n"
                    kb_section += f"  Core innovation: {p.get('innovation', '?')}\n"
                    if p.get('datasets'):
                        kb_section += f"  Datasets: {', '.join(p['datasets'])}\n"
                kb_section += f"\nTotal: {len(papers)} papers indexed. Use query_paper_index to search, save_paper_index after reading new papers.\n"
                base_prompt += kb_section
        except (json.JSONDecodeError, IOError):
            pass

    return base_prompt


def create_client() -> OpenAI:
    """Create the OpenAI-compatible client."""
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


# =============================================================================
# Streaming helper
# 流式输出
# =============================================================================


def _stream_response(client, messages, tools):
    """Call LLM with streaming. Returns (content, tool_calls) when done."""
    # stream 是一个迭代器，每次迭代返回一个增量的响应块（delta），包含文本增量和/或工具调用增量
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=TEMPERATURE,
        stream=True,
    )

    content_parts = []
    reasoning_parts = []
    tool_calls_map = {}  # index -> {id, function_name, arguments}

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # 累积思维链内容（mimo 等推理模型会返回 reasoning_content）
        if getattr(delta, "reasoning_content", None):
            reasoning_parts.append(delta.reasoning_content)

        # Stream text content
        if delta.content:
            print(delta.content, end="", flush=True)
            content_parts.append(delta.content)

        # 累积工具调用（流式时 tool_calls 分多个 chunk 到达）
        # 例如模型要调用 fetch_arxiv(arxiv_id="2310.06625")，实际到达顺序：
        #   chunk1: tool_calls[0].id="call_abc", function.name="fetch_arxiv"
        #   chunk2: tool_calls[0].function.arguments='{"arxi'
        #   chunk3: tool_calls[0].function.arguments='v_id":'
        #   chunk4: tool_calls[0].function.arguments='"2310.06625"}'
        # 所以需要用 map 按 index 累积拼接，最后组装成完整的工具调用
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index  # 第几个工具调用（模型可能同时调多个工具）
                if idx not in tool_calls_map:
                    tool_calls_map[idx] = {
                        "id": tc_delta.id or "",
                        "function_name": "",
                        "arguments": "",
                    }
                if tc_delta.id:  # id 只在第一个 chunk 出现
                    tool_calls_map[idx]["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:  # 函数名只在第一个 chunk 出现
                        tool_calls_map[idx]["function_name"] = tc_delta.function.name
                    if tc_delta.function.arguments:  # 参数 JSON 分多次到达，拼接
                        tool_calls_map[idx]["arguments"] += tc_delta.function.arguments

    # Newline after streamed text
    if content_parts:
        print()

    # Convert tool_calls_map to list format
    tool_calls = None
    if tool_calls_map:
        tool_calls = []
        for idx in sorted(tool_calls_map.keys()):
            tc = tool_calls_map[idx]
            tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function_name"],
                    "arguments": tc["arguments"],
                },
            })

    content = "".join(content_parts)
    reasoning_content = "".join(reasoning_parts) or None
    return content, tool_calls, reasoning_content


# =============================================================================
# Session persistence
# =============================================================================


def _get_session_path(session_id: str) -> Path:
    return SESSION_DIR / f"session_{session_id}.json"


def save_session(conversation: list, session_id: str) -> None:
    """Save conversation to a session file."""
    data = {
        "session_id": session_id,
        "updated_at": datetime.now().isoformat(),
        "model": MODEL,
        "messages": conversation,
    }
    path = _get_session_path(session_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session(session_id: str) -> list | None:
    """Load conversation from a session file. Returns None if not found."""
    path = _get_session_path(session_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["messages"]
    except (json.JSONDecodeError, KeyError):
        return None


def list_sessions() -> list[dict]:
    """List all saved sessions with metadata."""
    sessions = []
    for f in sorted(SESSION_DIR.glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # Find first user message as preview
            preview = ""
            for msg in data.get("messages", []):
                if msg.get("role") == "user":
                    preview = msg["content"][:60] if isinstance(msg["content"], str) else ""
                    break
            sessions.append({
                "id": data.get("session_id", f.stem),
                "updated_at": data.get("updated_at", ""),
                "model": data.get("model", ""),
                "preview": preview,
                "turns": sum(1 for m in data.get("messages", []) if m.get("role") == "user"),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return sessions


def generate_session_id() -> str:
    """Generate a new session ID based on timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# =============================================================================
# Skill system
# =============================================================================


def list_skills() -> list[dict]:
    """Scan skills/ directory for available skills."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for skill_md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        name = skill_md.parent.name
        content = skill_md.read_text(encoding="utf-8")
        description = ""
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                for line in content[3:end].split("\n"):
                    if line.strip().startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip("\"'")
                        break
        skills.append({"name": name, "description": description})
    return skills


def load_skill(name: str) -> str | None:
    """Load a skill's SKILL.md content by name. Returns None if not found."""
    if not SKILLS_DIR.exists():
        return None
    direct = SKILLS_DIR / name / "SKILL.md"
    if direct.exists():
        return direct.read_text(encoding="utf-8")
    for skill_md in SKILLS_DIR.rglob("SKILL.md"):
        if skill_md.parent.name == name:
            return skill_md.read_text(encoding="utf-8")
    return None


# =============================================================================
# Agent core loop
# =============================================================================


def run_agent(user_message: str, conversation: list | None = None) -> str:
    """
    Run one full agent turn: send user message, loop on tool calls until done.
    Uses streaming for real-time output.
    """
    client = create_client()

    if conversation is None:
        conversation = [{"role": "system", "content": load_system_prompt()}]

    conversation.append({"role": "user", "content": user_message})

    iterations = 0

    # === THE AGENT LOOP ===
    while iterations < MAX_ITERATIONS:
        iterations += 1

        # Call LLM with streaming
        content, tool_calls, reasoning_content = _stream_response(client, conversation, TOOL_DEFINITIONS)

        # Case 1: Model wants to call tools
        if tool_calls:
            # Add assistant message with tool calls to history
            assistant_msg = {"role": "assistant", "content": content or None, "tool_calls": tool_calls}
            if reasoning_content:
                assistant_msg["reasoning_content"] = reasoning_content
            conversation.append(assistant_msg)

            # Execute each tool call
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                print(f"  🔧 [{func_name}] {_summarize_args(func_args)}")

                # Auto-approve read-only tools; ask for others
                if func_name not in AUTO_APPROVE_TOOLS:
                    confirm = input("     执行? [Y/n/a(lwaysallow)/quit]: ").strip().lower()
                    if confirm in ("quit", "exit", "q"):
                        return "[用户中断]"
                    if confirm in ("n", "no"):
                        conversation.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": "Tool execution skipped by user.",
                        })
                        continue
                    if confirm in ("a", "always", "alwaysallow"):
                        AUTO_APPROVE_TOOLS.add(func_name)
                        print(f"     ✅ '{func_name}' 已加入本次会话白名单")

                # Execute the tool (local or MCP)
                if func_name in get_mcp_tool_names():
                    result = call_mcp_tool(func_name, func_args)
                else:
                    result = execute_tool(func_name, func_args)

                conversation.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            continue

        # Case 2: Model responds with text only — we're done
        assistant_msg = {"role": "assistant", "content": content}
        if reasoning_content:
            assistant_msg["reasoning_content"] = reasoning_content
        conversation.append(assistant_msg)
        return content

    return "[Agent reached maximum iterations without completing]"


def _summarize_args(args: dict) -> str:
    """Short summary of tool arguments for display."""
    parts = []
    for k, v in args.items():
        s = str(v)
        if len(s) > 60:
            s = s[:57] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts) if parts else ""


# =============================================================================
# Interactive CLI
# =============================================================================


def main():
    """Interactive REPL for the Paper Reader Agent."""
    print("=" * 60)
    print("  📚 Paper Reader Agent — Time Series Research")
    print("=" * 60)
    print()
    print("Commands:")
    print("  Type your question or instruction")
    print("  'quit' or 'exit'  — leave (auto-saves session)")
    print("  'new'             — start a fresh conversation")
    print("  'sessions'        — list saved sessions")
    print("  'resume'          — resume a saved session")
    print("  'skills'          — list available skills")
    print("  '/<skill> <task>' — invoke a skill (e.g. /research find PatchTST)")
    print()

    # Check for existing sessions to resume
    session_id = generate_session_id()
    conversation = [{"role": "system", "content": load_system_prompt()}]

    existing = list_sessions()
    if existing:
        print(f"  💾 Found {len(existing)} saved session(s). Type 'resume' to load one.")
        print()

    # Initialize MCP servers
    try:
        mcp_tools = init_mcp_servers()
        if mcp_tools:
            TOOL_DEFINITIONS.extend(mcp_tools)
            print(f"  🔌 MCP: {len(mcp_tools)} external tools loaded")
            print()
    except Exception as e:
        print(f"  ⚠️  MCP init failed ({e}), continuing without MCP tools")
        print()

    while True:
        try:
            user_input = input("\n📝 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            save_session(conversation, session_id)
            shutdown_mcp_servers()
            print(f"\n  💾 Session saved: {session_id}")
            print("Bye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            save_session(conversation, session_id)
            shutdown_mcp_servers()
            print(f"  💾 Session saved: {session_id}")
            print("Bye!")
            break

        if user_input.lower() == "new":
            save_session(conversation, session_id)
            session_id = generate_session_id()
            conversation = [{"role": "system", "content": load_system_prompt()}]
            print("🔄 New conversation started.")
            continue

        if user_input.lower() == "sessions":
            sessions = list_sessions()
            if not sessions:
                print("  (No saved sessions)")
            else:
                print(f"\n  {'ID':<20} {'Turns':<6} {'Updated':<22} Preview")
                print(f"  {'-'*20} {'-'*5} {'-'*21} {'-'*30}")
                for s in sessions[:10]:
                    print(f"  {s['id']:<20} {s['turns']:<6} {s['updated_at'][:19]:<22} {s['preview']}")
            continue

        if user_input.lower() == "resume":
            sessions = list_sessions()
            if not sessions:
                print("  (No saved sessions)")
                continue
            print("\n  Available sessions:")
            for i, s in enumerate(sessions[:10], 1):
                print(f"  [{i}] {s['id']}  ({s['turns']} turns)  {s['preview']}")
            choice = input("\n  Enter number or session ID: ").strip()
            # Parse choice
            loaded = None
            if choice.isdigit() and 1 <= int(choice) <= len(sessions):
                loaded = load_session(sessions[int(choice) - 1]["id"])
                session_id = sessions[int(choice) - 1]["id"]
            else:
                loaded = load_session(choice)
                if loaded:
                    session_id = choice
            if loaded:
                conversation = loaded
                turn_count = sum(1 for m in conversation if m.get("role") == "user")
                print(f"  ✅ Resumed session {session_id} ({turn_count} turns)")
            else:
                print("  ❌ Session not found")
            continue

        # Skill commands
        if user_input.lower() in ("skills", "/skills"):
            available = list_skills()
            if not available:
                print("  (No skills installed. Create skills/<name>/SKILL.md)")
            else:
                print("\n  Available skills:")
                for s in available:
                    print(f"    /{s['name']:<20} {s['description']}")
                print(f"\n  Usage: /<skill-name> <your instruction>")
            continue

        if user_input.startswith("/"):
            parts = user_input[1:].split(None, 1)
            skill_name = parts[0]
            instruction = parts[1] if len(parts) > 1 else ""

            skill_content = load_skill(skill_name)
            if skill_content is None:
                print(f"  Unknown skill: {skill_name}")
                print("  Type 'skills' to see available skills.")
                continue

            combined = f'[Skill "{skill_name}" activated — follow the workflow below.]\n\n'
            combined += skill_content.strip()
            if instruction:
                combined += f"\n\n---\n\nUser instruction: {instruction}"
            else:
                combined += "\n\n---\n\nThe user activated this skill without a specific instruction. Ask what they'd like to research."

            print(f"  📖 Skill '{skill_name}' loaded.")
            print("\n🤖 Agent:")
            response = run_agent(combined, conversation)
            if not response:
                print("(No response)")
            save_session(conversation, session_id)
            continue

        # Run the agent
        print("\n🤖 Agent:")
        response = run_agent(user_input, conversation)
        # (streaming already printed the response)
        if not response:
            print("(No response)")

        # Auto-save after each turn
        save_session(conversation, session_id)


if __name__ == "__main__":
    main()
