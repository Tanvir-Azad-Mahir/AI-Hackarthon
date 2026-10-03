import sys
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone


# ============================================================
# IMPORT SUPABASE CLIENT
# Works whether this file is inside backend/
# or backend/data_generator/
# ============================================================

CURRENT_DIR = Path(__file__).resolve().parent

if (CURRENT_DIR / "supabaseclient.py").exists():
    sys.path.append(str(CURRENT_DIR))
else:
    sys.path.append(str(CURRENT_DIR.parent))

from supabaseclient import supabase


# ============================================================
# SETTINGS
# ============================================================

TOTAL_FRAUD = 2000
BATCH_SIZE = 200
FETCH_SIZE = 1000


# ============================================================
# FETCH ALL ROWS FROM SUPABASE
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

        print(
            f"Fetched {len(rows):,} rows "
            f"from {table}"
        )

        if len(batch) < FETCH_SIZE:
            break

        start += FETCH_SIZE

    return rows


# ============================================================
# LOAD FRAUD SCENARIOS
# ============================================================

def load_scenarios():

    rows = fetch_all(
        "fraud_scenarios",
        "id,scenario_code"
    )

    scenarios = {
        row["scenario_code"]: row["id"]
        for row in rows
    }

    required = [
        "ATO_NEW_DEVICE",
        "HIGH_VALUE_ANOMALY",
        "MULE_RAPID_TRANSFER",
        "RAPID_CASHOUT",
        "MULE_FAN_IN",
        "MULE_FAN_OUT",
    ]

    missing = [
        code
        for code in required
        if code not in scenarios
    ]

    if missing:
        raise ValueError(
            "Missing fraud scenarios in database: "
            + ", ".join(missing)
        )

    return scenarios


# ============================================================
# GENERATE SUSPICIOUS TRANSACTION TIME
# ============================================================

def suspicious_time():

    now = datetime.now(timezone.utc)

    days_ago = random.randint(
        0,
        30
    )

    # Bias fraudulent transactions toward unusual hours.
    hour = random.choice([
        0,
        1,
        2,
        3,
        4,
        5,
        22,
        23
    ])

    fraud_time = (
        now
        - timedelta(days=days_ago)
    )

    fraud_time = fraud_time.replace(
        hour=hour,
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0
    )

    return fraud_time


# ============================================================
# CHOOSE A DEVICE THAT DOES NOT BELONG TO CUSTOMER
# Used for account takeover simulation
# ============================================================

def choose_unknown_device(
    all_device_ids,
    normal_devices
):

    if not all_device_ids:
        return None

    # Try random devices instead of creating a huge
    # filtered list every time.
    for _ in range(50):

        device_id = random.choice(
            all_device_ids
        )

        if device_id not in normal_devices:
            return device_id

    # Fallback
    for device_id in all_device_ids:

        if device_id not in normal_devices:
            return device_id

    return None


# ============================================================
# CREATE FRAUD TRANSACTION
# ============================================================

def make_transaction(
    sender,
    receiver,
    device_id,
    amount,
    tx_type="send_money",
    agent_id=None
):

    transaction_id = str(
        uuid.uuid4()
    )

    sender_balance = float(
        sender.get("balance") or 0
    )

    # IMPORTANT:
    # receiver can be None for cash_out.
    if receiver is not None:

        receiver_balance = float(
            receiver.get("balance") or 0
        )

        receiver_id = receiver["id"]

    else:

        receiver_balance = None
        receiver_id = None

    sender_after = max(
        sender_balance - amount,
        0
    )

    if receiver_balance is not None:

        receiver_after = (
            receiver_balance
            + amount
        )

    else:

        receiver_after = None

    return {

        "id":
            transaction_id,

        "transaction_code":
            "FRAUD-"
            + uuid.uuid4().hex[:14].upper(),

        "sender_wallet_id":
            sender["id"],

        "receiver_wallet_id":
            receiver_id,

        "device_id":
            device_id,

        "agent_id":
            agent_id,

        "merchant_id":
            None,

        "transaction_type":
            tx_type,

        "amount":
            round(
                amount,
                2
            ),

        "fee":
            0,

        "sender_balance_before":
            round(
                sender_balance,
                2
            ),

        "sender_balance_after":
            round(
                sender_after,
                2
            ),

        "receiver_balance_before":
            (
                round(
                    receiver_balance,
                    2
                )
                if receiver_balance is not None
                else None
            ),

        "receiver_balance_after":
            (
                round(
                    receiver_after,
                    2
                )
                if receiver_after is not None
                else None
            ),

        "channel":
            "mobile_app",

        "status":
            "completed",

        "transaction_time":
            suspicious_time().isoformat()
    }


