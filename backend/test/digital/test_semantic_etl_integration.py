# backend/test/digital/test_semantic_etl_integration.py
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from actions.digital.semantic_etl_client import (
    SemanticETLError,
    is_semantic_etl_healthy,
    upload_document_bytes,
    async_upload_document_bytes,
    get_job_status,
    async_get_job_status,
    query_semantic_rag,
    retrieve_document_context,
    get_health_status,
    async_get_health_status,
)
from core.routing.baseline.actions_catalog import ALL_ACTIONS_CATALOG
from core.routing.layer2.worker_nodes import TOOL_REGISTRY, chat_node
from core.routing.layer2.graph_nodes import (
    document_retrieval_node,
    tool_retrieval_node,
    route_query,
    decide_after_tool_retrieval,
    decide_next_step,
    memory_extraction_node,
    is_workstation_setup_query,
    is_file_operation_query,
)


def test_action_catalog_excludes_document_rag():
    # RAG is a Context-Augmentation Layer, not an Action Tool
    assert "document_rag_node" not in ALL_ACTIONS_CATALOG


def test_tool_registry_excludes_document_rag():
    # Verify tool registry is reserved strictly for actions/side-effects
    assert "document_rag_node" not in TOOL_REGISTRY


@patch("actions.digital.semantic_etl_client.httpx.Client")
def test_health_check_online(mock_client):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "healthy"}
    mock_instance.get.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_instance

    assert is_semantic_etl_healthy() is True
    status_data = get_health_status()
    assert status_data["status"] == "healthy"


@patch("actions.digital.semantic_etl_client.httpx.Client")
def test_upload_document_bytes(mock_client):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.json.return_value = {
        "job_id": "test_job_123",
        "status": "pending",
        "progress": 0.0
    }
    mock_instance.post.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_instance

    res = upload_document_bytes(b"dummy pdf content", "test.pdf")
    assert res["job_id"] == "test_job_123"
    assert res["status"] == "pending"


@patch("actions.digital.semantic_etl_client.httpx.Client")
def test_retrieve_document_context(mock_client):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "answer": "The thesis proposes a dual-layer cognitive architecture.",
        "sources": [
            {
                "citation_id": 1,
                "category": "Architecture",
                "source_pages": ["14", "15"],
                "summary": "Cognitive layer orchestration overview.",
                "text_snippet": "The architecture separates reflexes from cognitive planning."
            }
        ]
    }
    mock_instance.post.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_instance

    res = retrieve_document_context("What architecture does the thesis propose?")
    assert res["has_context"] is True
    assert len(res["sources"]) == 1
    assert res["sources"][0]["citation_id"] == 1


@patch("actions.digital.semantic_etl_client.is_semantic_etl_healthy", return_value=True)
@patch("actions.digital.semantic_etl_client.retrieve_document_context")
def test_document_retrieval_node(mock_retrieve, mock_healthy):
    mock_retrieve.return_value = {
        "answer": "Detailed answer",
        "has_context": True,
        "sources": [
            {
                "citation_id": 1,
                "category": "Requirements",
                "source_pages": [4, 5],
                "summary": "Must requirements list.",
                "text_snippet": "The system must respond within 800ms."
            }
        ]
    }
    state = {
        "messages": [HumanMessage(content="What are the must requirements?")]
    }
    out = document_retrieval_node(state)
    assert "retrieved_documents" in out
    assert len(out["retrieved_documents"]) == 1
    assert out["retrieved_documents"][0]["citation_id"] == 1


@patch("core.routing.llm_factory.get_chat_companion_llm")
def test_chat_node_document_grounding(mock_llm_factory):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="The must requirement is an 800ms response time [1].")
    mock_llm_factory.return_value = mock_llm

    state = {
        "messages": [HumanMessage(content="What are the must requirements?")],
        "summary": "",
        "retrieved_memories": [],
        "retrieved_documents": [
            {
                "citation_id": 1,
                "category": "SRS",
                "source_pages": [4],
                "summary": "Latency constraints",
                "text_snippet": "The system must respond within 800ms."
            }
        ],
        "provider": "local"
    }

    out = chat_node(state)
    assert "messages" in out
    # Verify system message sent to LLM contains the document knowledge base
    sent_messages = mock_llm.invoke.call_args[0][0]
    system_msg = next((m for m in sent_messages if isinstance(m, SystemMessage)), None)
    assert system_msg is not None
    assert "[UPLOADED DOCUMENT KNOWLEDGE BASE]" in system_msg.content
    assert "Latency constraints" in system_msg.content
    assert "Pages: 4" in system_msg.content


