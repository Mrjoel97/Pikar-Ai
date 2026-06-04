import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.routers import voice_session
from app.services import speech_to_text_service


class _FakeContent:
    def __init__(self, *, role=None, parts=None):
        self.role = role
        self.parts = parts or []


class _FakePart:
    def __init__(self, *, text=None):
        self.text = text

    @classmethod
    def from_text(cls, *, text):
        return cls(text=text)


class _FakeConfigObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeServerContent:
    def __init__(
        self,
        *,
        turn_complete=False,
        input_text=None,
        output_text=None,
        waiting_for_input=False,
        generation_complete=False,
    ):
        self.turn_complete = turn_complete
        self.generation_complete = generation_complete
        self.input_transcription = (
            SimpleNamespace(text=input_text) if input_text else None
        )
        self.output_transcription = (
            SimpleNamespace(text=output_text) if output_text else None
        )
        self.model_turn = None
        self.interrupted = False
        self.waiting_for_input = waiting_for_input


class _FakeLiveResponse:
    def __init__(
        self,
        server_content=None,
        *,
        session_resumption_update=None,
        go_away=None,
    ):
        self.server_content = server_content
        self.session_resumption_update = session_resumption_update
        self.go_away = go_away

    def model_dump(self, **_kwargs):
        return {
            "server_content": {
                "turn_complete": bool(
                    self.server_content and self.server_content.turn_complete
                )
            }
        }


