from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import Candidate, Election, User, Vote
from src.services.blockchain_service import (
    BlockchainResult,
    BlockchainService,
    BlockchainUnavailable,
)
from src.utils.db import session_scope

_blockchain_service: Optional[BlockchainService] = None


def get_blockchain_service() -> Optional[BlockchainService]:
    global _blockchain_service
    if _blockchain_service is None:
        try:
            _blockchain_service = BlockchainService()
        except BlockchainUnavailable:
            _blockchain_service = None
    return _blockchain_service


def _resolve_chain_election_id(
    election_id: int, chain_service: BlockchainService
) -> Optional[int]:
    """Mapeia o ID da eleição do banco para o ID equivalente no contrato."""

    # O contrato começa em 0, enquanto o banco inicia em 1 por conta do auto-incremento.
    # Fazemos o ajuste e validamos se o ID existe na blockchain para prevenir reverts.

    chain_election_id = election_id - 1
    if chain_election_id < 0:
        return None

    try:
        election_count = chain_service.contract.functions.electionCount().call()
    except Exception:
        # Se não conseguirmos consultar, devolvemos o ID calculado e deixamos a
        # transação lidar com qualquer erro. Isso evita mascarar problemas de RPC.
        return chain_election_id

    if chain_election_id >= election_count:
        return None

    return chain_election_id


def create_election(
    title: str, description: str, candidates: List[str], creator_wallet: str
) -> Dict:
    with session_scope() as session:
        user = session.execute(
            select(User).where(User.wallet_address == creator_wallet)
        ).scalar_one_or_none()
        if user is None:
            raise ValueError("Creator not found. Authenticate before creating elections.")

        election = Election(title=title, description=description, created_by=user.id)
        for candidate_name in candidates:
            candidate = session.execute(
                select(Candidate).where(Candidate.name == candidate_name)
            ).scalar_one_or_none()
            if candidate is None:
                candidate = Candidate(name=candidate_name)
            election.candidates.append(candidate)

        session.add(election)
        session.flush()
        election_dict = election.to_dict()

    chain_info = submit_election_to_chain(title, candidates)
    election_dict["blockchain"] = chain_info
    return election_dict


def list_elections() -> List[Dict]:
    with session_scope() as session:
        elections = (
            session.query(Election)
            .options(joinedload(Election.candidates))
            .order_by(Election.created_at.desc())
            .all()
        )
        return [election.to_dict() for election in elections]


def record_vote(election_id: int, candidate_id: int, wallet: str) -> Dict:
    with session_scope() as session:
        user = session.execute(select(User).where(User.wallet_address == wallet)).scalar_one_or_none()
        if user is None:
            user = User(wallet_address=wallet, is_admin=False)
            session.add(user)
            session.flush()

        election = (
            session.query(Election)
            .options(joinedload(Election.candidates))
            .filter(Election.id == election_id)
            .first()
        )
        if election is None:
            return {"status": "error", "message": "Election not found", "code": 404}

        candidate_index = None
        for index, candidate in enumerate(election.candidates):
            if candidate.id == candidate_id:
                candidate_index = index
                break
        if candidate_index is None:
            return {"status": "error", "message": "Candidate not found", "code": 404}

        existing_vote = (
            session.query(Vote)
            .filter(Vote.election_id == election_id, Vote.voter_id == user.id)
            .first()
        )
        if existing_vote:
            return {
                "status": "error",
                "message": "Wallet already voted for this election",
                "code": 409,
            }

        chain_result = submit_vote_to_chain(election_id, candidate_index)
        if chain_result.status == "error":
            session.rollback()
            return {"status": "error", "message": chain_result.message, "code": 400}

        vote = Vote(
            election_id=election_id,
            voter_id=user.id,
            candidate_id=candidate_id,
            tx_hash=chain_result.tx_hash or chain_result.status,
        )
        session.add(vote)
        session.flush()

        response = {
            "status": "ok",
            "vote": vote.to_dict(),
            "blockchain": chain_result.__dict__,
        }
    return response


def get_election_results(election_id: int) -> Optional[Dict]:
    with session_scope() as session:
        election = (
            session.query(Election)
            .options(joinedload(Election.candidates))
            .filter(Election.id == election_id)
            .first()
        )
        if election is None:
            return None

        election_dict = election.to_dict()

        votes = (
            session.query(Vote.candidate_id)
            .filter(Vote.election_id == election_id)
            .all()
        )
        vote_counts = {candidate["id"]: 0 for candidate in election_dict["candidates"]}
        for (candidate_id,) in votes:
            if candidate_id in vote_counts:
                vote_counts[candidate_id] += 1

    chain_service = get_blockchain_service()
    blockchain_data = None
    if chain_service:
        chain_election_id = _resolve_chain_election_id(election_id, chain_service)
        if chain_election_id is not None:
            blockchain_data = chain_service.fetch_results(chain_election_id)

    if blockchain_data:
        candidate_names, chain_counts = blockchain_data
        chain_results = [
            {"candidate": candidate_names[idx], "votes": chain_counts[idx]}
            for idx in range(len(candidate_names))
        ]
    else:
        chain_results = [
            {
                "candidate": candidate["name"],
                "votes": vote_counts.get(candidate["id"], 0),
            }
            for candidate in election_dict["candidates"]
        ]

    return {
        "election": election_dict,
        "results": chain_results,
        "source": "blockchain" if blockchain_data else "database",
    }


def submit_election_to_chain(title: str, candidates: List[str]) -> Dict:
    chain_service = get_blockchain_service()
    if not chain_service:
        return {"status": "skipped", "message": "Blockchain not configured"}
    result = chain_service.create_election(title, candidates)
    return result.__dict__


def submit_vote_to_chain(election_id: int, candidate_index: int) -> BlockchainResult:
    chain_service = get_blockchain_service()
    if not chain_service:
        return BlockchainResult(
            tx_hash=None,
            status="skipped",
            message="Blockchain not configured",
        )
    chain_election_id = _resolve_chain_election_id(election_id, chain_service)
    if chain_election_id is None:
        return BlockchainResult(
            tx_hash=None,
            status="error",
            message="Election not found on blockchain",
        )
    return chain_service.cast_vote(chain_election_id, candidate_index)
