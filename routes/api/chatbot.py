"""Chatbot API routes."""

from flask import jsonify, request

from routes.api.deps import logger
from services.chatbot_service import (
    clear_conversation_history,
    get_conversation_history,
    process_question,
    process_question_stream,
    process_question_stream_with_workspace,
)


def register_chatbot_routes(app):
    """Register chatbot routes."""

    @app.route("/api/chatbot/ask-stream", methods=["POST"])
    def ask_chatbot_stream():
        """AI-powered chatbot with streaming response and workspace context"""
        try:
            data = request.get_json()
            question = data.get("question", "")
            user_id = data.get("user_id", "default")
            workspace_id = data.get("workspace_id")
            assignment_id = data.get("assignment_id")
            fetch_metrics = bool(data.get("fetch_metrics", False))
            skip_metrics_fetch = bool(data.get("skip_metrics_fetch", False))

            if not question:
                return jsonify({"error": "No question provided"}), 400

            from flask import Response

            if workspace_id:
                stream_gen = process_question_stream_with_workspace(
                    question,
                    user_id,
                    workspace_id,
                    assignment_id,
                    fetch_metrics=fetch_metrics,
                    skip_metrics_fetch=skip_metrics_fetch,
                )
            else:
                stream_gen = process_question_stream(question, user_id)

            return Response(
                stream_gen,
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/ask", methods=["POST"])
    def ask_chatbot():
        """AI-powered chatbot endpoint with workspace context"""
        try:
            data = request.get_json()
            question = data.get("question", "")
            user_id = data.get("user_id", "default")
            workspace_id = data.get("workspace_id")
            assignment_id = data.get("assignment_id")
            fetch_metrics = bool(data.get("fetch_metrics", False))
            skip_metrics_fetch = bool(data.get("skip_metrics_fetch", False))

            logger.info(
                "Chatbot request received",
                extra={
                    "question": question,
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                    "assignment_id": assignment_id,
                    "fetch_metrics": fetch_metrics,
                    "has_workspace": bool(workspace_id),
                    "has_assignment": bool(assignment_id),
                },
            )

            if not question:
                return jsonify({"error": "No question provided"}), 400

            if workspace_id:
                from services.chatbot_service import process_question_with_workspace

                result = process_question_with_workspace(
                    question,
                    user_id,
                    workspace_id,
                    assignment_id,
                    fetch_metrics=fetch_metrics,
                    skip_metrics_fetch=skip_metrics_fetch,
                )
            else:
                result = process_question(question, user_id)

            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/history")
    def get_chatbot_history():
        """Get chatbot conversation history"""
        try:
            user_id = request.args.get("user_id", "default")
            limit = int(request.args.get("limit", 20))
            history = get_conversation_history(user_id, limit)
            return jsonify({"history": history})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chatbot/clear", methods=["POST"])
    def clear_chatbot_history():
        """Clear chatbot conversation history"""
        try:
            data = request.get_json() or {}
            user_id = data.get("user_id", "default")
            clear_conversation_history(user_id)
            return jsonify({"message": "History cleared", "success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
