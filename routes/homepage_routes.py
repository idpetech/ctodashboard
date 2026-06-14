"""
Homepage Routes
Handles homepage display and optional admin interface for content management
"""

import os
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from services.homepage_service import homepage_service

homepage_bp = Blueprint("homepage", __name__)

# Admin interface feature flag
ENABLE_HOMEPAGE_ADMIN = os.getenv("ENABLE_HOMEPAGE_ADMIN", "false").lower() == "true"


@homepage_bp.route("/")
def homepage():
    """Main homepage route"""
    try:
        content = homepage_service.get_content()
        now = datetime.now()
        briefing_date = f"{now.strftime('%B')} {now.day}, {now.year}"
        return render_template(
            "homepage.html",
            content=content,
            briefing_date=briefing_date,
        )
    except Exception:
        # Fallback content if configuration fails
        fallback_content = {
            "hero": {
                "headline": "Know the health of your startup in",
                "headline_emphasis": "5 minutes.",
                "subheadline": "Connect GitHub, AWS, Jira, OpenAI, and Railway. CTOLens pulls signals into one Overview briefing.",
                "cta_text": "Start Free Assessment",
                "cta_link": "/dashboard?signup=1",
                "cta_secondary_text": "See Sample Report",
                "cta_secondary_link": "#sample",
                "cta_primary_hint": "No credit card required",
                "trust_items": [
                    "Setup in minutes",
                    "Read-only access",
                    "No code stored",
                    "Cancel anytime",
                ],
                "social_proof": {
                    "text": "Built for founders and fractional CTOs",
                    "avatars": [],
                },
                "preview_items": [],
            },
            "problem": {
                "headline": "Current tools show data.",
                "subheadline": "CTO Lens shows what needs attention.",
                "challenges": [
                    {
                        "icon": "scatter",
                        "title": "Too many tools",
                        "description": "Scattered platforms",
                    },
                    {
                        "icon": "view",
                        "title": "No single view",
                        "description": "Missing connections",
                    },
                    {
                        "icon": "warning",
                        "title": "Hidden risks",
                        "description": "Problems surface late",
                    },
                ],
            },
            "solution": {
                "title": "Attention Engine",
                "description": "AI-powered system for your development pipeline",
                "workflow": [
                    {"name": "Your Tools", "description": "Connect services", "icon_type": "tools"},
                    {"name": "AI Engine", "description": "Analyze patterns", "icon_type": "engine"},
                    {"name": "Daily Brief", "description": "Get insights", "icon_type": "brief"},
                ],
            },
            "features": {
                "title": "Complete CTO Intelligence",
                "subtitle": "Connect your tech stack",
                "feature_list": [
                    {
                        "icon": "github",
                        "title": "GitHub Insights",
                        "description": "Code velocity",
                        "details": ["Repository health"],
                    },
                    {
                        "icon": "jira",
                        "title": "Jira Insights",
                        "description": "Sprint health",
                        "details": ["Issue tracking"],
                    },
                    {
                        "icon": "aws",
                        "title": "AWS Insights",
                        "description": "Uptime tracking",
                        "details": ["Error monitoring"],
                    },
                    {
                        "icon": "strategic",
                        "title": "Strategic Tracking",
                        "description": "Business KPIs",
                        "details": ["Cost optimization"],
                    },
                ],
            },
            "daily_brief": {
                "title": "Daily Briefing",
                "subtitle": "Essential insights",
                "date": "Today",
                "brief_items": [
                    {
                        "icon": "📊",
                        "level": "info",
                        "title": "System Status",
                        "description": "All systems operational",
                    }
                ],
                "cta": {"text": "View Dashboard", "link": "/dashboard"},
            },
            "pricing": {
                "title": "Simple pricing. Start free.",
                "subtitle": "Try the full Overview experience free for 7 days. No credit card required.",
                "footnote": "7-day free trial on all plans · Cancel anytime",
                "plans": [
                    {
                        "name": "Free Trial",
                        "tier": "Free Trial",
                        "price": "Free",
                        "price_type": "free",
                        "period": "",
                        "description": "7 days of Starter access. Connect tools and see your real Overview briefing.",
                        "features": [
                            "Overview health score & needs-attention alerts",
                            "GitHub, AWS, Jira, OpenAI, and Railway connectors",
                        ],
                        "cta": {
                            "text": "Start Free Assessment",
                            "link": "/dashboard?signup=1",
                            "style": "ghost",
                        },
                    },
                    {
                        "name": "Starter",
                        "tier": "Starter",
                        "price": "49",
                        "period": "/month",
                        "description": "For founders and in-house engineering leads.",
                        "popular": True,
                        "features": [
                            "Unlimited assignments & tool connections",
                            "Overview health score & attention alerts",
                            "Daily briefing with prioritized actions",
                        ],
                        "cta": {
                            "text": "Start Free Assessment",
                            "link": "/dashboard?signup=1&plan=starter",
                            "style": "solid",
                        },
                    },
                    {
                        "name": "Professional",
                        "tier": "Professional",
                        "price": "149",
                        "period": "/month",
                        "description": "For fractional CTOs managing multiple client portfolios.",
                        "features": [
                            "Multiple client portfolios",
                            "Per-portfolio health score & Overview briefing",
                        ],
                        "cta": {
                            "text": "Start Free Assessment",
                            "link": "/dashboard?signup=1&plan=professional",
                            "style": "outline",
                        },
                    },
                ],
            },
            "final_cta": {
                "headline": "See what needs your attention in one Overview.",
                "subheadline": "Connect your tools, set up assignments, and get your health score and briefing — free for 7 days.",
                "primary_hint": "No credit card required",
            },
            "footer": {
                "tagline": "CTO Lens by IdepTech",
                "company_url": "http://idpetech.com",
                "sections": [],
                "social_links": [],
                "copyright": "© 2026 idpetech.com All rights reserved.",
            },
        }
        now = datetime.now()
        briefing_date = f"{now.strftime('%B')} {now.day}, {now.year}"
        return render_template(
            "homepage.html",
            content=fallback_content,
            briefing_date=briefing_date,
        )


