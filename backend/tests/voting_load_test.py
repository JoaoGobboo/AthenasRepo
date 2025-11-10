#!/usr/bin/env python3
"""Load testing script for the Athenas voting API with optional blockchain calls."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import string
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.contract import Contract

API_DEFAULT = "http://localhost:5000/api/v1"
TOKEN_STORAGE_KEY = "athenas-token"

load_dotenv()


@dataclass
class WalletContext:
    address: str
    private_key: str
    token: str
    session: requests.Session


@dataclass
class RequestRecord:
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
        wallet_file: Optional[Path] = None,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        contract_abi_path: Optional[Path] = None,
    ) -> None:
        if seed is not None:
            random.seed(seed)
        self.base_url = base_url.rstrip("/")
        self.total_votes = total_votes
        self.requested_wallets = wallet_count
        self.candidate_names = candidate_names
        self.timeout = timeout
        self.max_retries = max_retries
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wallet_file = wallet_file

        self.rpc_url = rpc_url or os.getenv("RPC_URL")
        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        self.contract_abi_path = contract_abi_path or Path("backend/src/blockchain/Voting.json")
        self.use_blockchain = bool(self.wallet_file and self.rpc_url and self.contract_address)

        self.wallets: List[WalletContext] = []
        self.election: Optional[Dict[str, Any]] = None
        self.records: List[RequestRecord] = []
        self.request_counter = 0
        self.session = requests.Session()
        self.successful_wallets: Dict[str, bool] = {}
        self.web3: Optional[Web3] = None
        self.contract: Optional[Contract] = None
        self.chain_election_id: Optional[int] = None
        self.elections_created = 0

        if self.use_blockchain:
            self._init_blockchain()

    def run(self) -> None:
        self._prepare_wallets()
        self._authenticate_wallets()
        self._create_election()
        self._execute_votes()
        self._write_reports()

    # ---------- Setup ----------

    def _prepare_wallets(self) -> None:
        self.wallets.clear()
        if self.wallet_file:
            wallets_data = json.loads(Path(self.wallet_file).read_text(encoding="utf-8"))
            for entry in wallets_data:
                address = entry["address"]
                private_key = entry["private_key"]
                if not private_key.startswith("0x"):
                    private_key = f"0x{private_key}"
                if self.web3:
                    address = Web3.to_checksum_address(address)
                context = WalletContext(
                    address=address,
                    private_key=private_key,
                    token="",
                    session=requests.Session(),
                )
                self.wallets.append(context)
                self.successful_wallets[context.address] = False
        else:
            for _ in range(self.requested_wallets):
                account = Account.create()
                context = WalletContext(
                    address=account.address,
                    private_key=account.key.hex(),
                    token="",
                    session=requests.Session(),
                )
                self.wallets.append(context)
                self.successful_wallets[context.address] = False

        if not self.wallets:
            raise RuntimeError("At least one wallet is required to execute the test.")

    def _authenticate_wallets(self) -> None:
        for wallet in self.wallets:
            wallet.token = self._login_wallet(wallet)

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
        return response.json()["access_token"]

    def _create_election(self) -> None:
        admin_wallet = self.wallets[0]
        title = f"Carga Automatizada {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        payload = {
            "title": title,
            "description": "Cenário gerado pelo voting_load_test.py",
            "candidates": self.candidate_names,
        }

        if self.use_blockchain and self.contract:
            tx_hash, chain_election_id = self._create_election_on_chain(admin_wallet, title)
            payload["txHash"] = tx_hash
            self.chain_election_id = chain_election_id
        else:
            payload["txHash"] = self._generate_tx_hash()

        response = self._post("/elections", payload, admin_wallet)
        response.raise_for_status()
        self.election = response.json()["election"]
        self.elections_created += 1
        self._reset_wallet_usage()

    # ---------- Voting ----------

    def _execute_votes(self) -> None:
        if not self.election:
            raise RuntimeError("Election must be created before executing votes.")

        candidates = self.election.get("candidates", [])
        if not candidates:
            raise RuntimeError("Election returned without candidates; cannot proceed.")

        for index in range(self.total_votes):
            if all(self.successful_wallets.values()):
                self._create_election()
                candidates = self.election.get("candidates", [])
            wallet = self._select_wallet()
            candidate = random.choice(candidates)
            self._submit_vote(wallet, candidate, index)

    def _select_wallet(self) -> WalletContext:
        unused = [w for w in self.wallets if not self.successful_wallets[w.address]]
        pool = unused or self.wallets
        return random.choice(pool)

    def _submit_vote(self, wallet: WalletContext, candidate: Dict[str, Any], vote_index: int) -> None:
        tx_hash = None
        candidate_index = None
        for idx, entry in enumerate(self.election.get("candidates", [])):
            if entry["id"] == candidate["id"]:
                candidate_index = idx
                break

        if self.use_blockchain and self.contract:
            if candidate_index is None:
                self._record_request(
                    wallet=wallet.address,
                    candidate=candidate,
                    payload={},
                    response_time_ms=0.0,
                    operation_status="error",
                    status_code=0,
                    message="Candidate index not found for blockchain vote",
                    response_excerpt="Candidate index not found",
                    attempt=0,
                )
                return
            try:
                tx_hash = self._vote_on_chain(wallet, candidate_index)
            except Exception as exc:
                self._record_request(
                    wallet=wallet.address,
                    candidate=candidate,
                    payload={},
                    response_time_ms=0.0,
                    operation_status="error",
                    status_code=0,
                    message=str(exc),
                    response_excerpt=str(exc),
                    attempt=0,
                )
                return
        else:
            tx_hash = self._generate_tx_hash()

        payload = {
            "electionId": self.election["id"],
            "candidateId": candidate["id"],
            "txHash": tx_hash,
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

    # ---------- Networking & logging ----------

    def _post(self, path: str, payload: Dict[str, Any], wallet: Optional[WalletContext] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {}
        if wallet and wallet.token:
            headers["Authorization"] = f"Bearer {wallet.token}"
        return (wallet.session if wallet else self.session).post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

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

    def _reset_wallet_usage(self) -> None:
        for key in self.successful_wallets:
            self.successful_wallets[key] = False

    def _generate_tx_hash(self) -> str:
        return f"0x{random.getrandbits(256):064x}"

    # ---------- Blockchain helpers ----------

    def _init_blockchain(self) -> None:
        if not self.rpc_url or not self.contract_address:
            return
        abi_data = json.loads(Path(self.contract_abi_path).read_text(encoding="utf-8"))
        abi = abi_data["abi"] if isinstance(abi_data, dict) and "abi" in abi_data else abi_data
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address), abi=abi
        )

    def _create_election_on_chain(self, wallet: WalletContext, title: str) -> Tuple[str, int]:
        if not self.contract or not self.web3:
            raise RuntimeError("Blockchain not configured")
        tx_function = self.contract.functions.createElection(title, self.candidate_names)
        tx_hash, receipt = self._send_contract_tx(wallet, tx_function)
        try:
            events = self.contract.events.ElectionCreated().process_receipt(receipt)
            election_id = events[0]["args"]["electionId"] if events else None
        except Exception:
            election_id = None
        if election_id is None:
            election_id = self.contract.functions.electionCount().call() - 1
        return tx_hash, election_id

    def _vote_on_chain(self, wallet: WalletContext, candidate_index: int) -> str:
        if not self.contract:
            raise RuntimeError("Blockchain not configured")
        if self.chain_election_id is None:
            election_count = self.contract.functions.electionCount().call()
            self.chain_election_id = max(0, election_count - 1)
        tx_function = self.contract.functions.vote(self.chain_election_id, candidate_index)
        tx_hash, _ = self._send_contract_tx(wallet, tx_function)
        return tx_hash

    def _send_contract_tx(self, wallet: WalletContext, tx_function) -> Tuple[str, Any]:
        if not self.web3:
            raise RuntimeError("Web3 provider not initialized")
        account = self.web3.eth.account.from_key(wallet.private_key)
        nonce = self.web3.eth.get_transaction_count(account.address, 'pending')
        transaction = tx_function.build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "gasPrice": self.web3.eth.gas_price,
            }
        )
        transaction.setdefault("gas", 500000)
        signed_tx = self.web3.eth.account.sign_transaction(transaction, wallet.private_key)
        raw_tx = getattr(signed_tx, "rawTransaction", signed_tx.raw_transaction)
        tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return self.web3.to_hex(tx_hash), receipt

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
            "wallet_count": len(self.wallets),
            "candidate_names": self.candidate_names,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "blockchain": bool(self.contract),
            "elections_created": self.elections_created,
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
    parser.add_argument("--base-url", default=API_DEFAULT)
    parser.add_argument("--votes", type=int, default=100)
    parser.add_argument("--wallets", type=int, default=120)
    parser.add_argument("--candidates", nargs="+", default=["Alice", "Bob", "Carol"])
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("backend/tests/results"))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--wallet-file", type=Path, default=None)
    parser.add_argument("--rpc-url", default=os.getenv("RPC_URL"))
    parser.add_argument("--contract-address", default=os.getenv("CONTRACT_ADDRESS"))
    parser.add_argument(
        "--contract-abi",
        type=Path,
        default=Path("backend/src/blockchain/Voting.json"),
        help="Arquivo contendo o ABI ou Voting.json",
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
        wallet_file=args.wallet_file,
        rpc_url=args.rpc_url,
        contract_address=args.contract_address,
        contract_abi_path=args.contract_abi,
    )
    tester.run()


if __name__ == "__main__":
    main()
