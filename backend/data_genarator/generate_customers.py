import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabaseclient import supabase
 
 
fake = Faker() 
 
TOTAL_CUSTOMERS = 10_000 
BATCH_SIZE = 500 
 
 
BANGLADESH_DISTRICTS = [ 
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
 
 
OCCUPATIONS = [ 
    "Student", 
    "Teacher", 
    "Business Owner", 
    "Private Employee", 
    "Government Employee", 
    "Freelancer", 
    "Driver", 
    "Farmer", 
    "Shopkeeper", 
    "Engineer", 
    "Healthcare Worker", 
    "Delivery Rider", 
    "Technician", 
    "Homemaker", 
    "Sales Executive", 
] 
 
 
def random_registration_date(): 
    """ 
    Generate a registration date sometime 
    during the previous 3 years. 
    """ 
    days_ago = random.randint(1, 365 * 3) 
 
    registered_at = ( 
        datetime.now(timezone.utc) 
        - timedelta(days=days_ago) 
    ) 
 
    return registered_at.isoformat() 
 
 
def generate_customer(index): 
    gender = random.choice([ 
        "male", 
        "female" 
    ]) 
 
    registration_date = random_registration_date() 
 
    return { 
        "customer_code": f"CUST{index:07d}", 
 
        "full_name": fake.name(), 
 
        "gender": gender, 
 
        "age": random.randint(18, 70), 
 
        "district": random.choice( 
            BANGLADESH_DISTRICTS 
        ), 
 
        "occupation": random.choice( 
            OCCUPATIONS 
        ), 
 
        "account_status": random.choices( 
            [ 
                "active", 
                "inactive", 
                "suspended" 
            ], 
            weights=[ 
                92, 
                6, 
                2 
            ] 
        )[0], 
 
        "kyc_level": random.choices( 
            [ 
                "basic", 
                "verified", 
                "enhanced" 
            ], 
            weights=[ 
                25, 
                65, 
                10 
            ] 
        )[0], 
 
        "risk_segment": random.choices( 
            [ 
                "low", 
                "medium", 
                "high" 
            ], 
            weights=[ 
                75, 
                20, 
                5 
            ] 
        )[0], 
 
        "registered_at": registration_date, 
    } 
 
 
def upload_batch(customers): 
    response = ( 
        supabase 
        .table("customers") 
        .upsert( 
            customers, 
            on_conflict="customer_code" 
        ) 
        .execute() 
    ) 
 
    return response 
 
 
def main(): 
    print("=" * 50) 
    print("TraceAI Synthetic Customer Generator") 
    print("=" * 50) 
 
    print( 
        f"\nGenerating {TOTAL_CUSTOMERS:,} customers..." 
    ) 
 
    customers = [] 
 
    for i in range(1, TOTAL_CUSTOMERS + 1): 
 
        customer = generate_customer(i) 
 
        customers.append(customer) 
 
        if len(customers) == BATCH_SIZE: 
 
            upload_batch(customers) 
 
            print( 
                f"Uploaded {i:,} / " 
                f"{TOTAL_CUSTOMERS:,}" 
            ) 
 
            customers = [] 
 
    # Upload any remaining records 
    if customers: 
        upload_batch(customers) 
 
    print("\nCustomer generation completed.") 
 
    # Verify database count 
    response = ( 
        supabase 
        .table("customers") 
        .select( 
            "id", 
            count="exact" 
        ) 
        .limit(1) 
        .execute() 
    ) 
 
    print( 
        f"Customers currently in database: " 
        f"{response.count:,}" 
    ) 
 
 
if __name__ == "__main__": 
    main() 