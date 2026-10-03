import sys
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

from supabaseclient import supabase


# ============================================================
# SETTINGS
# ============================================================

TOTAL_TRANSACTIONS = 10_000
BATCH_SIZE = 500
FETCH_SIZE = 1000

DAYS_HISTORY = 90


# ============================================================
# FETCH HELPERS
# ============================================================

def fetch_all(table, columns="*"):

    rows = []
    start = 0

    while True:

        response = (
            supabase
            .table(table)
            .select(columns)
            .range(
                start,
                start + FETCH_SIZE - 1
            )
            .execute()
        )

        batch = response.data

        if not batch:
            break

        rows.extend(batch)

        if len(batch) < FETCH_SIZE:
            break

        start += FETCH_SIZE

    print(
        f"Fetched {len(rows):,} rows "
        f"from {table}"
    )

    return rows


# ============================================================
# RANDOM TRANSACTION TIME
# ============================================================

def random_transaction_time():

    now = datetime.now(timezone.utc)

    days_ago = random.randint(
        0,
        DAYS_HISTORY
    )

    base_date = now - timedelta(
        days=days_ago
    )

    # Most transactions happen during daytime/evening

    hour = random.choices(
        list(range(24)),
        weights=[
            1, 1, 1, 1, 1, 2,
            4, 6, 8, 10, 12, 12,
            12, 12, 12, 12, 13, 14,
            14, 13, 10, 7, 4, 2
        ]
    )[0]

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_date.replace(
        hour=hour,
        minute=minute,
        second=second,
        microsecond=0
    )


# ============================================================
# AMOUNT GENERATION
# ============================================================