def _fake_live_types(**overrides):
    base = {
        "Content": _FakeContent,
        "Part": _FakePart,
        "Blob": _FakeConfigObject,
        "LiveConnectConfig": _FakeConfigObject,
        "AudioTranscriptionConfig": _FakeConfigObject,
        "RealtimeInputConfig": _FakeConfigObject,
        "AutomaticActivityDetection": _FakeConfigObject,
        "SpeechConfig": _FakeConfigObject,
        "VoiceConfig": _FakeConfigObject,
        "PrebuiltVoiceConfig": _FakeConfigObject,
        "ContextWindowCompressionConfig": _FakeConfigObject,
        "SlidingWindow": _FakeConfigObject,
        "SessionResumptionConfig": _FakeConfigObject,
        "StartSensitivity": SimpleNamespace(START_SENSITIVITY_HIGH="high"),
        "EndSensitivity": SimpleNamespace(END_SENSITIVITY_HIGH="high"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_live_config_enables_session_resumption_management(monkeypatch):
    monkeypatch.setattr(voice_session, "DEFAULT_LIVE_VOICE_NAME", "Kore")
    fake_types = _fake_live_types()

    config = voice_session._build_live_connect_config(
        fake_types,
        "stay focused",
        session_resumption_handle="resume-handle-1",
    )

    assert config.response_modalities == ["AUDIO"]
    assert config.system_instruction.parts[0].text == "stay focused"
    assert config.speech_config.voice_config.prebuilt_voice_config.voice_name == "Kore"
    assert isinstance(config.input_audio_transcription, _FakeConfigObject)
    assert isinstance(config.output_audio_transcription, _FakeConfigObject)
    assert (
        config.realtime_input_config.automatic_activity_detection.silence_duration_ms
        == 500
    )
    assert isinstance(config.context_window_compression, _FakeConfigObject)
    assert isinstance(config.context_window_compression.sliding_window, _FakeConfigObject)
    assert config.session_resumption.handle == "resume-handle-1"


@pytest.mark.asyncio
async def test_finalize_returns_after_transcript_save_and_schedules_analysis(
    monkeypatch,
):
    class FakeTable:
        def __init__(self):
            self.updates = []

        def update(self, payload):
            self.updates.append(payload)
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class FakeSupabase:
        def __init__(self):
            self.table_ref = FakeTable()

        def table(self, _name):
            return self.table_ref

    fake_supabase = FakeSupabase()
    scheduled = []

    def fake_start_background_task(coro, *, name):
        scheduled.append((name, coro))

    from app.agents.tools import brain_dump
    from app.services import supabase_client, user_agent_factory

    save_mock = AsyncMock(
        return_value={
            "file_path": "user-1/brain_dump_transcript.md",
            "doc_id": "transcript-doc-1",
        }
    )
    monkeypatch.setattr(voice_session, "_get_http_user_id", lambda _request: "user-1")
    monkeypatch.setattr(
        voice_session,
        "_load_recent_vault_brief",
        AsyncMock(return_value=""),
    )
    monkeypatch.setattr(
        user_agent_factory,
        "get_user_agent_factory",
        lambda: SimpleNamespace(
            get_runtime_personalization=AsyncMock(return_value={})
        ),
    )
    monkeypatch.setattr(brain_dump, "_save_to_vault", save_mock)
    monkeypatch.setattr(supabase_client, "get_service_client", lambda: fake_supabase)
    monkeypatch.setattr(
        voice_session,
        "_start_background_task",
        fake_start_background_task,
    )

    response = await voice_session.finalize_brainstorm_session.__wrapped__(
        SimpleNamespace(headers={}),
        voice_session.BrainstormFinalizeRequest(
            session_id="brainstorm-123",
            turns=[
                voice_session.TranscriptTurn(
                    speaker="user",
                    text="I want to build a cafe app",
                    ts_ms=1,
                ),
                voice_session.TranscriptTurn(
                    speaker="agent",
                    text="What problem does it solve?",
                    ts_ms=2,
                ),
            ],
        ),
    )

    assert response.success is True
    assert response.analysis_pending is True
    assert response.transcript_doc_id == "transcript-doc-1"
    assert response.analysis_doc_id is None
    assert response.analysis_markdown is None
    assert scheduled and scheduled[0][0] == "brainstorm-analysis:brainstorm-123"
    assert fake_supabase.table_ref.updates[0]["transcript_doc_id"] == "transcript-doc-1"
    assert save_mock.await_args.kwargs["ingest"] is False

    # The test replaces the scheduler, so close the created coroutine explicitly.
    scheduled[0][1].close()


def test_live_lifecycle_extractors_accept_go_away_generation_complete_and_resumption():
    snake_response = SimpleNamespace(
        session_resumption_update=SimpleNamespace(
            resumable=True,
            new_handle="snake-handle",
        ),
        go_away=SimpleNamespace(time_left=SimpleNamespace(seconds=11, nanos=1)),
        server_content=SimpleNamespace(generation_complete=True),
    )
    camel_response = SimpleNamespace(
        sessionResumptionUpdate=SimpleNamespace(
            resumable=True,
            newHandle="camel-handle",
        ),
        goAway=SimpleNamespace(timeLeft=9),
        serverContent=SimpleNamespace(generationComplete=True),
    )

    assert voice_session._extract_live_resumption_handle(snake_response) == "snake-handle"
    assert voice_session._extract_live_go_away_seconds(snake_response) == (True, 12)
    assert voice_session._response_generation_complete(snake_response) is True

    assert voice_session._extract_live_resumption_handle(camel_response) == "camel-handle"
    assert voice_session._extract_live_go_away_seconds(camel_response) == (True, 9)
    assert voice_session._response_generation_complete(camel_response) is True


@pytest.mark.asyncio
async def test_live_server_message_stream_continues_after_turn_complete():
    """Gemini Live receive() returns per turn; the router must keep listening."""

    class FakeLiveSession:
        def __init__(self):
            self.receive_calls = 0

        async def receive(self):
            self.receive_calls += 1
            yield _FakeLiveResponse(
                _FakeServerContent(
                    turn_complete=True,
                    output_text=f"turn {self.receive_calls}",
                )
            )

    fake_session = FakeLiveSession()
    stop_event = voice_session.asyncio.Event()
    seen = []

    async for response in voice_session._live_server_message_stream(
        fake_session,
        stop_event,
    ):
        seen.append(response.server_content.output_transcription.text)
        if len(seen) == 2:
            stop_event.set()

    assert seen == ["turn 1", "turn 2"]
    assert fake_session.receive_calls == 2


@pytest.mark.asyncio
async def test_voice_session_reads_second_live_turn_and_persists_user_transcript(
    monkeypatch,
):
    """Regression: after intro turn_complete, keep reading later user turns."""

    class FakeWebSocket:
        def __init__(self):
            self.sent = []
            self.closed = False
            self._messages = [
                json.dumps({"type": "auth", "token": "token"}),
                json.dumps({"type": "audio", "data": "AAAA"}),
                json.dumps({"type": "end"}),
            ]

        async def accept(self):
            return None

        async def receive_text(self):
            msg = self._messages.pop(0)
            if json.loads(msg).get("type") == "end":
                await voice_session.asyncio.sleep(0.05)
            return msg

        async def send_json(self, payload):
            self.sent.append(payload)

        async def close(self, *args, **kwargs):
            self.closed = True

    class FakeLiveSession:
        def __init__(self):
            self.receive_calls = 0
            self.send_client_content = AsyncMock()
            self.send_realtime_input = AsyncMock()

        async def receive(self):
            self.receive_calls += 1
            if self.receive_calls == 1:
                yield _FakeLiveResponse(
                    session_resumption_update=SimpleNamespace(
                        resumable=True,
                        new_handle="session-handle-1",
                    )
                )
                yield _FakeLiveResponse(
                    go_away=SimpleNamespace(
                        time_left=SimpleNamespace(seconds=30, nanos=0)
                    )
                )
                yield _FakeLiveResponse(
                    _FakeServerContent(generation_complete=True)
                )
                yield _FakeLiveResponse(
                    _FakeServerContent(
                        turn_complete=True,
                        output_text="What should we unpack first?",
                        waiting_for_input=True,
                    )
                )
            elif self.receive_calls == 2:
                yield _FakeLiveResponse(
                    _FakeServerContent(generation_complete=True)
                )
                yield _FakeLiveResponse(
                    _FakeServerContent(input_text="I want to build a cafe app")
                )
                yield _FakeLiveResponse(
                    _FakeServerContent(
                        turn_complete=True,
                        output_text="What problem does the cafe app solve?",
                    )
                )
            else:
                await voice_session.asyncio.sleep(60)

    class FakeLiveConnect:
        def __init__(self, session):
            self.session = session

        def connect(self, **_kwargs):
            return self

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, *_args):
            return None

    class FakeTable:
        def __init__(self, updates):
            self.updates = updates
            self._mode = "insert"

        def insert(self, _payload):
            self._mode = "insert"
            return self

        def update(self, payload):
            self._mode = "update"
            self.updates.append(payload)
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            if self._mode == "insert":
                return SimpleNamespace(data=[{"id": "db-session-id"}])
            return SimpleNamespace(data=[])

    class FakeSupabase:
        def __init__(self):
            self.updates = []

        def table(self, _name):
            return FakeTable(self.updates)

    fake_live_session = FakeLiveSession()
    fake_supabase = FakeSupabase()
    fake_types = SimpleNamespace(
        Content=_FakeContent,
        Part=_FakePart,
        Blob=_FakeConfigObject,
        LiveConnectConfig=_FakeConfigObject,
        AudioTranscriptionConfig=_FakeConfigObject,
        RealtimeInputConfig=_FakeConfigObject,
        AutomaticActivityDetection=_FakeConfigObject,
        SpeechConfig=_FakeConfigObject,
        VoiceConfig=_FakeConfigObject,
        PrebuiltVoiceConfig=_FakeConfigObject,
        StartSensitivity=SimpleNamespace(START_SENSITIVITY_HIGH="high"),
        EndSensitivity=SimpleNamespace(END_SENSITIVITY_HIGH="high"),
    )

    monkeypatch.setattr(
        voice_session, "_authenticate", AsyncMock(return_value="user-1")
    )
    monkeypatch.setattr(sys.modules["google.genai"], "types", fake_types, raising=False)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)
    monkeypatch.setattr(
        voice_session,
        "_load_recent_vault_brief",
        AsyncMock(return_value=""),
    )
    monkeypatch.setattr(
        voice_session,
        "_load_recent_braindump_context",
        AsyncMock(return_value=""),
    )
    monkeypatch.setattr(
        voice_session,
        "_get_genai_client",
        lambda: SimpleNamespace(
            aio=SimpleNamespace(live=FakeLiveConnect(fake_live_session))
        ),
    )

    from app.agents.tools import brain_dump
    from app.services import supabase_client

    monkeypatch.setattr(
        brain_dump,
        "_save_to_vault",
        AsyncMock(return_value={"file_path": "path.md", "doc_id": "doc-1"}),
    )
    monkeypatch.setattr(
        supabase_client,
        "get_service_client",
        lambda: fake_supabase,
    )

    websocket = FakeWebSocket()
    await voice_session.voice_session(websocket, "brainstorm-123")

    assert fake_live_session.receive_calls >= 2
    assert {
        "type": "user_transcript",
        "text": "I want to build a cafe app",
        "source": "gemini-live",
    } in websocket.sent
    assert {
        "type": "live_reconnecting",
        "reason": "go_away",
        "remaining_seconds": 30,
    } in websocket.sent
    assert {"type": "generation_complete"} in websocket.sent
    assert any(
        update.get("transcript_doc_id") == "doc-1" for update in fake_supabase.updates
    )
    assert any(update.get("turn_count", 0) >= 1 for update in fake_supabase.updates), (
        fake_supabase.updates
    )


