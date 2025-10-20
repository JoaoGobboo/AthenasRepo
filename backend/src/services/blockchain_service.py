from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware

try:
    from solcx import compile_standard, install_solc
except ImportError:  # pragma: no cover - optional dependency for deployment
    compile_standard = None
    install_solc = None

CONTRACT_VERSION = os.getenv("SOLC_VERSION", "0.8.20")
BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = BASE_DIR / "blockchain" / "Voting.sol"


class BlockchainUnavailable(Exception):
    """Raised when blockchain configuration is missing."""


@dataclass
class BlockchainResult:
    tx_hash: Optional[str]
    status: str
    message: Optional[str] = None


class BlockchainService:
    def __init__(self) -> None:
        self.rpc_url = os.getenv("RPC_URL")
        self.contract_address = os.getenv("CONTRACT_ADDRESS")
        if not self.rpc_url or not self.contract_address:
            raise BlockchainUnavailable("RPC_URL and CONTRACT_ADDRESS are required")

        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if os.getenv("CHAIN_ID", "").isdigit():
            self.chain_id = int(os.getenv("CHAIN_ID"))
        else:
            self.chain_id = self.web3.eth.chain_id

        # Inject middleware for Goerli/Sepolia support
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.contract = self._load_contract()

    def _load_contract(self) -> Contract:
        contract_interface = compile_contract()
        abi = contract_interface["abi"]
        address = Web3.to_checksum_address(self.contract_address)
        return self.web3.eth.contract(address=address, abi=abi)

    def create_election(self, title: str, candidates: List[str]) -> BlockchainResult:
        return self._transact("createElection", title, candidates)

    def cast_vote(self, election_id: int, candidate_index: int) -> BlockchainResult:
        return self._transact("vote", election_id, candidate_index)

    def fetch_results(self, election_id: int) -> Optional[Tuple[List[str], List[int]]]:
        try:
            results = self.contract.functions.getResults(election_id).call()
            return results[0], [int(v) for v in results[1]]
        except Exception:
            return None

    def _transact(self, function_name: str, *args) -> BlockchainResult:
        private_key = os.getenv("PRIVATE_KEY")
        account = os.getenv("ACCOUNT_ADDRESS")
        if not private_key or not account:
            return BlockchainResult(
                tx_hash=None,
                status="skipped",
                message="PRIVATE_KEY and ACCOUNT_ADDRESS are required to submit transactions.",
            )

        try:
            nonce = self.web3.eth.get_transaction_count(account)
            tx = getattr(self.contract.functions, function_name)(*args).build_transaction(
                {
                    "from": account,
                    "nonce": nonce,
                    "gasPrice": self.web3.eth.gas_price,
                }
            )
            tx["gas"] = tx.get("gas", 500000)
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return BlockchainResult(
                tx_hash=self.web3.to_hex(tx_hash),
                status="submitted",
                message="Transaction submitted to the network.",
            )
        except Exception as exc:
            return BlockchainResult(
                tx_hash=None,
                status="error",
                message=str(exc),
            )


def compile_contract() -> dict:
    cache_path = BASE_DIR / "blockchain" / "Voting.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    if compile_standard is None:
        raise RuntimeError("py-solc-x is required to compile the contract")

    install_solc(CONTRACT_VERSION)
    source = CONTRACT_PATH.read_text(encoding="utf-8")

    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {"Voting.sol": {"content": source}},
            "settings": {
                "outputSelection": {
                    "*": {"*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]}
                }
            },
        },
        solc_version=CONTRACT_VERSION,
    )

    contract_interface = compiled_sol["contracts"]["Voting.sol"]["Voting"]
    cache_path.write_text(json.dumps(contract_interface, indent=2), encoding="utf-8")
    return contract_interface