def transaction_amount(tx_type):

    ranges = {

        "send_money":
            (100, 8000),

        "cash_in":
            (500, 15000),

        "cash_out":
            (500, 12000),

        "merchant_payment":
            (100, 6000),

        "bill_payment":
            (200, 8000),

        "mobile_recharge":
            (20, 1000),

        "bank_transfer":
            (1000, 20000),

        "remittance":
            (2000, 30000)
    }

    low, high = ranges[tx_type]

    return round(
        random.uniform(low, high),
        2
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 55)
    print("TraceAI Normal Transaction Generator")
    print("=" * 55)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    customers = fetch_all(
        "customers",
        "id,district"
    )

    wallets = fetch_all(
        "wallets",
        "id,customer_id,balance,status"
    )

    customer_devices = fetch_all(
        "customer_devices",
        "customer_id,device_id"
    )

    agents = fetch_all(
        "agents",
        "id,status,district"
    )

    merchants = fetch_all(
        "merchants",
        "id,status,district"
    )

    # --------------------------------------------------------
    # Build mappings
    # --------------------------------------------------------

    customer_district = {
        c["id"]: c["district"]
        for c in customers
    }

    devices_by_customer = {}

    for relation in customer_devices:

        customer_id = relation["customer_id"]

        devices_by_customer.setdefault(
            customer_id,
            []
        ).append(
            relation["device_id"]
        )

    active_wallets = [
        w for w in wallets
        if w["status"] == "active"
    ]

    active_agents = [
        a for a in agents
        if a["status"] == "active"
    ]

    active_merchants = [
        m for m in merchants
        if m["status"] == "active"
    ]

    if len(active_wallets) < 2:
        print(
            "Not enough active wallets."
        )
        return

    # --------------------------------------------------------
    # Local wallet balances
    # --------------------------------------------------------

    wallet_balances = {}

    for wallet in active_wallets:

        wallet_balances[
            wallet["id"]
        ] = float(
            wallet["balance"] or 0
        )

    # --------------------------------------------------------
    # Transaction distribution
    # --------------------------------------------------------

    tx_types = [
        "send_money",
        "cash_in",
        "cash_out",
        "merchant_payment",
        "bill_payment",
        "mobile_recharge",
        "bank_transfer",
        "remittance"
    ]

    tx_weights = [
        30,
        15,
        15,
        15,
        8,
        10,
        4,
        3
    ]

    transactions = []

    # --------------------------------------------------------
    # Generate transactions
    # --------------------------------------------------------

    for i in range(
        1,
        TOTAL_TRANSACTIONS + 1
    ):

        tx_type = random.choices(
            tx_types,
            weights=tx_weights
        )[0]

        amount = transaction_amount(
            tx_type
        )

        sender_wallet = None
        receiver_wallet = None
        device_id = None
        agent_id = None
        merchant_id = None

        sender_before = None
        sender_after = None

        receiver_before = None
        receiver_after = None

        district = None

        # ====================================================
        # SEND MONEY
        # ====================================================

        if tx_type == "send_money":

            sender_wallet = random.choice(
                active_wallets
            )

            receiver_wallet = random.choice(
                active_wallets
            )

            while (
                receiver_wallet["id"]
                == sender_wallet["id"]
            ):

                receiver_wallet = random.choice(
                    active_wallets
                )

        # ====================================================
        # BANK TRANSFER
        # ====================================================

        elif tx_type == "bank_transfer":

            sender_wallet = random.choice(
                active_wallets
            )

            receiver_wallet = random.choice(
                active_wallets
            )

            while (
                receiver_wallet["id"]
                == sender_wallet["id"]
            ):

                receiver_wallet = random.choice(
                    active_wallets
                )

        # ====================================================
        # CASH OUT
        # ====================================================

        elif tx_type == "cash_out":

            sender_wallet = random.choice(
                active_wallets
            )

            if active_agents:

                agent_id = random.choice(
                    active_agents
                )["id"]

        # ====================================================
        # CASH IN
        # ====================================================

        elif tx_type == "cash_in":

            receiver_wallet = random.choice(
                active_wallets
            )

            if active_agents:

                agent_id = random.choice(
                    active_agents
                )["id"]

        # ====================================================
        # MERCHANT PAYMENT
        # ====================================================

        elif tx_type == "merchant_payment":

            sender_wallet = random.choice(
                active_wallets
            )

            if active_merchants:

                merchant_id = random.choice(
                    active_merchants
                )["id"]

        # ====================================================
        # BILL PAYMENT
        # ====================================================

        elif tx_type == "bill_payment":

            sender_wallet = random.choice(
                active_wallets
            )

            if active_merchants:

                merchant_id = random.choice(
                    active_merchants
                )["id"]

        # ====================================================
        # MOBILE RECHARGE
        # ====================================================

        elif tx_type == "mobile_recharge":

            sender_wallet = random.choice(
                active_wallets
            )

        # ====================================================
        # REMITTANCE
        # ====================================================

        elif tx_type == "remittance":

            receiver_wallet = random.choice(
                active_wallets
            )

        # ====================================================
        # DEVICE
        # ====================================================

        device_customer_id = None

        if sender_wallet:

            device_customer_id = (
                sender_wallet[
                    "customer_id"
                ]
            )

        elif receiver_wallet:

            device_customer_id = (
                receiver_wallet[
                    "customer_id"
                ]
            )

        if device_customer_id:

            device_list = (
                devices_by_customer.get(
                    device_customer_id,
                    []
                )
            )

            if device_list:

                device_id = random.choice(
                    device_list
                )

            district = (
                customer_district.get(
                    device_customer_id
                )
            )

        # ====================================================
        # BALANCE SIMULATION
        # ====================================================

        if sender_wallet:

            sender_id = (
                sender_wallet["id"]
            )

            sender_before = (
                wallet_balances[
                    sender_id
                ]
            )

            # Ensure normal transaction
            # does not exceed wallet balance

            if sender_before < amount:

                amount = max(
                    10,
                    sender_before * 0.5
                )

            sender_after = max(
                sender_before
                - amount,
                0
            )

            wallet_balances[
                sender_id
            ] = sender_after

        if receiver_wallet:

            receiver_id = (
                receiver_wallet["id"]
            )

            receiver_before = (
                wallet_balances[
                    receiver_id
                ]
            )

            receiver_after = (
                receiver_before
                + amount
            )

            wallet_balances[
                receiver_id
            ] = receiver_after

        # ====================================================
        # FEE
        # ====================================================

        if tx_type == "cash_out":

            fee = round(
                amount * 0.015,
                2
            )

        elif tx_type in [
            "send_money",
            "bank_transfer"
        ]:

            fee = round(
                random.uniform(
                    0,
                    10
                ),
                2
            )

        else:

            fee = 0

        # ====================================================
        # CREATE ROW
        # ====================================================

        transaction = {

            "transaction_code":
                "TX-"
                + uuid.uuid4().hex[:16].upper(),

            "sender_wallet_id":
                sender_wallet["id"]
                if sender_wallet
                else None,

            "receiver_wallet_id":
                receiver_wallet["id"]
                if receiver_wallet
                else None,

            "device_id":
                device_id,

            "agent_id":
                agent_id,

            "merchant_id":
                merchant_id,

            "transaction_type":
                tx_type,

            "amount":
                round(amount, 2),

            "fee":
                fee,

            "sender_balance_before":
                round(
                    sender_before,
                    2
                )
                if sender_before is not None
                else None,

            "sender_balance_after":
                round(
                    sender_after,
                    2
                )
                if sender_after is not None
                else None,

            "receiver_balance_before":
                round(
                    receiver_before,
                    2
                )
                if receiver_before is not None
                else None,

            "receiver_balance_after":
                round(
                    receiver_after,
                    2
                )
                if receiver_after is not None
                else None,

            "channel":
                "mobile_app",

            "status":
                "completed",

            "district":
                district,

            "transaction_time":
                random_transaction_time()
                .isoformat()
        }

        transactions.append(
            transaction
        )

        # ====================================================
        # UPLOAD BATCH
        # ====================================================

        if len(
            transactions
        ) >= BATCH_SIZE:

            (
                supabase
                .table("transactions")
                .insert(transactions)
                .execute()
            )

            print(
                f"Uploaded {i:,} / "
                f"{TOTAL_TRANSACTIONS:,} "
                f"transactions"
            )

            transactions.clear()

    # Remaining rows

    if transactions:

        (
            supabase
            .table("transactions")
            .insert(transactions)
            .execute()
        )

    print(
        "\nNormal transaction "
        "generation completed."
    )


if __name__ == "__main__":
    main()