@patch("actions.digital.semantic_etl_client.is_semantic_etl_healthy", return_value=False)
def test_document_retrieval_node_offline(mock_healthy):
    state = {
        "messages": [HumanMessage(content="What is in the document?")]
    }
    out = document_retrieval_node(state)
    assert out.get("retrieved_documents") == []


def test_question_and_list_tool_queries_not_bypassed():
    """
    Regression test: Ensure question-phrased or 'what/show me/list' queries for
    weather, web search, math, todoist, and workspace files still retrieve tools
    instead of being short-circuited to chat_node.
    """
    cases = [
        ("is it freezing cold outside in Tokyo today?", "weather_node"),
        ("what is the forecast and rain chance for Vienna tomorrow?", "weather_node"),
        ("who won the Champions League final match?", "web_search_node"),
        ("what is 17 to the power of 3?", "code_executor_node"),
        ("show me all the items currently on my to-do list", "todolist_node"),
        ("list files in the directory", "mcp_pack_filesystem"),
        ("can you read README.md?", "mcp_pack_filesystem"),
    ]
    sample_catalog = [
        {"name": "weather_node", "description": "Weather conditions and forecasts."},
        {"name": "web_search_node", "description": "Live web search."},
        {"name": "code_executor_node", "description": "Python math and calculation sandbox."},
        {"name": "todolist_node", "description": "Manage Todoist tasks and to-do lists."},
        {"name": "mcp_pack_filesystem", "description": "Workspace file operations.", "source_type": "mcp_dormant", "server_pack_id": "mcp_pack_filesystem"},
    ]
    with patch("core.routing.layer2.graph_nodes.tool_rag_registry") as mock_reg:
        mock_reg.db = object()
        mock_reg._tools_source = [
            MagicMock(page_content="Workspace file operations.", metadata={"tool_name": "mcp_pack_filesystem", "source_type": "mcp_dormant", "server_pack_id": "mcp_pack_filesystem"})
        ]
        for query, expected_tool in cases:
            mock_reg.search_relevant_tools.return_value = [
                next(t for t in sample_catalog if t["name"] == expected_tool)
            ]
            res = tool_retrieval_node({"messages": [HumanMessage(content=query)], "retrieved_documents": [{"citation_id": 1}]})
            names = [t["name"] for t in res.get("active_tools", [])]
            assert expected_tool in names, f"Expected '{expected_tool}' for query {query!r}, got {names}"


def test_setup_guards_and_explicit_rag_only_bypass():
    """
    Verifies that setup/file safety guards block doc inquiries without needing a hardcoded
    doc-QA keyword list, and that explicit rag_only mode bypasses both FAISS and LAYA.
    """
    for q in [
        "what are the must requirements?",
        "summarize the uploaded SRS document",
        "what does the thesis say about testing?",
        "read the uploaded PDF document",
    ]:
        assert is_workstation_setup_query(q) is False
        assert is_file_operation_query(q) is False
        assert tool_retrieval_node({"messages": [HumanMessage(content=q)], "rag_only": True}) == {"active_tools": []}

    # Graph short-circuit: rag_only or empty active_tools skips LAYA (route_query) completely
    assert decide_after_tool_retrieval({"rag_only": True, "active_tools": [{"name": "weather_node"}]}) == "document_retrieval_node"
    assert decide_after_tool_retrieval({"rag_only": False, "active_tools": []}) == "document_retrieval_node"
    assert decide_after_tool_retrieval({"rag_only": False, "active_tools": [{"name": "weather_node"}]}) == "route_query"

    # Paraphrased workstation setup commands must remain allowed
    assert is_workstation_setup_query("bring up my study materials and Moodle page") is True
    assert is_workstation_setup_query("boot up PyCharm and open my GitHub repositories") is True
    assert is_workstation_setup_query("what is Moodle?") is False


