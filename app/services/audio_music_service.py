# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Background music selector for generated video pipelines."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILTIN_BGM_PATH = REPO_ROOT / "frontend" / "public" / "audio" / "bg-ambient.mp3"


def select_background_music_url(
    mood: str | None,
    *,
    include_builtin_default: bool = True,
) -> str | None:
    mood_key = (mood or "neutral").strip().lower().replace(" ", "_")
    exact_key = f"DIRECTOR_BGM_URL_{mood_key.upper()}"
    if os.getenv(exact_key):
        return os.getenv(exact_key)

    # Fallback categories
    if "upbeat" in mood_key and os.getenv("DIRECTOR_BGM_URL_UPBEAT"):
        return os.getenv("DIRECTOR_BGM_URL_UPBEAT")
    if ("calm" in mood_key or "ambient" in mood_key) and os.getenv(
        "DIRECTOR_BGM_URL_CALM"
    ):
        return os.getenv("DIRECTOR_BGM_URL_CALM")

    if os.getenv("DIRECTOR_BGM_URL_DEFAULT"):
        return os.getenv("DIRECTOR_BGM_URL_DEFAULT")

    if include_builtin_default and BUILTIN_BGM_PATH.is_file():
        return str(BUILTIN_BGM_PATH)

    return None
