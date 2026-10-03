import sys
import random
from pathlib import Path
from datetime import datetime, timezone

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

from supabaseclient import supabase


BATCH_SIZE = 500
FETCH_SIZE = 1000


def fetch_all_customers():
    """
    Fetch all synthetic customers from Supabase.
    Supabase commonly returns limited rows per request,
    so we paginate.
    """

    customers = []
    start = 0

    while True:
        response = (
            supabase
            .table("customers")
            .select(
                "id, customer_code, account_status, occupation"
            )
            .range(
                start,
                start + FETCH_SIZE - 1
            )
            .execute()
        )

        rows = response.data

        if not rows:
            break

        customers.extend(rows)

        print(
            f"Fetched {len(customers):,} customers"
        )

        if len(rows) < FETCH_SIZE:
            break

        start += FETCH_SIZE

    return customers


def determine_wallet_type(customer):
    occupation = customer.get("occupation")

    if occupation in [
        "Business Owner",
        "Shopkeeper"
    ]:
        return random.choices(
            ["business", "personal"],
            weights=[70, 30]
        )[0]

    if occupation in [
        "Private Employee",
        "Government Employee",
        "Teacher",
        "Engineer",
        "Healthcare Worker",
        "Sales Executive"
    ]:
        return random.choices(
            ["salary", "personal"],
            weights=[40, 60]
        )[0]

    return random.choices(
        [
            "personal",
            "remittance"
        ],
        weights=[
            95,
            5
        ]
    )[0]


def generate_balance(wallet_type):
    """
    Generate a positively skewed wallet balance.

    Most users have relatively small balances,
    while a smaller number hold larger balances.
    """

    if wallet_type == "business":
        balance = random.lognormvariate(
            9.0,
            0.9
        )

        return round(
            min(balance, 150000),
            2
        )

    if wallet_type == "salary":
        balance = random.lognormvariate(
            8.0,
            0.9
        )

        return round(
            min(balance, 80000),
            2
        )

    balance = random.lognormvariate(
        7.2,
        1.0
    )

    return round(
        min(balance, 50000),
        2
    )


def generate_wallet(customer, index):

    wallet_type = determine_wallet_type(
        customer
    )

    customer_status = customer.get(
        "account_status"
    )

    if customer_status == "suspended":
        wallet_status = "suspended"
    else:
        wallet_status = random.choices(
            [
                "active",
                "restricted"
            ],
            weights=[
                98,
                2
            ]
        )[0]

    return {
        "wallet_number":
            f"WLT{index:07d}",

        "customer_id":
            customer["id"],

        "wallet_type":
            wallet_type,

        "balance":
            generate_balance(
                wallet_type
            ),

        "status":
            wallet_status,

        "opened_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }


def upload_batch(wallets):

    response = (
        supabase
        .table("wallets")
        .upsert(
            wallets,
            on_conflict="wallet_number"
        )
        .execute()
    )

    return response


def main():

    print("=" * 50)
    print("TraceAI Synthetic Wallet Generator")
    print("=" * 50)

    customers = fetch_all_customers()

    print(
        f"\nTotal customers found: "
        f"{len(customers):,}"
    )

    if not customers:
        print(
            "No customers found. "
            "Stopping."
        )
        return

    wallets = []

    for index, customer in enumerate(
        customers,
        start=1
    ):

        wallet = generate_wallet(
            customer,
            index
        )

        wallets.append(wallet)

        if len(wallets) >= BATCH_SIZE:

            upload_batch(wallets)

            print(
                f"Uploaded {index:,} / "
                f"{len(customers):,} wallets"
            )

            wallets.clear()

    if wallets:
        upload_batch(wallets)

    print(
        "\nWallet generation completed."
    )

    response = (
        supabase
        .table("wallets")
        .select(
            "id",
            count="exact"
        )
        .limit(1)
        .execute()
    )

    print(
        f"Wallets currently in database: "
        f"{response.count:,}"
    )


if __name__ == "__main__":
    main()