def test_route_query_enriches_none_when_documents_retrieved():
    """
    When LAYA evaluates candidate tools, verify 'none' criteria cleanly covers
    uploaded document discussion without overpowering tool intents, and rag_only skips LAYA.
    """
    state = {
        "messages": [HumanMessage(content="Explain section 3 architecture")],
        "retrieved_documents": [{"citation_id": 1, "summary": "Section 3 architecture"}],
        "active_tools": [{"name": "web_search_node", "description": "Live web search."}],
    }
    with patch("core.routing.layer2.graph_nodes.get_laya_agent") as mock_laya:
        mock_laya.return_value.predict.return_value = {"answers": {"tool_selection": {"choice": "none"}}}
        res = route_query(state)
        assert res["next_route"] == "none"
        questions_arg = mock_laya.return_value.predict.call_args[0][1]
        none_desc = questions_arg["tool_selection"]["criteria"]["none"]
        assert "uploaded document" in none_desc.lower()

    with patch("core.routing.layer2.graph_nodes.get_laya_agent") as mock_laya:
        bypass = route_query({
            "messages": [HumanMessage(content="what is the weather?")],
            "rag_only": True,
            "active_tools": [{"name": "weather_node", "description": "Weather."}],
        })
        assert bypass == {"next_route": "none"}
        mock_laya.assert_not_called()


@patch("actions.digital.semantic_etl_client.is_semantic_etl_healthy", return_value=True)
@patch("actions.digital.semantic_etl_client.retrieve_document_context")
def test_document_retrieval_node_forwards_custom_namespace(mock_retrieve, mock_healthy):
    mock_retrieve.return_value = {"answer": "", "sources": [{"citation_id": 1}], "has_context": True}
    out = document_retrieval_node({
        "messages": [HumanMessage(content="Who signed the contract?")],
        "rag_only": True,
        "document_namespace": "contracts",
    })
    assert len(out["retrieved_documents"]) == 1
    mock_retrieve.assert_called_once_with("Who signed the contract?", namespace="contracts")


@patch("actions.digital.semantic_etl_client.httpx.Client")
def test_upload_and_job_status_raise_semantic_etl_error_on_failure(mock_client):
    mock_instance = MagicMock()
    req = httpx.Request("POST", "http://localhost:8001/pipeline/jobs/upload")
    resp_500 = httpx.Response(500, json={"detail": "Pinecone down"}, request=req)
    mock_post_resp = MagicMock()
    mock_post_resp.raise_for_status.side_effect = httpx.HTTPStatusError("err", request=req, response=resp_500)
    mock_instance.post.return_value = mock_post_resp
    mock_client.return_value.__enter__.return_value = mock_instance

    try:
        upload_document_bytes(b"hello", "notes.txt")
        assert False, "Expected SemanticETLError on HTTP 500"
    except SemanticETLError as exc:
        assert exc.status_code == 502
        assert "Pinecone down" in exc.detail

    mock_instance.get.side_effect = httpx.ConnectError("Connection refused")
    try:
        get_job_status("job_missing")
        assert False, "Expected SemanticETLError on connection failure"
    except SemanticETLError as exc:
        assert exc.status_code == 503


@patch("actions.digital.semantic_etl_client.httpx.AsyncClient")
def test_async_client_upload_job_and_health(mock_async_client):
    mock_instance = AsyncMock()
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"job_id": "async_job_1", "status": "pending"}
    mock_instance.post.return_value = mock_post_resp

    mock_get_job_resp = MagicMock()
    mock_get_job_resp.json.return_value = {"job_id": "async_job_1", "status": "completed", "progress": 100}
    mock_get_health_resp = MagicMock()
    mock_get_health_resp.status_code = 200
    mock_get_health_resp.json.return_value = {"status": "healthy"}
    mock_instance.get.side_effect = [mock_get_job_resp, mock_get_health_resp]

    mock_async_client.return_value.__aenter__.return_value = mock_instance

    up_res = asyncio.run(async_upload_document_bytes(b"abc", "doc.pdf", content_type="application/pdf"))
    assert up_res["job_id"] == "async_job_1"
    job_res = asyncio.run(async_get_job_status("async_job_1"))
    assert job_res["status"] == "completed"
    health_res = asyncio.run(async_get_health_status())
    assert health_res["status"] == "healthy"