@pytest.mark.asyncio
async def test_relay_user_turn_from_audio_emits_transcript_and_prompts_live_session(
    monkeypatch,
):
    monkeypatch.setattr(voice_session, "VOICE_STT_FALLBACK_ENABLED", True)
    monkeypatch.setattr(
        speech_to_text_service,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "success": True,
            "transcript": "I want to help restaurants retain customers",
            "confidence": 0.94,
            "error": None,
        },
    )
    fake_types = SimpleNamespace(Content=_FakeContent, Part=_FakePart)
    monkeypatch.setattr(sys.modules["google.genai"], "types", fake_types, raising=False)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

    websocket = AsyncMock()
    live_session = SimpleNamespace(
        send_client_content=AsyncMock(),
        send=AsyncMock(),
    )

    transcript = await voice_session._relay_user_turn_from_audio(
        audio_bytes=b"pcm-audio",
        websocket=websocket,
        live_session=live_session,
        session_id="brainstorm-123",
        reason="audio_stream_end",
    )

    assert transcript == "I want to help restaurants retain customers"
    websocket.send_json.assert_awaited_once_with(
        {
            "type": "user_transcript",
            "text": "I want to help restaurants retain customers",
            "source": "google-stt",
        }
    )
    live_session.send_client_content.assert_awaited_once()
    live_session.send.assert_not_awaited()
    call = live_session.send_client_content.await_args
    assert call.kwargs["turn_complete"] is True
    turns = call.kwargs["turns"]
    assert getattr(turns, "role", None) == "user"
    assert turns.parts[0].text == "I want to help restaurants retain customers"


