from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from src.services.election_service import record_vote

vote_bp = Blueprint("votes", __name__)


@vote_bp.post("/vote")
@jwt_required()
def submit_vote():
    payload = request.get_json() or {}
    election_id = payload.get("electionId")
    candidate_id = payload.get("candidateId")
    tx_hash = payload.get("txHash")

    if not election_id or not candidate_id:
        return jsonify({"message": "electionId and candidateId are required"}), 400
    if not tx_hash:
        return jsonify({"message": "txHash is required"}), 400

    wallet = get_jwt_identity()

    result = record_vote(election_id, candidate_id, wallet, tx_hash)
    if result.get("status") == "error":
        return jsonify(result), result.get("code", 400)

    return jsonify(result), 200