# ============================================================
# UPLOAD FRAUD TRANSACTIONS + LABELS
# ============================================================

def upload_fraud_batch(
    transactions,
    metadata,
    scenarios
):

    if not transactions:
        return

    # --------------------------------------------------------
    # Insert fraudulent transactions
    # --------------------------------------------------------

    (
        supabase
        .table("transactions")
        .insert(transactions)
        .execute()
    )

    labels = []

    # --------------------------------------------------------
    # Generate ground-truth labels
    # --------------------------------------------------------

    for item in metadata:

        amount = item["amount"]

        # Synthetic recovery potential.
        recoverable = round(
            amount
            * random.uniform(
                0.05,
                0.60
            ),
            2
        )

        labels.append({

            "transaction_id":
                item["transaction_id"],

            "is_fraud":
                True,

            "fraud_type":
                item["fraud_type"],

            "fraud_scenario_id":
                scenarios[
                    item["scenario"]
                ],

            "mule_wallet":
                item["mule_wallet"],

            "account_takeover":
                item["account_takeover"],

            "amount_lost":
                round(
                    amount,
                    2
                ),

            "recoverable_amount":
                recoverable
        })

    # --------------------------------------------------------
    # Insert labels
    # --------------------------------------------------------

    (
        supabase
        .table("fraud_labels")
        .insert(labels)
        .execute()
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TraceAI Fraud Injection Engine")
    print("=" * 60)

    # --------------------------------------------------------
    # LOAD DATABASE DATA
    # --------------------------------------------------------

    wallets = fetch_all(
        "wallets",
        "id,customer_id,balance,status"
    )

    devices = fetch_all(
        "devices",
        "id"
    )

    customer_devices = fetch_all(
        "customer_devices",
        "customer_id,device_id"
    )

    agents = fetch_all(
        "agents",
        "id,status"
    )

    scenarios = load_scenarios()

    # --------------------------------------------------------
    # FILTER ACTIVE DATA
    # --------------------------------------------------------

    active_wallets = [
        wallet
        for wallet in wallets
        if wallet["status"] == "active"
    ]

    active_agents = [
        agent
        for agent in agents
        if agent["status"] == "active"
    ]

    if len(active_wallets) < 2:

        raise ValueError(
            "At least two active wallets "
            "are required."
        )

    # --------------------------------------------------------
    # CUSTOMER -> KNOWN DEVICES
    # --------------------------------------------------------

    known_devices = {}

    for relation in customer_devices:

        customer_id = (
            relation["customer_id"]
        )

        known_devices.setdefault(
            customer_id,
            set()
        ).add(
            relation["device_id"]
        )

    device_ids = [
        device["id"]
        for device in devices
    ]

    # --------------------------------------------------------
    # FRAUD DISTRIBUTION
    # --------------------------------------------------------

    scenario_choices = [

        "ATO_NEW_DEVICE",

        "HIGH_VALUE_ANOMALY",

        "MULE_RAPID_TRANSFER",

        "RAPID_CASHOUT",

        "MULE_FAN_IN",

        "MULE_FAN_OUT",
    ]

    scenario_weights = [
        25,
        20,
        20,
        15,
        10,
        10
    ]

    # --------------------------------------------------------
    # BATCH HOLDERS
    # --------------------------------------------------------

    fraud_transactions = []
    fraud_metadata = []

    # --------------------------------------------------------
    # GENERATE FRAUD
    # --------------------------------------------------------

    for i in range(
        1,
        TOTAL_FRAUD + 1
    ):

        scenario = random.choices(
            scenario_choices,
            weights=scenario_weights
        )[0]

        # ----------------------------------------------------
        # SELECT SENDER
        # ----------------------------------------------------

        sender = random.choice(
            active_wallets
        )

        # ----------------------------------------------------
        # SELECT RECEIVER
        # ----------------------------------------------------

        receiver = random.choice(
            active_wallets
        )

        while (
            receiver["id"]
            == sender["id"]
        ):

            receiver = random.choice(
                active_wallets
            )

        customer_id = (
            sender["customer_id"]
        )

        normal_devices = (
            known_devices.get(
                customer_id,
                set()
            )
        )

        # ----------------------------------------------------
        # NORMAL DEVICE BY DEFAULT
        # ----------------------------------------------------

        device_id = None

        if normal_devices:

            device_id = random.choice(
                list(normal_devices)
            )

        # ====================================================
        # 1. ACCOUNT TAKEOVER
        # ====================================================

        if scenario == "ATO_NEW_DEVICE":

            device_id = choose_unknown_device(
                device_ids,
                normal_devices
            )

            amount = random.uniform(
                15_000,
                50_000
            )

            fraud_type = (
                "account_takeover"
            )

            account_takeover = True
            mule_wallet = False

        # ====================================================
        # 2. HIGH-VALUE ANOMALY
        # ====================================================

        elif (
            scenario
            == "HIGH_VALUE_ANOMALY"
        ):

            amount = random.uniform(
                20_000,
                60_000
            )

            fraud_type = (
                "high_value_anomaly"
            )

            account_takeover = False
            mule_wallet = False

        # ====================================================
        # 3. MULE RAPID TRANSFER
        # ====================================================

        elif (
            scenario
            == "MULE_RAPID_TRANSFER"
        ):

            amount = random.uniform(
                10_000,
                40_000
            )

            fraud_type = (
                "mule_transfer"
            )

            account_takeover = False
            mule_wallet = True

        # ====================================================
        # 4. RAPID CASH-OUT
        # ====================================================

        elif (
            scenario
            == "RAPID_CASHOUT"
        ):

            amount = random.uniform(
                8_000,
                35_000
            )

            fraud_type = (
                "rapid_cashout"
            )

            account_takeover = False
            mule_wallet = True

        # ====================================================
        # 5. MULE FAN-IN
        # ====================================================

        elif (
            scenario
            == "MULE_FAN_IN"
        ):

            amount = random.uniform(
                5_000,
                25_000
            )

            fraud_type = (
                "mule_fan_in"
            )

            account_takeover = False
            mule_wallet = True

        # ====================================================
        # 6. MULE FAN-OUT
        # ====================================================

        else:

            amount = random.uniform(
                5_000,
                25_000
            )

            fraud_type = (
                "mule_fan_out"
            )

            account_takeover = False
            mule_wallet = True

        amount = round(
            amount,
            2
        )

        # ----------------------------------------------------
        # ENSURE SIMULATED SENDER HAS ENOUGH BALANCE
        # ----------------------------------------------------

        sender_balance = float(
            sender.get("balance") or 0
        )

        if sender_balance < amount:

            sender["balance"] = round(
                amount
                + random.uniform(
                    1_000,
                    10_000
                ),
                2
            )

        # ----------------------------------------------------
        # DEFAULT FRAUD TRANSACTION TYPE
        # ----------------------------------------------------

        agent_id = None
        tx_type = "send_money"

        receiver_for_tx = receiver

        # ----------------------------------------------------
        # CASH-OUT HAS NO RECEIVER WALLET
        # ----------------------------------------------------

        if scenario == "RAPID_CASHOUT":

            tx_type = "cash_out"

            receiver_for_tx = None

            if active_agents:

                agent_id = random.choice(
                    active_agents
                )["id"]

        # ----------------------------------------------------
        # BUILD TRANSACTION
        # ----------------------------------------------------

        transaction = make_transaction(

            sender=sender,

            receiver=receiver_for_tx,

            device_id=device_id,

            amount=amount,

            tx_type=tx_type,

            agent_id=agent_id
        )

        fraud_transactions.append(
            transaction
        )

        fraud_metadata.append({

            "transaction_id":
                transaction["id"],

            "transaction_code":
                transaction[
                    "transaction_code"
                ],

            "scenario":
                scenario,

            "fraud_type":
                fraud_type,

            "mule_wallet":
                mule_wallet,

            "account_takeover":
                account_takeover,

            "amount":
                amount
        })

        # ----------------------------------------------------
        # UPLOAD FULL BATCH
        # ----------------------------------------------------

        if len(
            fraud_transactions
        ) >= BATCH_SIZE:

            upload_fraud_batch(
                fraud_transactions,
                fraud_metadata,
                scenarios
            )

            print(
                f"Injected "
                f"{i:,} / "
                f"{TOTAL_FRAUD:,} "
                f"fraud transactions"
            )

            fraud_transactions.clear()
            fraud_metadata.clear()

    # ========================================================
    # UPLOAD FINAL PARTIAL BATCH
    # ========================================================

    if fraud_transactions:

        upload_fraud_batch(
            fraud_transactions,
            fraud_metadata,
            scenarios
        )

        print(
            f"Injected "
            f"{TOTAL_FRAUD:,} / "
            f"{TOTAL_FRAUD:,} "
            f"fraud transactions"
        )

    # ========================================================
    # VERIFY COUNTS
    # ========================================================

    fraud_count_response = (
        supabase
        .table("fraud_labels")
        .select(
            "id",
            count="exact"
        )
        .eq(
            "is_fraud",
            True
        )
        .limit(1)
        .execute()
    )

    print()
    print("=" * 60)
    print("Fraud injection completed successfully.")
    print("=" * 60)

    print(
        "Fraud labels currently in database:",
        fraud_count_response.count
    )


if __name__ == "__main__":
    main()