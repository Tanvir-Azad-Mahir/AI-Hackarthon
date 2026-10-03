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

TOTAL_AGENTS = 500
BATCH_SIZE = 100


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


def generate_agent(index):

    district = random.choice(DISTRICTS)

    return {
        "agent_code": f"AGT{index:06d}",

        "agent_name": fake.name(),

        "district": district,

        "area": fake.street_name(),

        "cash_balance": round(
            random.uniform(
                10_000,
                250_000
            ),
            2
        ),

        "digital_balance": round(
            random.uniform(
                10_000,
                250_000
            ),
            2
        ),

        "status": random.choices(
            [
                "active",
                "inactive",
                "restricted"
            ],
            weights=[
                96,
                3,
                1
            ]
        )[0],

        "risk_level": random.choices(
            [
                "low",
                "medium",
                "high"
            ],
            weights=[
                80,
                17,
                3
            ]
        )[0],

        "registered_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


def upload_batch(agents):

    return (
        supabase
        .table("agents")
        .upsert(
            agents,
            on_conflict="agent_code"
        )
        .execute()
    )


def main():

    print("=" * 50)
    print("TraceAI Agent Generator")
    print("=" * 50)

    agents = []

    for i in range(
        1,
        TOTAL_AGENTS + 1
    ):

        agents.append(
            generate_agent(i)
        )

        if len(agents) >= BATCH_SIZE:

            upload_batch(agents)

            print(
                f"Uploaded {i:,} / "
                f"{TOTAL_AGENTS:,} agents"
            )

            agents.clear()

    if agents:
        upload_batch(agents)

    print("\nAgent generation completed.")

    response = (
        supabase
        .table("agents")
        .select(
            "id",
            count="exact"
        )
        .limit(1)
        .execute()
    )

    print(
        f"Agents in database: "
        f"{response.count:,}"
    )


if __name__ == "__main__":
    main()