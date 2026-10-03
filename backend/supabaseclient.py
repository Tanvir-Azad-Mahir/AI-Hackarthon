import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing")

if not SUPABASE_SECRET_KEY:
    raise ValueError("SUPABASE_SECRET_KEY is missing")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)

print("Supabase client created successfully.")

try:
    response = (
        supabase
        .table("fraud_scenarios")
        .select("*")
        .execute()
    )

    print("\nConnected to Supabase database successfully.")
    print("Fraud scenarios found:", len(response.data))

    for row in response.data:
        print(
            row["scenario_code"],
            "->",
            row["scenario_name"]
        )

except Exception as e:
    print("\nDatabase query failed:")
    print(e)