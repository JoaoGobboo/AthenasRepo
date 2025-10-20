from __future__ import annotations

import os

from eth_account.messages import encode_defunct
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError
from web3 import Web3

from src.models import User
from src.utils.db import session_scope

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login():
    payload = request.get_json() or {}
    wallet_address = payload.get("walletAddress")
    signature = payload.get("signature")
    nonce = payload.get("nonce")

    if not wallet_address or not signature or not nonce:
        return jsonify({"message": "walletAddress, signature and nonce are required"}), 400

    if not verify_signature(wallet_address, signature, nonce):
        return jsonify({"message": "Invalid signature"}), 401

    with session_scope() as session:
        user = session.query(User).filter_by(wallet_address=wallet_address).first()
        if not user:
            user = User(wallet_address=wallet_address, is_admin=False)
            session.add(user)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                return jsonify({"message": "Unable to create user"}), 500

        user_data = user.to_dict()
        token = create_access_token(identity=wallet_address)

    return jsonify({"access_token": token, "user": user_data}), 200


def verify_signature(wallet_address: str, signature: str, nonce: str) -> bool:
    """Validate signature created in MetaMask using a simple nonce message."""
    try:
        rpc_url = os.getenv("RPC_URL")
        w3 = Web3(Web3.HTTPProvider(rpc_url)) if rpc_url else Web3()
        message = encode_defunct(text=f"Login nonce: {nonce}")
        recovered = w3.eth.account.recover_message(message, signature=signature)
        return recovered.lower() == wallet_address.lower()
    except Exception as exc:  # pragma: no cover - fail closed
        current_app.logger.warning("Signature verification failed: %s", exc)
        return False