@pytest.mark.asyncio
async def test_relay_user_turn_from_audio_skips_empty_transcript(monkeypatch):
    monkeypatch.setattr(voice_session, "VOICE_STT_FALLBACK_ENABLED", True)
    monkeypatch.setattr(
        speech_to_text_service,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "success": False,
            "transcript": None,
            "confidence": None,
            "error": "No speech detected",
        },
    )

    websocket = AsyncMock()
    live_session = SimpleNamespace(
        send_client_content=AsyncMock(),
        send=AsyncMock(),
    )

    transcript = await voice_session._relay_user_turn_from_audio(
        audio_bytes=b"pcm-audio",
        websocket=websocket,
        live_session=live_session,
        session_id="brainstorm-123",
        reason="audio_stream_end",
    )

    assert transcript is None
    websocket.send_json.assert_not_awaited()
    live_session.send_client_content.assert_not_awaited()
    live_session.send.assert_not_awaited()


def test_format_transcript_markdown_includes_session_metadata():
    markdown = voice_session._format_transcript_markdown(
        session_id="brainstorm-123",
        turns=[
            {
                "speaker": "user",
                "text": "I want to build something for creators",
                "ts_ms": 1_000,
            },
            {
                "speaker": "agent",
                "text": "What part feels most urgent?",
                "ts_ms": 5_000,
            },
        ],
    )

    assert "# Brain Dump Discussion Transcript" in markdown
    assert "| **Session ID** | `brainstorm-123` |" in markdown
    assert "| **Turns** | 2 |" in markdown
    assert "## Conversation" in markdown
    assert "I want to build something for creators" in markdown
    assert "What part feels most urgent?" in markdown


def test_build_live_greeting_prompt_continues_after_refresh_without_reintroducing():
    prompt = voice_session._build_live_greeting_prompt(
        agent_display_name="Pikar AI",
        personalization_context="",
        recent_vault_brief="",
        recent_braindump_context="",
        resume_transcript="USER: I want to help salons get more repeat bookings.\nAGENT: What part feels stuck right now?",
        start_mode="resume",
    )

    assert "Continue the live brainstorm as Pikar AI." in prompt
    assert "Do not introduce yourself again." in prompt
    assert "The browser refreshed mid-session." in prompt
    assert "help salons get more repeat bookings" in prompt
    assert "Introduce yourself as Pikar AI." not in prompt


def test_build_live_voice_instruction_prefers_continuation_when_resume_transcript_exists():
    instruction = voice_session._build_live_voice_instruction(
        agent_display_name="Pikar AI",
        personalization_context="",
        recent_vault_brief="",
        recent_braindump_context="",
        resume_transcript="USER: I am refining the value proposition.\nAGENT: Which segment feels most urgent?",
        start_mode="resume",
    )

    assert "without re-introducing yourself" in instruction
    assert (
        "Continue this exact brainstorm without re-introducing yourself" in instruction
    )
    assert "I am refining the value proposition" in instruction


def test_build_live_response_modalities_uses_audio_only_when_transcriptions_are_enabled():
    modalities = voice_session._build_live_response_modalities()

    assert modalities == ["AUDIO"]


def test_build_live_response_modalities_stays_audio_only_when_transcriptions_are_off():
    modalities = voice_session._build_live_response_modalities(
        include_transcriptions=False
    )

    assert modalities == ["AUDIO"]
