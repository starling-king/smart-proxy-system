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
    # ... existing code ...
    ok, reason = proxy_core.verify_proxy_teacher_is_present(proxy_key)
    
    if not ok:
        return jsonify({"success": False, "message": reason}), 401

    # --- [START UPDATE] BLOCK ABSENT TEACHERS ---
    # Fetch today's absent list
    absent_keys, _ = proxy_core.get_todays_absent_keys()
    
    # Normalize keys for robust comparison (handles "Amit" vs "amit ")
    if absent_keys:
        norm_input = proxy_core._normalize(proxy_key)
        norm_absent = [proxy_core._normalize(k) for k in absent_keys]

        if norm_input in norm_absent:
            return jsonify({
                "success": False, 
                "message": f"Access Denied: '{proxy_key}' is marked ABSENT today."
            }), 403
    # --- [END UPDATE] ---

    return jsonify({"success": True, "message": "Login successful"}), 200