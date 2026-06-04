# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Default audio policy for generated videos."""

from __future__ import annotations

import re

_SILENT_AUDIO_RE = re.compile(
    r"("
    r"\b(silent|silence|muted|mute)\b"
    r"|"
    r"\b(no|without|omit|remove|disable)\s+"
    r"(sound|audio|voiceover|voice-over|soundtrack)\b"
    r"|"
    r"\b(sound|audio)\s+(off|muted|disabled)\b"
    r"|"
    r"\bdo\s+not\s+(add|include|use)\s+"
    r"(sound|audio|voiceover|voice-over|soundtrack)\b"
    r")",
    re.IGNORECASE,
)


def prompt_requests_no_sound(prompt: str | None) -> bool:
    """Return True when the user clearly asks for a silent video."""
    return bool(_SILENT_AUDIO_RE.search(str(prompt or "")))


def resolve_include_audio(
    prompt: str | None,
    include_audio: bool | None = None,
) -> bool:
    """Default to audio unless the caller or prompt explicitly disables it."""
    if include_audio is not None:
        return bool(include_audio)
    return not prompt_requests_no_sound(prompt)
