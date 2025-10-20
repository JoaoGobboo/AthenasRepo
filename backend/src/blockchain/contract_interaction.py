import argparse
import os

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

from src.services.blockchain_service import compile_contract


def get_contract(web3: Web3, address: str):
    contract_interface = compile_contract()
    abi = contract_interface["abi"]
    return web3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def connect_web3() -> Web3:
    rpc_url = os.getenv("RPC_URL")
    if not rpc_url:
        raise SystemExit("RPC_URL must be defined in the environment.")
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return web3


def cast_vote(contract, election_id: int, candidate_index: int):
    private_key = os.getenv("PRIVATE_KEY")
    account_address = os.getenv("ACCOUNT_ADDRESS")
    if not private_key or not account_address:
        raise SystemExit("PRIVATE_KEY and ACCOUNT_ADDRESS must be configured.")

    nonce = contract.web3.eth.get_transaction_count(account_address)
    transaction = contract.functions.vote(election_id, candidate_index).build_transaction(
        {
            "from": account_address,
            "nonce": nonce,
            "gasPrice": contract.web3.eth.gas_price,
        }
    )
    transaction["gas"] = transaction.get("gas", 500_000)

    signed_tx = contract.web3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = contract.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = contract.web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Vote submitted:", contract.web3.to_hex(tx_hash))
    print("Status:", receipt.status)


def read_results(contract, election_id: int):
    candidates, votes = contract.functions.getResults(election_id).call()
    for index, candidate in enumerate(candidates):
        print(f"{candidate}: {votes[index]}")


def create_election(contract, title: str, candidates):
    private_key = os.getenv("PRIVATE_KEY")
    account_address = os.getenv("ACCOUNT_ADDRESS")
    if not private_key or not account_address:
        raise SystemExit("PRIVATE_KEY and ACCOUNT_ADDRESS must be configured.")

    nonce = contract.web3.eth.get_transaction_count(account_address)
    transaction = contract.functions.createElection(title, candidates).build_transaction(
        {
            "from": account_address,
            "nonce": nonce,
            "gasPrice": contract.web3.eth.gas_price,
        }
    )
    transaction["gas"] = transaction.get("gas", 3_000_000)

    signed_tx = contract.web3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = contract.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = contract.web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Election created with tx:", contract.web3.to_hex(tx_hash))
    print("Status:", receipt.status)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Interact with the Voting smart contract.")
    parser.add_argument("--contract", required=True, help="Deployed contract address")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Create a new election")
    create_parser.add_argument("--title", required=True)
    create_parser.add_argument("--candidates", nargs="+", required=True)

    vote_parser = subparsers.add_parser("vote", help="Cast a vote")
    vote_parser.add_argument("--election", type=int, required=True)
    vote_parser.add_argument("--candidate", type=int, required=True)

    results_parser = subparsers.add_parser("results", help="Fetch election results")
    results_parser.add_argument("--election", type=int, required=True)

    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_arguments()
    web3 = connect_web3()
    contract = get_contract(web3, args.contract)

    if args.command == "create":
        create_election(contract, args.title, args.candidates)
    elif args.command == "vote":
        cast_vote(contract, args.election, args.candidate)
    elif args.command == "results":
        read_results(contract, args.election)
    else:
        print("No command provided. Use --help for instructions.")


if __name__ == "__main__":
    main()
