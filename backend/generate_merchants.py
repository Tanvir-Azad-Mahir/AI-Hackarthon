import sys
import random
from pathlib import Path
from datetime import datetime, timezone

from faker import Faker

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

from supabaseclient import supabase


fake = Faker()

TOTAL_MERCHANTS = 1000
BATCH_SIZE = 200


DISTRICTS = [
    "Dhaka",
    "Chattogram",
    "Cumilla",
    "Sylhet",
    "Rajshahi",
    "Khulna",
    "Barishal",
    "Rangpur",
    "Mymensingh",
    "Gazipur",
    "Narayanganj",
    "Bogura",
    "Jashore",
    "Noakhali",
    "Feni",
    "Cox's Bazar",
    "Tangail",
    "Faridpur",
    "Kushtia",
    "Dinajpur",
]


MERCHANT_CATEGORIES = [
    "Grocery",
    "Restaurant",
    "Pharmacy",
    "Electronics",
    "Clothing",
    "Education",
    "Transport",
    "Healthcare",
    "Utility",
    "E-commerce",
    "Mobile Shop",
    "Department Store",
    "Fuel Station",
    "Travel",
    "Entertainment",
]


def generate_merchant(index):

    category = random.choice(
        MERCHANT_CATEGORIES
    )

    return {
        "merchant_code":
            f"MER{index:06d}",

        "merchant_name":
            fake.company(),

        "merchant_category":
            category,

        "district":
            random.choice(DISTRICTS),

        "area":
            fake.street_name(),

        "status":
            random.choices(
                [
                    "active",
                    "inactive",
                    "restricted"
                ],
                weights=[
                    97,
                    2,
                    1
                ]
            )[0],

        "risk_level":
            random.choices(
                [
                    "low",
                    "medium",
                    "high"
                ],
                weights=[
                    85,
                    13,
                    2
                ]
            )[0],

        "registered_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


def upload_batch(merchants):

    return (
        supabase
        .table("merchants")
        .upsert(
            merchants,
            on_conflict="merchant_code"
        )
        .execute()
    )


def main():

    print("=" * 50)
    print("TraceAI Merchant Generator")
    print("=" * 50)

    merchants = []

    for i in range(
        1,
        TOTAL_MERCHANTS + 1
    ):

        merchants.append(
            generate_merchant(i)
        )

        if len(merchants) >= BATCH_SIZE:

            upload_batch(merchants)

            print(
                f"Uploaded {i:,} / "
                f"{TOTAL_MERCHANTS:,} merchants"
            )

            merchants.clear()

    if merchants:
        upload_batch(merchants)

    print(
        "\nMerchant generation completed."
    )

    response = (
        supabase
        .table("merchants")
        .select(
            "id",
            count="exact"
        )
        .limit(1)
        .execute()
    )

    print(
        f"Merchants in database: "
        f"{response.count:,}"
    )


if __name__ == "__main__":
    main()