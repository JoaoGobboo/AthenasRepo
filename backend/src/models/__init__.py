from __future__ import annotations

from datetime import datetime
from typing import Dict

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

election_candidates = Table(
    "election_candidates",
    Base.metadata,
    Column("election_id", ForeignKey("elections.id"), primary_key=True),
    Column("candidate_id", ForeignKey("candidates.id"), primary_key=True),
    UniqueConstraint("election_id", "candidate_id", name="uq_election_candidate"),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    wallet_address = Column(String(64), unique=True, nullable=False, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    votes = relationship("Vote", back_populates="voter")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "wallet_address": self.wallet_address,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat(),
        }


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    elections = relationship(
        "Election", secondary=election_candidates, back_populates="candidates"
    )

    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name}


class Election(Base):
    __tablename__ = "elections"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    candidates = relationship(
        "Candidate", secondary=election_candidates, back_populates="elections"
    )
    votes = relationship("Vote", back_populates="election")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    election_id = Column(Integer, ForeignKey("elections.id"), nullable=False)
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    tx_hash = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    election = relationship("Election", back_populates="votes")
    voter = relationship("User", back_populates="votes")
    candidate = relationship("Candidate")

    __table_args__ = (
        UniqueConstraint("election_id", "voter_id", name="uq_vote_election_voter"),
    )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "election_id": self.election_id,
            "voter_id": self.voter_id,
            "candidate_id": self.candidate_id,
            "tx_hash": self.tx_hash,
            "created_at": self.created_at.isoformat(),
        }
