
@app.route("/api/services/status")
def get_services_status():
    """Get status of all services"""
    return jsonify({
        "service_manager": {
            "enabled_services": list(service_manager.services.keys()),
            "total_services": len(service_manager.services)
        },
        "feature_flags": FEATURE_FLAGS,
        "status": "read_only"
    })

@app.route("/api/workstreams", methods=["GET", "POST"])
def workstreams_endpoint():
    """Workstream management endpoint (disabled by default)"""
    if request.method == "GET":
        workstream_service = service_manager.get_service("workstream")
        if not workstream_service:
            return jsonify({"error": "Workstream management disabled", "enabled": False})
        
        return jsonify({
            "workstreams": workstream_service.get_workstreams(),
            "enabled": True
        })
    
    elif request.method == "POST":
        workstream_service = service_manager.get_service("workstream")
        if not workstream_service:
            return jsonify({"error": "Workstream management disabled", "enabled": False})
        
        data = request.get_json()
        result = workstream_service.create_workstream(
            data.get("name", ""),
            data.get("config", {})
        )
        return jsonify(result)

@app.route("/api/service-configs", methods=["GET", "POST"])
def service_configs_endpoint():
    """Service configuration endpoint (disabled by default)"""
    if request.method == "GET":
        config_service = service_manager.get_service("config")
        if not config_service:
            return jsonify({"error": "Service configuration UI disabled", "enabled": False})
        
        workstream_id = request.args.get("workstream_id")
        return jsonify({
            "configs": config_service.get_service_configs(workstream_id),
            "enabled": True
        })
    
    elif request.method == "POST":
        config_service = service_manager.get_service("config")
        if not config_service:
            return jsonify({"error": "Service configuration UI disabled", "enabled": False})
        
        data = request.get_json()
        result = config_service.add_service_config(
            data.get("workstream_id", ""),
            data.get("service_type", ""),
            data.get("config", {})
        )
        return jsonify(result)

