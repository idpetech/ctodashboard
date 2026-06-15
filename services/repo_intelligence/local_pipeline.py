"""Local filesystem ingestion pipeline (no GitHub API)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.repo_intelligence.indexer import (
    build_code_index,
    flatten_snapshot_files,
    summarize_index_eligibility,
)
from services.repo_intelligence.local_source import (
    build_local_snapshot,
    local_content_fetcher_bytes,
    local_content_fetcher_text,
    resolve_local_root,
)
from services.repo_intelligence.metrics_engine import compute_baseline_metrics
from services.repo_intelligence.pipeline import PipelineOptions, PipelineResult, _result_fingerprint

logger = logging.getLogger(__name__)


class LocalPipelineError(Exception):
    """User-visible local pipeline error."""


class LocalRepoIngestionPipeline:
    """
    Walk a local directory → snapshot → code index → baseline metrics.

    Produces the same PipelineResult shape as the GitHub ingest path.
    """

    def run(
        self,
        root_path: str | Path,
        *,
        repo_full_name: Optional[str] = None,
        options: Optional[PipelineOptions] = None,
    ) -> PipelineResult:
        opts = options or PipelineOptions(persist=False)
        if opts.persist:
            raise LocalPipelineError(
                "Local pipeline does not persist to Postgres yet; use --out and run_analysis.py"
            )

        root = resolve_local_root(root_path)
        snapshot = build_local_snapshot(
            root,
            snapshot_id=opts.snapshot_id,
            repo_full_name=repo_full_name,
        )
        snapshot_payload = snapshot.to_dict()
        synced_at = snapshot.repository.last_synced_at

        files = flatten_snapshot_files(snapshot.folder_structure)
        files.sort(key=lambda row: row.get("path") or "")
        eligibility = summarize_index_eligibility(files)

        code_index: List[Dict[str, Any]] = []
        if not opts.skip_index:
            logger.info("Building local code index for %s", root)
            text_fetcher = local_content_fetcher_text(root)
            entries = build_code_index(files, content_fetcher=text_fetcher, indexed_at=synced_at)
            code_index = [entry.to_dict() for entry in entries]

        metrics: Dict[str, Any] = {}
        if not opts.skip_metrics:
            bytes_fetcher = local_content_fetcher_bytes(root)
            metrics = compute_baseline_metrics(
                snapshot_payload,
                computed_at=synced_at,
                content_fetcher=bytes_fetcher,
            ).to_dict()

        fingerprint = _result_fingerprint(
            snapshot=snapshot_payload,
            files=files,
            code_index=code_index,
            metrics=metrics,
        )

        return PipelineResult(
            snapshot_id=snapshot.snapshot_id,
            repository_id="",
            repo_full_name=snapshot.repository.full_name,
            head_commit_sha=snapshot.repository.head_commit_sha,
            file_count=eligibility["total_files"],
            index_eligible=eligibility["index_eligible"],
            indexed_files=len(code_index),
            persisted=False,
            reused_snapshot=False,
            result_fingerprint=fingerprint,
            snapshot=snapshot_payload,
            files=files,
            code_index=code_index,
            metrics=metrics,
        )


def run_local_repo_ingestion(
    root_path: str | Path,
    *,
    repo_full_name: Optional[str] = None,
    options: Optional[PipelineOptions] = None,
) -> PipelineResult:
    return LocalRepoIngestionPipeline().run(
        root_path,
        repo_full_name=repo_full_name,
        options=options,
    )
