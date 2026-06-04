"""Backfill Knowledge Vault embedding state.

Repairs existing ``vault_documents`` rows that are visible in the vault but not
properly represented in ``embeddings``:

1. If embeddings already exist for a row, update ``embedding_count`` and
   ``is_processed``.
2. If no embeddings exist and the stored file is searchable, download it,
   extract text, ingest chunks, and update the vault row.

The script never prints document contents. Run a dry-run first:

    python scripts/backfill_knowledge_vault_embeddings.py --dry-run
    python scripts/backfill_knowledge_vault_embeddings.py --apply
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(message: str) -> None:
    print(message, flush=True)


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("metadata")
    return dict(value) if isinstance(value, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _vector_values(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        return [float(item) for item in value.strip("[]").split(",") if item.strip()]
    return []


def _is_zero_vector(value: Any) -> bool:
    values = _vector_values(value)
    return not values or all(item == 0.0 for item in values)


def _make_query(client: Any, field: str, value: str):
    if field == "source_id":
        return client.table("embeddings").select("id").eq("source_id", value)
    return client.table("embeddings").select("id").filter(field, "eq", value)


def _embedding_ids_for_row(client: Any, row: dict[str, Any]) -> set[str]:
    """Return embedding ids linked to a vault row by any known historical path."""
    ids: set[str] = set()
    doc_id = str(row.get("id") or "")
    file_path = str(row.get("file_path") or "")
    lookups: list[tuple[str, str]] = []
    if file_path:
        lookups.append(("metadata->>file_path", file_path))
    if doc_id:
        lookups.extend(
            [
                ("source_id", doc_id),
                ("metadata->>document_id", doc_id),
                ("metadata->>vault_document_id", doc_id),
            ]
        )

    for field, value in lookups:
        try:
            result = _make_query(client, field, value).execute()
        except Exception:
            continue
        for item in result.data or []:
            if item.get("id"):
                ids.add(str(item["id"]))
    return ids


def _document_type(row: dict[str, Any]) -> str:
    meta = _metadata(row)
    return (
        row.get("category")
        or meta.get("document_type")
        or meta.get("category")
        or "vault_document"
    )


def _build_update_payload(
    row: dict[str, Any],
    *,
    embedding_count: int,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    meta = _metadata(row)
    doc_id = str(row.get("id") or "")
    file_path = row.get("file_path")
    if file_path:
        meta["file_path"] = file_path
    if doc_id:
        meta["document_id"] = doc_id
        meta["vault_document_id"] = doc_id
    meta["processing_status"] = status
    meta["backfilled_at"] = _now_iso()
    if error:
        meta["processing_error"] = error
    else:
        meta.pop("processing_error", None)

    return {
        "is_processed": embedding_count > 0 and status == "completed",
        "embedding_count": embedding_count,
        "metadata": meta,
    }


async def _ingest_row(
    *,
    sync_client: Any,
    async_client: Any,
    row: dict[str, Any],
) -> int:
    from app.rag.ingestion_service import ingest_document
    from app.services.document_text_extraction import extract_text_from_bytes

    doc_id = str(row["id"])
    user_id = str(row["user_id"])
    file_path = str(row["file_path"])
    filename = row.get("filename") or file_path.rsplit("/", 1)[-1]
    mime_type = row.get("file_type")

    file_bytes = sync_client.storage.from_("knowledge-vault").download(file_path)
    content = extract_text_from_bytes(file_bytes, mime_type, filename=filename)
    if not content or not content.strip():
        return 0

    meta = _metadata(row)
    meta.update(
        {
            "file_path": file_path,
            "document_id": doc_id,
            "vault_document_id": doc_id,
            "title": meta.get("title") or filename,
            "backfill_source": "knowledge_vault_embedding_backfill",
        }
    )
    embedding_ids = await ingest_document(
        async_client,
        content,
        source_type=_document_type(row),
        source_id=doc_id,
        metadata=meta,
        user_id=user_id,
        agent_id=row.get("agent_id"),
        chunk_size=500,
        chunk_overlap=50,
    )
    if not embedding_ids:
        return 0

    inserted = (
        sync_client.table("embeddings")
        .select("id, embedding")
        .in_("id", embedding_ids)
        .execute()
        .data
        or []
    )
    zero_ids = [row["id"] for row in inserted if _is_zero_vector(row.get("embedding"))]
    if zero_ids:
        sync_client.table("embeddings").delete().in_("id", embedding_ids).execute()
        raise RuntimeError(
            "Embedding provider returned zero vectors; removed placeholder rows."
        )
    return len(embedding_ids)


def _should_consider(row: dict[str, Any], *, include_unprocessed: bool) -> bool:
    if row.get("is_processed"):
        return True
    return include_unprocessed


async def run(args: argparse.Namespace) -> dict[str, int]:
    _load_dotenv()

    from app.services.document_text_extraction import is_searchable_format
    from app.services.supabase import get_service_client
    from app.services.supabase_client import get_async_client

    sync_client = get_service_client()
    async_client = await get_async_client()

    query = (
        sync_client.table("vault_documents")
        .select(
            "id,user_id,filename,file_path,file_type,category,is_processed,"
            "embedding_count,metadata,created_at"
        )
        .order("created_at", desc=False)
        .limit(args.limit)
    )
    if args.user_id:
        query = query.eq("user_id", args.user_id)
    rows = query.execute().data or []

    stats = {
        "loaded": len(rows),
        "considered": 0,
        "already_ok": 0,
        "counter_repairs": 0,
        "reingested": 0,
        "marked_failed": 0,
        "skipped_not_searchable": 0,
        "skipped_missing_owner_or_path": 0,
        "deferred_max_reingest": 0,
        "errors": 0,
    }
    reingest_attempts = 0

    for row in rows:
        if not _should_consider(row, include_unprocessed=args.include_unprocessed):
            stats["already_ok"] += 1
            continue

        stats["considered"] += 1
        row_id = str(row.get("id"))
        file_path = row.get("file_path")
        user_id = row.get("user_id")
        declared_count = _safe_int(row.get("embedding_count"))
        actual_ids = _embedding_ids_for_row(sync_client, row)
        actual_count = len(actual_ids)

        if actual_count > 0:
            if declared_count != actual_count or not row.get("is_processed"):
                stats["counter_repairs"] += 1
                _log(
                    f"repair-counter id={row_id} filename={row.get('filename')} "
                    f"declared={declared_count} actual={actual_count}"
                )
                if args.apply:
                    payload = _build_update_payload(
                        row,
                        embedding_count=actual_count,
                        status="completed",
                    )
                    (
                        sync_client.table("vault_documents")
                        .update(payload)
                        .eq("id", row_id)
                        .execute()
                    )
            else:
                stats["already_ok"] += 1
            continue

        if not user_id or not file_path:
            stats["skipped_missing_owner_or_path"] += 1
            _log(f"skip-missing-owner-or-path id={row_id}")
            continue

        if not is_searchable_format(row.get("file_type"), row.get("filename")):
            stats["skipped_not_searchable"] += 1
            _log(
                f"skip-not-searchable id={row_id} filename={row.get('filename')} "
                f"type={row.get('file_type')}"
            )
            if args.apply and args.mark_failures:
                payload = _build_update_payload(
                    row,
                    embedding_count=0,
                    status="storage_only",
                )
                sync_client.table("vault_documents").update(payload).eq(
                    "id", row_id
                ).execute()
            continue

        if not args.apply:
            _log(f"reingest id={row_id} filename={row.get('filename')}")
            continue
        if args.max_reingest is not None and reingest_attempts >= args.max_reingest:
            stats["deferred_max_reingest"] += 1
            continue
        reingest_attempts += 1
        _log(f"reingest id={row_id} filename={row.get('filename')}")

        try:
            chunk_count = await _ingest_row(
                sync_client=sync_client,
                async_client=async_client,
                row=row,
            )
            if chunk_count > 0:
                stats["reingested"] += 1
                payload = _build_update_payload(
                    row,
                    embedding_count=chunk_count,
                    status="completed",
                )
            else:
                stats["marked_failed"] += 1
                payload = _build_update_payload(
                    row,
                    embedding_count=0,
                    status="no_extractable_text",
                    error="No extractable text was available for backfill.",
                )
            sync_client.table("vault_documents").update(payload).eq(
                "id", row_id
            ).execute()
        except Exception as exc:
            stats["errors"] += 1
            _log(f"error id={row_id} filename={row.get('filename')} error={exc}")
            if args.mark_failures:
                payload = _build_update_payload(
                    row,
                    embedding_count=0,
                    status="failed",
                    error=str(exc),
                )
                sync_client.table("vault_documents").update(payload).eq(
                    "id", row_id
                ).execute()

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill Knowledge Vault document embeddings and counters."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report work only.")
    mode.add_argument("--apply", action="store_true", help="Write repairs to Supabase.")
    parser.add_argument("--user-id", help="Limit backfill to one user id.")
    parser.add_argument("--limit", type=int, default=1000, help="Max rows to scan.")
    parser.add_argument(
        "--include-unprocessed",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also consider rows marked is_processed=false.",
    )
    parser.add_argument(
        "--mark-failures",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Persist failure/storage-only processing metadata when applying.",
    )
    parser.add_argument(
        "--max-reingest",
        type=int,
        help="Maximum number of missing-embedding rows to re-ingest in this run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats = asyncio.run(run(args))
    _log(f"summary {stats}")
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