@homepage_bp.route("/admin/homepage")
def homepage_admin():
    """Homepage admin interface (only if enabled)"""
    if not ENABLE_HOMEPAGE_ADMIN:
        return "Homepage admin interface is disabled", 404

    # Simple auth check - you might want to integrate with existing auth
    if not session.get("is_admin"):
        return redirect(url_for("homepage.admin_login"))

    try:
        content = homepage_service.get_content()
        sections = homepage_service.get_editable_sections()
        return render_template("homepage_admin.html", content=content, sections=sections)
    except Exception as e:
        flash(f"Error loading homepage content: {e}", "error")
        return redirect(url_for("homepage.homepage"))


@homepage_bp.route("/admin/homepage/login", methods=["GET", "POST"])
def admin_login():
    """Simple admin login (only if admin interface enabled)"""
    if not ENABLE_HOMEPAGE_ADMIN:
        return "Homepage admin interface is disabled", 404

    if request.method == "POST":
        # Simple password check - replace with proper auth
        admin_password = os.getenv("HOMEPAGE_ADMIN_PASSWORD", "admin123")
        if request.form.get("password") == admin_password:
            session["is_admin"] = True
            return redirect(url_for("homepage.homepage_admin"))
        else:
            flash("Invalid password", "error")

    return render_template("admin_login.html")


@homepage_bp.route("/admin/homepage/logout")
def admin_logout():
    """Admin logout"""
    if not ENABLE_HOMEPAGE_ADMIN:
        return "Homepage admin interface is disabled", 404

    session.pop("is_admin", None)
    return redirect(url_for("homepage.homepage"))


# Login and register functionality is handled in /dashboard
# No separate routes needed as forms are embedded in dashboard.html


@homepage_bp.route("/admin/homepage/api/content", methods=["GET"])
def get_content_api():
    """API endpoint to get homepage content"""
    if not ENABLE_HOMEPAGE_ADMIN or not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        content = homepage_service.get_content(use_cache=False)
        return jsonify(content)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@homepage_bp.route("/admin/homepage/api/content/<section>", methods=["GET", "PUT"])
def section_api(section):
    """API endpoint to get/update specific section"""
    if not ENABLE_HOMEPAGE_ADMIN or not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        if request.method == "GET":
            section_content = homepage_service.get_section(section)
            if section_content is None:
                return jsonify({"error": "Section not found"}), 404
            return jsonify(section_content)

        elif request.method == "PUT":
            new_content = request.get_json()
            if not new_content:
                return jsonify({"error": "No content provided"}), 400

            success = homepage_service.update_section(section, new_content)
            if success:
                return jsonify(
                    {"success": True, "message": f"Section '{section}' updated successfully"}
                )
            else:
                return jsonify({"error": "Failed to update section"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@homepage_bp.route("/admin/homepage/api/content", methods=["PUT"])
def update_content_api():
    """API endpoint to update entire homepage content"""
    if not ENABLE_HOMEPAGE_ADMIN or not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        new_content = request.get_json()
        if not new_content:
            return jsonify({"error": "No content provided"}), 400

        success = homepage_service.update_content(new_content)
        if success:
            return jsonify({"success": True, "message": "Homepage content updated successfully"})
        else:
            return jsonify({"error": "Failed to update content"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@homepage_bp.route("/admin/homepage/api/sections")
def get_sections_api():
    """API endpoint to get editable sections info"""
    if not ENABLE_HOMEPAGE_ADMIN or not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    sections = homepage_service.get_editable_sections()
    return jsonify(sections)


# Context processor to make admin status available in templates
@homepage_bp.context_processor
def inject_admin_status():
    return {
        "homepage_admin_enabled": ENABLE_HOMEPAGE_ADMIN,
        "is_homepage_admin": session.get("is_admin", False),
    }