def test_web_api_document_endpoints_validation_and_error_propagation():
    """
    Verifies FastAPI /api/documents/* endpoints:
    1. Reject unsupported extensions (400) and empty files (400).
    2. Propagate upstream SemanticETLError as HTTP 503/404 rather than returning HTTP 200.
    3. Return HTTP 202 with job_id when Semantic ETL accepts the upload.
    """
    from fastapi.testclient import TestClient
    from core.modes.web_api import app

    client = TestClient(app)
    orig_token = os.environ.get("MOKA_ADMIN_TOKEN")
    os.environ["MOKA_ADMIN_TOKEN"] = "test-secret-token"
    headers = {"X-Moka-Token": "test-secret-token"}

    try:
        # 1. Unsupported extension
        bad_ext = client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": ("malware.exe", b"mz", "application/octet-stream")},
        )
        assert bad_ext.status_code == 400

        # 2. Empty file
        empty_resp = client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": ("notes.txt", b"", "text/plain")},
        )
        assert empty_resp.status_code == 400

        # 3. Upstream unreachable -> HTTP 503 (must NOT be 200!)
        with patch(
            "actions.digital.semantic_etl_client.async_upload_document_bytes",
            new=AsyncMock(side_effect=SemanticETLError(503, "Semantic ETL service is unreachable")),
        ):
            offline_resp = client.post(
                "/api/documents/upload",
                headers=headers,
                files={"file": ("srs.pdf", b"%PDF-1.4", "application/pdf")},
            )
            assert offline_resp.status_code == 503
            assert "unreachable" in offline_resp.json()["detail"].lower()

        # 4. Upstream accepts job -> HTTP 202
        with patch(
            "actions.digital.semantic_etl_client.async_upload_document_bytes",
            new=AsyncMock(return_value={"job_id": "job_42", "status": "pending", "progress": 0}),
        ):
            ok_resp = client.post(
                "/api/documents/upload",
                headers=headers,
                files={"file": ("srs.pdf", b"%PDF-1.4", "application/pdf")},
                data={"namespace": "documents"},
            )
            assert ok_resp.status_code == 202
            assert ok_resp.json()["job_id"] == "job_42"

        # 5. Job status 404 propagated instead of HTTP 200
        with patch(
            "actions.digital.semantic_etl_client.async_get_job_status",
            new=AsyncMock(side_effect=SemanticETLError(404, "Job status query failed (404): Not found")),
        ):
            job_404 = client.get("/api/documents/jobs/nonexistent", headers=headers)
            assert job_404.status_code == 404
    finally:
        if orig_token is not None:
            os.environ["MOKA_ADMIN_TOKEN"] = orig_token
        elif "MOKA_ADMIN_TOKEN" in os.environ:
            del os.environ["MOKA_ADMIN_TOKEN"]


def test_post_route_graph_skips_rag_for_tools_and_runs_for_chat():
    """
    Verifies post-route RAG branching:
    - 'none' routes through document_retrieval_node before chat_node.
    - Tool routes skip document_retrieval_node entirely.
    """
    assert decide_next_step({"next_route": "none", "active_tools": []}) == "document_retrieval_node"
    assert decide_next_step({"next_route": "weather_node", "active_tools": [{"name": "weather_node"}]}) == "execute_tool_node"
    assert decide_next_step({
        "next_route": "mcp_pack_github",
        "active_tools": [{"name": "mcp_pack_github", "source_type": "mcp_dormant"}],
    }) == "mcp_discovery_node"


@patch("actions.digital.semantic_etl_client.is_semantic_etl_healthy", return_value=True)
@patch("actions.digital.semantic_etl_client.retrieve_document_context")
def test_document_retrieval_node_contextualizes_followup(mock_retrieve, mock_healthy):
    mock_retrieve.return_value = {"answer": "", "sources": [{"citation_id": 1}], "has_context": True}
    state = {
        "messages": [
            HumanMessage(content="What architecture does the thesis propose?"),
            AIMessage(content="It proposes a dual-layer cognitive router."),
            HumanMessage(content="What about page 4?"),
        ]
    }
    out = document_retrieval_node(state)
    assert len(out["retrieved_documents"]) == 1
    called_query = mock_retrieve.call_args[0][0]
    assert "What architecture does the thesis propose?" in called_query
    assert "What about page 4?" in called_query


