from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
from chat import run_model_tool_loop, trim_history, safe_slug, now_iso, write_transcript

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"

load_lab_env(ROOT)

# Page configuration
st.set_page_config(
    page_title="Research Agent - Day 04 Lab",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern design aesthetics
st.markdown(
    """
    <style>
    /* Global styles */
    .stApp {
        background-color: #0e1117;
        color: #e0e6ed;
    }
    
    /* Header card */
    .header-card {
        background: linear-gradient(135deg, #1e2640 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .header-title {
        font-size: 24px;
        font-weight: 700;
        color: #38bdf8;
        margin: 0 0 8px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-subtitle {
        font-size: 14px;
        color: #94a3b8;
        margin: 0;
    }

    /* Version badge */
    .version-badge {
        display: inline-block;
        background: #0284c7;
        color: #ffffff;
        font-family: monospace;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        margin-top: 6px;
    }

    /* Hash badges */
    .hash-badge {
        background: #1e293b;
        border: 1px solid #475569;
        color: #cbd5e1;
        font-family: monospace;
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
    }

    /* Tool Call Card */
    .tool-card {
        background-color: #1e293b;
        border-left: 4px solid #38bdf8;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 8px 0;
    }

    .tool-name {
        font-family: monospace;
        font-weight: bold;
        color: #38bdf8;
    }

    .status-waiting {
        color: #f59e0b;
        font-weight: bold;
    }
    .status-answered {
        color: #10b981;
        font-weight: bold;
    }
    .status-error {
        color: #ef4444;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "turns_history" not in st.session_state:
        st.session_state.turns_history = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "transcript_id" not in st.session_state:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        st.session_state.transcript_id = f"ui_{timestamp}"


def reset_session() -> None:
    st.session_state.messages = []
    st.session_state.turns_history = []
    st.session_state.history = []
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    st.session_state.transcript_id = f"ui_{timestamp}"


def main() -> None:
    init_session_state()

    # --- SIDEBAR CONFIGURATION ---
    st.sidebar.title("⚙️ Agent Settings")

    provider_name = st.sidebar.selectbox(
        "Model Provider",
        options=["openrouter", "openai", "anthropic", "gemini"],
        index=0,
        help="Select model provider for the agent",
    )

    model_override = st.sidebar.text_input(
        "Model Override (Optional)",
        value="",
        placeholder="e.g. google/gemini-2.5-flash",
        help="Leave empty for provider default",
    )

    version_label = st.sidebar.text_input(
        "Artifact Version Label",
        value="v3",
        help="e.g., v0, v1, v2, v3",
    )

    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"

    max_tool_rounds = st.sidebar.slider("Max Tool Rounds", min_value=1, max_value=10, value=4)
    history_window = st.sidebar.slider("History Window", min_value=1, max_value=10, value=5)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Active Files Inspection")

    with st.sidebar.expander("📝 System Prompt"):
        if system_prompt_path.exists():
            st.code(system_prompt_path.read_text(encoding="utf-8"), language="markdown")
        else:
            st.warning(f"File not found: {system_prompt_path}")

    with st.sidebar.expander("🛠️ Tools Declaration (YAML)"):
        if tools_path.exists():
            st.code(tools_path.read_text(encoding="utf-8"), language="yaml")
        else:
            st.warning(f"File not found: {tools_path}")

    if st.sidebar.button("🔄 Reset Chat Session", use_container_width=True):
        reset_session()
        st.rerun()

    # --- ARTIFACT VERSION CALCULATION ---
    artifact_ver = build_artifact_version(version_label, system_prompt_path, tools_path)

    # --- MAIN INTERFACE HEADER ---
    st.markdown(
        f"""
        <div class="header-card">
            <div class="header-title">
                🔬 Research Agent Execution & Evaluation UI
            </div>
            <div class="header-subtitle">
                Interactive Multi-turn Agent Playground with Evidence Tracing & Tool Execution Logs
            </div>
            <div style="margin-top: 10px;">
                <span class="version-badge">Version: {artifact_ver.artifact_version}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Info bar
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Provider", provider_name)
    with col2:
        st.metric("Model", model_override or "Default")
    with col3:
        st.caption("Prompt Hash")
        st.markdown(f"<span class='hash-badge'>{artifact_ver.prompt_hash[:12]}</span>", unsafe_allow_html=True)
    with col4:
        st.caption("Tools Hash")
        st.markdown(f"<span class='hash-badge'>{artifact_ver.tools_hash[:12]}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # Tabs for Chat & Transcript viewer
    tab_chat, tab_transcript, tab_runs = st.tabs(["💬 Interactive Chat & Tool Trace", "📜 Live Transcript JSON", "📊 Runs / Evaluation History"])

    with tab_chat:
        # Render existing message history
        for turn in st.session_state.turns_history:
            # User message
            with st.chat_message("user"):
                st.write(turn["user"])

            # Assistant response message
            with st.chat_message("assistant"):
                # Display Tool Trace if any rounds occurred
                rounds = turn.get("rounds", [])
                tool_events = turn.get("tool_events", [])
                status = turn.get("status", "completed")

                if tool_events:
                    with st.expander(f"🛠️ Tool Execution Trace ({len(tool_events)} tool call(s), {len(rounds)} round(s))", expanded=False):
                        for r in rounds:
                            st.markdown(f"**Round {r.get('round')}**")
                            if r.get("assistant_text"):
                                st.caption(f"Assistant Note: {r.get('assistant_text')}")
                            for tc in r.get("tool_calls", []):
                                st.markdown(f"🔹 **Call:** `{tc['name']}`")
                                st.json(tc.get("args", {}), expanded=False)
                            for tr in r.get("tool_results", []):
                                res = tr.get("result", {})
                                if isinstance(res, dict) and res.get("error"):
                                    st.error(f"Error in `{tr['tool']}`: {res.get('error')} - {res.get('message')}")
                                else:
                                    st.success(f"Result from `{tr['tool']}`")
                                    st.json(res, expanded=False)
                            st.divider()

                # Status indicator
                if status == "waiting_for_user":
                    st.warning("⚠️ Agent is awaiting user response / confirmation.")
                elif status == "max_tool_rounds":
                    st.warning("⚠️ Stopped after max tool rounds limit.")
                elif status == "provider_error":
                    st.error(f"❌ Provider Error: {turn.get('error')}")

                st.write(turn.get("assistant_text") or "")

        # Chat Input
        if user_input := st.chat_input("Nhập câu hỏi hoặc yêu cầu nghiên cứu của bạn..."):
            # Display user message immediately
            with st.chat_message("user"):
                st.write(user_input)

            turn_index = len(st.session_state.turns_history) + 1
            turn_record: dict[str, Any] = {
                "turn_index": turn_index,
                "started_at": now_iso(),
                "user": user_input,
                "status": "started",
                "assistant_text": None,
                "rounds": [],
                "tool_events": [],
            }

            # Prepare agent dependencies
            try:
                system_prompt = system_prompt_path.read_text(encoding="utf-8")
                tool_declarations = load_tool_declarations(tools_path)
                openai_tools = to_openai_tools(tool_declarations)
                provider = make_provider(provider_name)
                selected_model = model_override.strip() if model_override.strip() else getattr(provider, "default_model", None)

                messages = [
                    {"role": "system", "content": system_prompt},
                    *trim_history(st.session_state.history, history_window),
                    {"role": "user", "content": user_input},
                ]

                with st.chat_message("assistant"):
                    with st.spinner("Agent is reasoning and executing tools..."):
                        result = run_model_tool_loop(
                            provider=provider,
                            messages=messages,
                            tools=openai_tools,
                            model=selected_model,
                            max_tool_rounds=max_tool_rounds,
                        )

                    turn_record.update(result)
                    assistant_text = result.get("assistant_text", "")

                    # Render tools execution trace
                    rounds = result.get("rounds", [])
                    tool_events = result.get("tool_events", [])
                    if tool_events:
                        with st.expander(f"🛠️ Tool Execution Trace ({len(tool_events)} tool call(s), {len(rounds)} round(s))", expanded=True):
                            for r in rounds:
                                st.markdown(f"**Round {r.get('round')}**")
                                if r.get("assistant_text"):
                                    st.caption(f"Assistant Note: {r.get('assistant_text')}")
                                for tc in r.get("tool_calls", []):
                                    st.markdown(f"🔹 **Call:** `{tc['name']}`")
                                    st.json(tc.get("args", {}), expanded=False)
                                for tr in r.get("tool_results", []):
                                    res = tr.get("result", {})
                                    if isinstance(res, dict) and res.get("error"):
                                        st.error(f"Error in `{tr['tool']}`: {res.get('error')} - {res.get('message')}")
                                    else:
                                        st.success(f"Result from `{tr['tool']}`")
                                        st.json(res, expanded=False)
                                st.divider()

                    if result.get("status") == "waiting_for_user":
                        st.warning("⚠️ Agent is awaiting user response / confirmation.")

                    st.write(assistant_text)

                    # Update history
                    st.session_state.history.append({"role": "user", "content": user_input})
                    st.session_state.history.append({"role": "assistant", "content": assistant_text})

            except Exception as exc:
                turn_record.update({
                    "status": "provider_error",
                    "error": f"{type(exc).__name__}: {str(exc)}",
                })
                with st.chat_message("assistant"):
                    st.error(f"❌ Error: {type(exc).__name__}: {str(exc)}")

            turn_record["ended_at"] = now_iso()
            st.session_state.turns_history.append(turn_record)

            # Auto-save transcript
            transcript_filename = f"{safe_slug(version_label)}_{safe_slug(provider_name)}_{st.session_state.transcript_id}.transcript.json"
            transcript_path = TRANSCRIPTS_DIR / transcript_filename
            transcript_data = {
                "transcript_id": st.session_state.transcript_id,
                **artifact_version_dict(artifact_ver),
                "provider": provider_name,
                "model": selected_model if 'selected_model' in locals() else None,
                "system_prompt": str(system_prompt_path),
                "tools": str(tools_path),
                "history_window": history_window,
                "max_tool_rounds": max_tool_rounds,
                "created_at": now_iso(),
                "updated_at": now_iso(),
                "turns": st.session_state.turns_history,
            }
            write_transcript(transcript_path, transcript_data)

    with tab_transcript:
        st.subheader("📜 Current Session Transcript JSON")
        if st.session_state.turns_history:
            current_transcript = {
                "transcript_id": st.session_state.transcript_id,
                **artifact_version_dict(artifact_ver),
                "provider": provider_name,
                "turns": st.session_state.turns_history,
            }
            st.json(current_transcript)
        else:
            st.info("No chat turns yet in current session.")

        st.divider()
        st.subheader("📁 Saved Transcripts in `transcripts/`")
        if TRANSCRIPTS_DIR.exists():
            transcript_files = sorted(list(TRANSCRIPTS_DIR.glob("*.json")), reverse=True)
            if transcript_files:
                selected_file = st.selectbox("Select saved transcript", options=[f.name for f in transcript_files])
                if selected_file:
                    target_file = TRANSCRIPTS_DIR / selected_file
                    st.code(target_file.read_text(encoding="utf-8"), language="json")
            else:
                st.caption("No transcript files saved yet in `transcripts/`.")

    with tab_runs:
        st.subheader("📊 Evaluation Run Log Summaries")
        runs_dir = ROOT / "runs"
        if runs_dir.exists():
            run_files = sorted(list(runs_dir.glob("*.json")), reverse=True)
            if run_files:
                selected_run = st.selectbox("Select run JSON to inspect", options=[f.name for f in run_files])
                if selected_run:
                    target_run = runs_dir / selected_run
                    try:
                        run_data = json.loads(target_run.read_text(encoding="utf-8"))
                        summary = run_data.get("summary", {})
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Case Accuracy", f"{summary.get('case_accuracy', 0):.1%}" if isinstance(summary.get('case_accuracy'), (int, float)) else str(summary.get('case_accuracy')))
                        c2.metric("Tool Routing Accuracy", f"{summary.get('tool_routing_accuracy', 0):.1%}" if isinstance(summary.get('tool_routing_accuracy'), (int, float)) else str(summary.get('tool_routing_accuracy')))
                        c3.metric("Argument Accuracy", f"{summary.get('argument_accuracy', 0):.1%}" if isinstance(summary.get('argument_accuracy'), (int, float)) else str(summary.get('argument_accuracy')))
                        c4.metric("Provider Errors", summary.get("provider_error_cases", 0))

                        with st.expander("Full Run Data"):
                            st.json(run_data)
                    except Exception as e:
                        st.error(f"Failed to parse run JSON: {e}")
            else:
                st.info("No run JSON files found in `runs/` directory yet.")
        else:
            st.info("`runs/` directory does not exist yet.")


if __name__ == "__main__":
    main()
