#!/usr/bin/env python3
"""
Script de teste de carga para a API de votação Athenas.

Esta ferramenta simula múltiplas carteiras interagindo com os endpoints de autenticação, criação e votação, a fim de gerar dados para o capítulo “Resultados” do TCC.
Ela se concentra no fluxo de envio de votos, registrando telemetria por requisição e exportando relatórios detalhados e resumidos em formato JSON.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import string
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from eth_account import Account
from eth_account.messages import encode_defunct

API_DEFAULT = "http://localhost:5000/api/v1"
TOKEN_STORAGE_KEY = "athenas-token"


@dataclass
class WalletContext:
    """Represents a simulated wallet with its authentication token and session."""

    address: str
    private_key: str
    token: str
    session: requests.Session


@dataclass
class RequestRecord:
    """Captures telemetry for a single HTTP call."""

    timestamp: str
    request_index: int
    wallet: str
    candidate_id: Optional[int]
    candidate_name: Optional[str]
    request_type: str
    payload: Dict[str, Any]
    response_time_ms: float
    operation_status: str
    status_code: int
    message: str
    response_excerpt: str
    attempt: int


def generate_nonce(length: int = 12) -> str:
    charset = string.ascii_letters + string.digits
    return "".join(random.choice(charset) for _ in range(length))


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (pct / 100)
    lower = math.floor(k)
    upper = math.ceil(k)
    if lower == upper:
        return sorted_values[int(k)]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (k - lower)


class ElectionLoadTester:
    def __init__(
        self,
        base_url: str,
        total_votes: int,
        wallet_count: int,
        candidate_names: List[str],
        timeout: float,
        max_retries: int,
        output_dir: Path,
        seed: Optional[int] = None,
    ) -> None:
        if seed is not None:
            random.seed(seed)
        self.base_url = base_url.rstrip("/")
        self.total_votes = total_votes
        self.wallet_count = wallet_count
        self.candidate_names = candidate_names
        self.timeout = timeout
        self.max_retries = max_retries
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.wallets: List[WalletContext] = []
        self.election: Optional[Dict[str, Any]] = None
        self.records: List[RequestRecord] = []
        self.request_counter = 0
        self.session = requests.Session()
        self.successful_wallets: Dict[str, bool] = {}

    # ---------- Public API ----------

    def run(self) -> None:
        self._prepare_wallets()
        self._authenticate_wallets()
        self._create_election()
        self._execute_votes()
        self._write_reports()

    # ---------- Setup helpers ----------

    def _prepare_wallets(self) -> None:
        self.wallets.clear()
        for _ in range(self.wallet_count):
            account = Account.create()
            session = requests.Session()
            context = WalletContext(
                address=account.address,
                private_key=account.key.hex(),
                token="",
                session=session,
            )
            self.wallets.append(context)
            self.successful_wallets[context.address] = False

    def _authenticate_wallets(self) -> None:
        for wallet in self.wallets:
            token = self._login_wallet(wallet)
            wallet.token = token

    def _login_wallet(self, wallet: WalletContext) -> str:
        nonce = generate_nonce()
        message = encode_defunct(text=f"Login nonce: {nonce}")
        signature = Account.sign_message(message, private_key=wallet.private_key).signature.hex()
        payload = {
            "walletAddress": wallet.address,
            "signature": signature,
            "nonce": nonce,
        }
        response = self._post("/auth/login", payload, wallet)
        response.raise_for_status()
        data = response.json()
        return data["access_token"]

    def _create_election(self) -> None:
        if not self.wallets:
            raise RuntimeError("No wallets available to create an election.")
        admin_wallet = self.wallets[0]
        payload = {
            "title": f"Carga Automatizada {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            "description": "Cenário gerado pelo voting_load_test.py",
            "candidates": self.candidate_names,
            "txHash": self._generate_tx_hash(),
        }
        response = self._post("/elections", payload, admin_wallet)
        response.raise_for_status()
        self.election = response.json()["election"]

    # ---------- Voting loop ----------

    def _execute_votes(self) -> None:
        if not self.election:
            raise RuntimeError("Election must be created before executing votes.")

        candidates = self.election.get("candidates", [])
        if not candidates:
            raise RuntimeError("Election returned without candidates; cannot proceed.")

        for index in range(self.total_votes):
            wallet = self._select_wallet()
            candidate = random.choice(candidates)
            self._submit_vote(wallet, candidate, index)

    def _select_wallet(self) -> WalletContext:
        pending_wallets = [w for w in self.wallets if not self.successful_wallets[w.address]]
        pool = pending_wallets or self.wallets
        return random.choice(pool)

    def _submit_vote(self, wallet: WalletContext, candidate: Dict[str, Any], vote_index: int) -> None:
        payload = {
            "electionId": self.election["id"],
            "candidateId": candidate["id"],
            "txHash": self._generate_tx_hash(),
        }
        max_attempts = self.max_retries + 1
        for attempt in range(1, max_attempts + 1):
            start = time.perf_counter()
            status_code = 0
            message = ""
            response_excerpt = ""
            operation_status = "error"
            try:
                response = self._post("/vote", payload, wallet)
                status_code = response.status_code
                body = self._safe_json(response)
                message = body.get("message") or body.get("status") or ""
                response_excerpt = self._truncate_json(body)
                operation_status = "success" if status_code < 400 and body.get("status") == "ok" else "error"
            except requests.RequestException as exc:
                message = str(exc)
                response_excerpt = ""
                status_code = getattr(exc.response, "status_code", 0)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                self._record_request(
                    wallet=wallet.address,
                    candidate=candidate,
                    payload=payload,
                    response_time_ms=elapsed_ms,
                    operation_status=operation_status,
                    status_code=status_code,
                    message=message,
                    response_excerpt=response_excerpt,
                    attempt=attempt,
                )

            if operation_status == "success":
                self.successful_wallets[wallet.address] = True
                break
            if attempt < max_attempts:
                time.sleep(0.2 * attempt)

    # ---------- Networking helpers ----------

    def _post(self, path: str, payload: Dict[str, Any], wallet: Optional[WalletContext] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {}
        if wallet and wallet.token:
            headers["Authorization"] = f"Bearer {wallet.token}"
        response = (wallet.session if wallet else self.session).post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        return response

    @staticmethod
    def _safe_json(response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {"raw": response.text}

    @staticmethod
    def _truncate_json(data: Dict[str, Any], limit: int = 400) -> str:
        serialized = json.dumps(data, ensure_ascii=True)
        return serialized[:limit]

    def _record_request(
        self,
        wallet: str,
        candidate: Dict[str, Any],
        payload: Dict[str, Any],
        response_time_ms: float,
        operation_status: str,
        status_code: int,
        message: str,
        response_excerpt: str,
        attempt: int,
    ) -> None:
        self.request_counter += 1
        record = RequestRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_index=self.request_counter,
            wallet=wallet,
            candidate_id=candidate.get("id"),
            candidate_name=candidate.get("name"),
            request_type="vote",
            payload=payload,
            response_time_ms=round(response_time_ms, 2),
            operation_status=operation_status,
            status_code=status_code,
            message=message,
            response_excerpt=response_excerpt,
            attempt=attempt,
        )
        self.records.append(record)

    def _generate_tx_hash(self) -> str:
        return f"0x{random.getrandbits(256):064x}"

    # ---------- Reporting ----------

    def _write_reports(self) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        detail_path = self.output_dir / f"load_test_results_{timestamp}.json"
        summary_path = self.output_dir / f"load_test_summary_{timestamp}.json"

        detail_payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "config": self._config_dict(),
            "election": {
                "id": self.election.get("id") if self.election else None,
                "title": self.election.get("title") if self.election else None,
                "candidates": self.election.get("candidates") if self.election else [],
            },
            "records": [asdict(record) for record in self.records],
        }
        detail_path.write_text(json.dumps(detail_payload, indent=2), encoding="utf-8")

        summary_payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "config": self._config_dict(),
            "stats": self._summarize_records(),
        }
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

        print(f"Detalhes salvos em: {detail_path}")
        print(f"Resumo salvo em:   {summary_path}")

    def _config_dict(self) -> Dict[str, Any]:
        return {
            "base_url": self.base_url,
            "total_votes": self.total_votes,
            "wallet_count": self.wallet_count,
            "candidate_names": self.candidate_names,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

    def _summarize_records(self) -> Dict[str, Any]:
        total = len(self.records)
        successes = sum(1 for record in self.records if record.operation_status == "success")
        failures = total - successes
        latencies = [record.response_time_ms for record in self.records]

        error_breakdown: Dict[str, Dict[str, Any]] = {}
        for record in self.records:
            if record.operation_status == "success":
                continue
            code_key = str(record.status_code)
            error_entry = error_breakdown.setdefault(code_key, {"count": 0, "messages": {}})
            error_entry["count"] += 1
            msg_key = record.message or "(sem mensagem)"
            error_entry["messages"][msg_key] = error_entry["messages"].get(msg_key, 0) + 1

        return {
            "total_requests": total,
            "success_count": successes,
            "failure_count": failures,
            "success_rate": round((successes / total) * 100, 2) if total else 0.0,
            "failure_rate": round((failures / total) * 100, 2) if total else 0.0,
            "latency_ms": {
                "avg": round(sum(latencies) / total, 2) if total else 0.0,
                "p50": round(percentile(latencies, 50), 2),
                "p95": round(percentile(latencies, 95), 2),
                "p99": round(percentile(latencies, 99), 2),
                "min": round(min(latencies), 2) if latencies else 0.0,
                "max": round(max(latencies), 2) if latencies else 0.0,
            },
            "error_types": error_breakdown,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulação de carga para o backend de votação")
    parser.add_argument(
        "--base-url",
        default=API_DEFAULT,
        help=f"Endpoint base da API (padrão: {API_DEFAULT})",
    )
    parser.add_argument(
        "--votes",
        type=int,
        default=100,
        help="Quantidade de requisições de voto a serem enviadas (padrão: 100)",
    )
    parser.add_argument(
        "--wallets",
        type=int,
        default=120,
        help="Número de carteiras simuladas (padrão: 120)",
    )
    parser.add_argument(
        "--candidates",
        nargs="+",
        default=["Alice", "Bob", "Carol"],
        help="Lista de nomes de candidatos para a eleição criada pela simulação",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Tempo máximo de espera por requisição em segundos (padrão: 10)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Número de tentativas extras em caso de erro (padrão: 2)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/tests/results"),
        help="Diretório para salvar os relatórios JSON",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed opcional para reprodução dos testes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tester = ElectionLoadTester(
        base_url=args.base_url,
        total_votes=args.votes,
        wallet_count=args.wallets,
        candidate_names=args.candidates,
        timeout=args.timeout,
        max_retries=args.retries,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    tester.run()


if __name__ == "__main__":
    main()
