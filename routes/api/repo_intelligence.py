"""Repo intelligence API — repository snapshot capture and retrieval."""

from flask import jsonify, request

from routes.api.deps import get_require_workspace_access, get_workspace_service


def register_repo_intelligence_routes(app):
    """Register repo intelligence routes (feature-flagged)."""

    @app.route(
        "/api/workspaces/<workspace_id>/assignments/<assignment_id>/repo-intelligence/snapshots",
        methods=["GET", "POST"],
    )
    @get_require_workspace_access()
    def repo_intelligence_snapshots(workspace_id, assignment_id):
        from services.repo_intelligence.config import is_repo_intelligence_enabled
        from services.repo_intelligence.snapshot_service import (
            RepoSnapshotError,
            create_repo_snapshot,
            list_snapshots,
        )

        if not is_repo_intelligence_enabled():
            return jsonify({"error": "Repo intelligence is disabled"}), 403

        assignment = get_workspace_service().get_assignment(workspace_id, assignment_id)
        if not assignment:
            return jsonify({"error": "Assignment not found"}), 404

        if request.method == "GET":
            limit = request.args.get("limit", 20, type=int)
            limit = max(1, min(limit, 100))
            snapshots = list_snapshots(workspace_id, assignment_id, limit=limit)
            return jsonify({"snapshots": snapshots, "count": len(snapshots)})

        body = request.get_json(silent=True) or {}
        repo = (body.get("repo") or body.get("repo_url") or "").strip() or None

        try:
            result = create_repo_snapshot(
                workspace_id,
                assignment_id,
                assignment,
                repo_input=repo,
            )
            return jsonify(result), 201
        except RepoSnapshotError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route(
        "/api/workspaces/<workspace_id>/repo-intelligence/snapshots/<snapshot_id>",
        methods=["GET"],
    )
    @get_require_workspace_access()
    def repo_intelligence_snapshot_detail(workspace_id, snapshot_id):
        from services.repo_intelligence.config import is_repo_intelligence_enabled
        from services.repo_intelligence.snapshot_service import get_snapshot

        if not is_repo_intelligence_enabled():
            return jsonify({"error": "Repo intelligence is disabled"}), 403

        record = get_snapshot(workspace_id, snapshot_id)
        if not record:
            return jsonify({"error": "Snapshot not found"}), 404
        return jsonify(record)

    @app.route(
        "/api/workspaces/<workspace_id>/repo-intelligence/snapshots/<snapshot_id>/files",
        methods=["GET"],
    )
    @get_require_workspace_access()
    def repo_intelligence_snapshot_files(workspace_id, snapshot_id):
        from services.repo_intelligence.config import is_repo_intelligence_enabled
        from services.repo_intelligence.snapshot_service import get_snapshot, list_file_index

        if not is_repo_intelligence_enabled():
            return jsonify({"error": "Repo intelligence is disabled"}), 403

        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        limit = max(1, min(limit, 500))
        offset = max(0, offset)

        payload = list_file_index(
            workspace_id,
            snapshot_id,
            limit=limit,
            offset=offset,
        )
        if not payload.get("total") and not get_snapshot(workspace_id, snapshot_id):
            return jsonify({"error": "Snapshot not found"}), 404
        return jsonify(payload)

    @app.route(
        "/api/workspaces/<workspace_id>/repo-intelligence/snapshots/<snapshot_id>/code-index",
        methods=["GET", "POST"],
    )
    @get_require_workspace_access()
    def repo_intelligence_code_index(workspace_id, snapshot_id):
        from services.assignment_metrics_config import (
            connector_credentials_ready,
            missing_connector_message,
        )
        from services.auth.credential_service import CredentialService
        from services.repo_intelligence.code_index_store import get_code_index_store
        from services.repo_intelligence.config import is_repo_intelligence_enabled
        from services.repo_intelligence.indexer import CodeIndexError, build_and_store_code_index
        from services.repo_intelligence.store import get_store

        if not is_repo_intelligence_enabled():
            return jsonify({"error": "Repo intelligence is disabled"}), 403

        record = get_store().get_snapshot(snapshot_id)
        if not record or record.get("workspace_id") != workspace_id:
            return jsonify({"error": "Snapshot not found"}), 404

        if request.method == "GET":
            limit = request.args.get("limit", 500, type=int)
            offset = request.args.get("offset", 0, type=int)
            file_path = (request.args.get("path") or "").strip()
            limit = max(1, min(limit, 2000))
            offset = max(0, offset)

            store = get_code_index_store()
            if file_path:
                entry = store.get_index_entry(snapshot_id, file_path)
                if not entry:
                    return jsonify({"error": "Code index entry not found"}), 404
                return jsonify(entry)

            entries = store.list_index_entries(snapshot_id, limit=limit, offset=offset)
            total = store.count_index_entries(snapshot_id)
            return jsonify(
                {"snapshot_id": snapshot_id, "entries": entries, "total": total, "limit": limit, "offset": offset}
            )

        assignment_id = record.get("assignment_id")
        if not assignment_id or not connector_credentials_ready(workspace_id, assignment_id, "github"):
            return jsonify({"error": missing_connector_message("github")}), 400

        creds = CredentialService().get_github_credentials(workspace_id, assignment_id)
        token = creds.get("token")
        if not token:
            return jsonify({"error": missing_connector_message("github")}), 400

        try:
            result = build_and_store_code_index(snapshot_id, workspace_id, token=token)
            return jsonify({"success": True, **result}), 201
        except CodeIndexError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.route(
        "/api/workspaces/<workspace_id>/repo-intelligence/snapshots/<snapshot_id>/baseline-metrics",
        methods=["GET", "POST"],
    )
    @get_require_workspace_access()
    def repo_intelligence_baseline_metrics(workspace_id, snapshot_id):
        from services.repo_intelligence.config import is_repo_intelligence_enabled
        from services.repo_intelligence.metrics_engine import (
            BaselineMetricsError,
            build_and_store_baseline_metrics,
        )
        from services.repo_intelligence.metrics_store import get_metrics_store
        from services.repo_intelligence.store import get_store

        if not is_repo_intelligence_enabled():
            return jsonify({"error": "Repo intelligence is disabled"}), 403

        record = get_store().get_snapshot(snapshot_id)
        if not record or record.get("workspace_id") != workspace_id:
            return jsonify({"error": "Snapshot not found"}), 404

        if request.method == "GET":
            metrics = get_metrics_store().get_metrics(snapshot_id)
            if not metrics:
                return jsonify({"error": "Baseline metrics not found"}), 404
            return jsonify(metrics)

        try:
            metrics = build_and_store_baseline_metrics(snapshot_id, workspace_id)
            return jsonify({"success": True, "metrics": metrics}), 201
        except BaselineMetricsError as exc:
            return jsonify({"error": str(exc)}), 400
