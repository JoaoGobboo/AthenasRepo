import os

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import geth_poa_middleware

from src.services.blockchain_service import compile_contract


def main():
    load_dotenv()
    rpc_url = os.getenv("RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    account_address = os.getenv("ACCOUNT_ADDRESS")

    if not rpc_url or not private_key or not account_address:
        raise SystemExit("RPC_URL, PRIVATE_KEY and ACCOUNT_ADDRESS must be configured.")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    compiled_contract = compile_contract()
    abi = compiled_contract["abi"]
    bytecode = compiled_contract["evm"]["bytecode"]["object"]

    contract = web3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = web3.eth.get_transaction_count(account_address)
    transaction = contract.constructor().build_transaction(
        {
            "from": account_address,
            "nonce": nonce,
            "gasPrice": web3.eth.gas_price,
        }
    )
    transaction["gas"] = transaction.get("gas", 3_000_000)

    signed_tx = web3.eth.account.sign_transaction(transaction, private_key=private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    print("Deployment transaction hash:", web3.to_hex(tx_hash))
    print("Contract deployed at:", receipt.contractAddress)


if __name__ == "__main__":
    main()
