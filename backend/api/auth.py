from flask import Blueprint, request, jsonify
from api.core_instance import proxy_core

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    # Silent=True returns None if parsing fails, so we default to {}
    data = request.get_json(silent=True) or {}

    proxy_key = str(data.get("proxy_key", "")).strip()
    
    if not proxy_key:
        return jsonify({"success": False, "message": "Proxy Key is required"}), 400

    # Verify key against core logic
    ok, reason = proxy_core.verify_proxy_teacher_is_present(proxy_key)
    
    if not ok:
        return jsonify({"success": False, "message": reason}), 401

    return jsonify({"success": True, "message": "Login successful"}), 200