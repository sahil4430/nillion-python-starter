import asyncio
import os
from dotenv import load_dotenv
import py_nillion_client as nillion
from py_nillion_client import NodeKey, UserKey
from nillion_python_helpers import get_quote_and_pay, create_nillion_client, create_payments_config
from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

# Load environment variables
home = os.getenv("HOME")
load_dotenv(f"{home}/.config/nillion/nillion-devnet.env")

async def main():
    try:
        # 1. Initial setup
        # 1.1. Get cluster_id, grpc_endpoint, & chain_id from the .env file
        cluster_id = os.getenv("NILLION_CLUSTER_ID")
        grpc_endpoint = os.getenv("NILLION_NILCHAIN_GRPC")
        chain_id = os.getenv("NILLION_NILCHAIN_CHAIN_ID")
        private_key_hex = os.getenv("NILLION_NILCHAIN_PRIVATE_KEY_0")

        if not all([cluster_id, grpc_endpoint, chain_id, private_key_hex]):
            raise ValueError("Missing required environment variables.")

        # 1.2 Generate user and node keys from a seed
        seed = "my_seed"
        user_key = UserKey.from_seed(seed)
        node_key = NodeKey.from_seed(seed)

        # 2. Initialize NillionClient against nillion-devnet
        client = create_nillion_client(user_key, node_key)

        # 3. Pay for and store the program
        program_name = "secret_addition_complete"
        program_mir_path = f"../nada_quickstart_programs/target/{program_name}.nada.bin"
        
        # Create payments config, client and wallet
        payments_config = create_payments_config(chain_id, grpc_endpoint)
        payments_client = LedgerClient(payments_config)
        payments_wallet = LocalWallet(PrivateKey(bytes.fromhex(private_key_hex)), prefix="nillion")

        # Pay to store the program and obtain a receipt of the payment
        receipt_store_program = await get_quote_and_pay(
            client,
            nillion.Operation.store_program(program_mir_path),
            payments_wallet,
            payments_client,
            cluster_id,
        )

        # Store the program
        action_id = await client.store_program(cluster_id, program_name, program_mir_path, receipt_store_program)
        program_id = f"{client.user_id}/{program_name}"
        print(f"Stored program. action_id: {action_id}")
        print(f"Stored program_id: {program_id}")

        # 4. Create the 1st secret, add permissions, pay for and store it in the network
        new_secret = nillion.NadaValues({"my_int1": nillion.SecretInteger(500)})
        party_name = "Party1"
        permissions = nillion.Permissions.default_for_user(client.user_id)
        permissions.add_compute_permissions({client.user_id: {program_id}})

        receipt_store_secret = await get_quote_and_pay(
            client,
            nillion.Operation.store_values(new_secret, ttl_days=5),
            payments_wallet,
            payments_client,
            cluster_id,
        )

        store_id = await client.store_values(cluster_id, new_secret, permissions, receipt_store_secret)
        print(f"Secret stored with store_id: {store_id}")

        # 5. Set up and run the computation
        compute_bindings = nillion.ProgramBindings(program_id)
        compute_bindings.add_input_party(party_name, client.party_id)
        compute_bindings.add_output_party(party_name, client.party_id)

        computation_time_secrets = nillion.NadaValues({"my_int2": nillion.SecretInteger(10)})

        receipt_compute = await get_quote_and_pay(
            client,
            nillion.Operation.compute(program_id, computation_time_secrets),
            payments_wallet,
            payments_client,
            cluster_id,
        )

        compute_id = await client.compute(
            cluster_id,
            compute_bindings,
            [store_id],
            computation_time_secrets,
            receipt_compute,
        )

        print(f"Computation sent to the network. compute_id: {compute_id}")

        # 6. Retrieve and print the computation result
        while True:
            compute_event = await client.next_compute_event()
            if isinstance(compute_event, nillion.ComputeFinishedEvent):
                print(f"✅  Compute complete for compute_id {compute_event.uuid}")
                print(f"🖥️  The result is {compute_event.result.value}")
                return compute_event.result.value

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
