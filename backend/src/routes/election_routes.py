from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from src.services.election_service import (
    create_election,
    get_election_results,
    list_elections,
)

election_bp = Blueprint("elections", __name__)


@election_bp.get("")
@jwt_required()
def get_all_elections():
    elections = list_elections()
    return jsonify({"elections": elections}), 200


@election_bp.post("")
@jwt_required()
def create_new_election():
    wallet = get_jwt_identity()
    payload = request.get_json() or {}
    title = payload.get("title")
    description = payload.get("description", "")
    candidates = payload.get("candidates", [])
    if not title or not candidates:
        return jsonify({"message": "title and candidates are required"}), 400

    try:
        election = create_election(
            title=title,
            description=description,
            candidates=candidates,
            creator_wallet=wallet,
        )
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400
    return jsonify({"election": election}), 201


@election_bp.get("/<int:election_id>/results")
@jwt_required()
def election_results(election_id: int):
    results = get_election_results(election_id)
    if results is None:
        return jsonify({"message": "Election not found"}), 404
    return jsonify(results), 200