@patch("core.routing.layer2.graph_nodes.threading.Thread")
def test_memory_extraction_skips_assistant_rag_turns(mock_thread):
    state = {
        "messages": [
            HumanMessage(content="I am studying computer science. What does page 4 say?"),
            AIMessage(content="Page 4 specifies an 800ms latency requirement [1]."),
        ],
        "retrieved_documents": [{"citation_id": 1, "summary": "Latency"}],
    }
    captured = {}

    def _run_inline(target=None, daemon=False):
        mock_t = MagicMock()
        mock_t.start.side_effect = target
        return mock_t

    mock_thread.side_effect = _run_inline
    with patch("core.routing.layer2.graph_nodes.long_term_memory") as mock_mem:
        mock_mem.add_dialogue.side_effect = lambda turns, user_id=None: captured.setdefault("turns", turns)
        memory_extraction_node(state)

    assert len(captured["turns"]) == 1
    assert captured["turns"][0]["role"] == "user"


def test_voice_speaker_strips_inline_citations():
    from actions.physical.speak import VoiceSpeaker
    speaker = VoiceSpeaker()
    cleaned = speaker._sanitize_text("Latency must be under 800ms [1] and verified [2, 3].")
    assert cleaned == "Latency must be under 800ms and verified."


def test_semantic_etl_launcher_skips_remote_and_disabled():
    import core.services.semantic_etl_launcher as launcher

    with patch.dict(os.environ, {"SEMANTIC_ETL_URL": "http://host.docker.internal:8002", "DISABLE_SEMANTIC_ETL_AUTOSTART": "0", "SEMANTIC_ETL_AUTOSTART": "true"}):
        assert launcher._resolve_local_target() is None
        assert launcher.ensure_semantic_etl_started() is False

    with patch.dict(os.environ, {"SEMANTIC_ETL_URL": "http://localhost:8001", "SEMANTIC_ETL_AUTOSTART": "false", "DISABLE_SEMANTIC_ETL_AUTOSTART": "0"}):
        assert launcher.ensure_semantic_etl_started() is False

    with patch.dict(os.environ, {"SEMANTIC_ETL_URL": "http://localhost:8001", "SEMANTIC_ETL_AUTOSTART": "true", "DISABLE_SEMANTIC_ETL_AUTOSTART": "1"}):
        assert launcher.ensure_semantic_etl_started() is False


def test_semantic_etl_launcher_spawns_once_and_stops_cleanly():
    import tempfile
    from pathlib import Path
    import core.services.semantic_etl_launcher as launcher

    with tempfile.TemporaryDirectory() as tmpdir:
        etl_root = Path(tmpdir)
        (etl_root / "src").mkdir()
        (etl_root / "src" / "main.py").write_text("app = None\n", encoding="utf-8")
        scripts_dir = etl_root / ".venv" / "Scripts"
        scripts_dir.mkdir(parents=True)
        fake_py = scripts_dir / "python.exe"
        fake_py.write_text("", encoding="utf-8")

        fake_proc = MagicMock()
        fake_proc.pid = 43210
        fake_proc.poll.return_value = None

        env_overrides = {
            "SEMANTIC_ETL_URL": "http://localhost:8001",
            "SEMANTIC_ETL_DIR": str(etl_root),
            "SEMANTIC_ETL_AUTOSTART": "true",
            "DISABLE_SEMANTIC_ETL_AUTOSTART": "0",
            "PYTHONPATH": "C:/some/moka/backend",
            "VIRTUAL_ENV": "C:/some/moka/.venv",
        }

        with patch.dict(os.environ, env_overrides):
            with patch.object(launcher, "_is_port_listening", return_value=False), \
                 patch.object(launcher, "_wait_for_service_ready", return_value=True), \
                 patch.object(launcher, "_terminate_process_tree") as mock_kill_tree, \
                 patch("core.services.semantic_etl_launcher.subprocess.Popen", return_value=fake_proc) as mock_popen:
                assert launcher.ensure_semantic_etl_started(wait_ready=True) is True
                # Calling again while process is alive must not spawn a duplicate
                assert launcher.ensure_semantic_etl_started(wait_ready=True) is True
                assert mock_popen.call_count == 1

                spawn_cmd = mock_popen.call_args[0][0]
                spawn_kwargs = mock_popen.call_args[1]
                assert spawn_cmd[0] == str(fake_py)
                assert "--port" in spawn_cmd and "8001" in spawn_cmd
                assert spawn_kwargs["cwd"] == str(etl_root)
                assert "PYTHONPATH" not in spawn_kwargs["env"]
                assert "VIRTUAL_ENV" not in spawn_kwargs["env"]

                launcher.stop_semantic_etl()
                mock_kill_tree.assert_called_once_with(fake_proc)

