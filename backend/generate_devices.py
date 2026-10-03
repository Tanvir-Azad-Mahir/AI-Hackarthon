import sys
import random
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

from faker import Faker

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)

from supabaseclient import supabase


fake = Faker()

BATCH_SIZE = 500
FETCH_SIZE = 1000


ANDROID_DEVICES = [
    ("Samsung", "Galaxy A15"),
    ("Samsung", "Galaxy A24"),
    ("Samsung", "Galaxy A34"),
    ("Xiaomi", "Redmi Note 12"),
    ("Xiaomi", "Redmi 12"),
    ("Realme", "C55"),
    ("Realme", "Narzo 50"),
    ("Vivo", "Y21"),
    ("Vivo", "Y27"),
    ("Oppo", "A57"),
    ("Oppo", "A78"),
    ("Infinix", "Hot 30"),
    ("Tecno", "Spark 10"),
]

IOS_DEVICES = [
    ("Apple", "iPhone 11"),
    ("Apple", "iPhone 12"),
    ("Apple", "iPhone 13"),
    ("Apple", "iPhone 14"),
]


def fetch_all_customers():

    customers = []
    start = 0

    while True:

        response = (
            supabase
            .table("customers")
            .select(
                "id, customer_code, district"
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


def generate_device(customer, device_number):

    # Most MFS customers will use Android
    device_type = random.choices(
        ["android", "ios"],
        weights=[92, 8]
    )[0]

    if device_type == "android":

        manufacturer, model = random.choice(
            ANDROID_DEVICES
        )

        operating_system = "Android"

        os_version = random.choice([
            "10",
            "11",
            "12",
            "13",
            "14"
        ])

    else:

        manufacturer, model = random.choice(
            IOS_DEVICES
        )

        operating_system = "iOS"

        os_version = random.choice([
            "15",
            "16",
            "17",
            "18"
        ])

    device_id = str(uuid.uuid4())

    # Primary device is usually older
    if device_number == 1:
        days_ago = random.randint(30, 800)
    else:
        days_ago = random.randint(1, 180)

    first_seen = (
        datetime.now(timezone.utc)
        - timedelta(days=days_ago)
    )

    last_seen = (
        first_seen
        + timedelta(
            days=random.randint(
                0,
                max(days_ago, 1)
            )
        )
    )

    # Avoid future timestamp
    now = datetime.now(timezone.utc)

    if last_seen > now:
        last_seen = now

    device = {
        "id": device_id,

        "device_fingerprint":
            f"DEV-{customer['customer_code']}-{device_number}",

        "device_type":
            device_type,

        "manufacturer":
            manufacturer,

        "model":
            model,

        "operating_system":
            operating_system,

        "os_version":
            os_version,

        "app_version":
            random.choice([
                "1.0.0",
                "1.1.0",
                "1.2.0",
                "1.3.1",
                "1.4.0",
                "2.0.0"
            ]),

        "ip_address":
            fake.ipv4_public(),

        "district":
            customer["district"],

        # Very small percentage of suspicious devices
        "is_emulator":
            random.random() < 0.003,

        "is_rooted":
            random.random() < 0.01,

        "first_seen_at":
            first_seen.isoformat(),

        "last_seen_at":
            last_seen.isoformat()
    }

    customer_device = {
        "customer_id":
            customer["id"],

        "device_id":
            device_id,

        "is_primary":
            device_number == 1,

        "is_trusted":
            (
                device_number == 1
                or random.random() < 0.65
            ),

        "first_used_at":
            first_seen.isoformat(),

        "last_used_at":
            last_seen.isoformat(),

        "use_count":
            random.randint(
                20,
                500
            )
            if device_number == 1
            else random.randint(
                1,
                80
            )
    }

    return device, customer_device


def upload_devices(devices):

    (
        supabase
        .table("devices")
        .insert(devices)
        .execute()
    )


def upload_customer_devices(relations):

    (
        supabase
        .table("customer_devices")
        .insert(relations)
        .execute()
    )


def main():

    print("=" * 55)
    print("TraceAI Synthetic Device Generator")
    print("=" * 55)

    customers = fetch_all_customers()

    print(
        f"\nCustomers found: "
        f"{len(customers):,}"
    )

    if not customers:
        print("No customers found.")
        return

    devices = []
    relations = []

    total_devices = 0

    for index, customer in enumerate(
        customers,
        start=1
    ):

        # Every customer gets one main device

        device, relation = generate_device(
            customer,
            1
        )

        devices.append(device)
        relations.append(relation)

        total_devices += 1

        # Around 20% have a second device

        if random.random() < 0.20:

            device, relation = generate_device(
                customer,
                2
            )

            devices.append(device)
            relations.append(relation)

            total_devices += 1

        # Upload whenever batch becomes large

        if len(devices) >= BATCH_SIZE:

            upload_devices(devices)

            upload_customer_devices(
                relations
            )

            print(
                f"Processed "
                f"{index:,} / "
                f"{len(customers):,} customers"
            )

            devices.clear()
            relations.clear()

    # Remaining rows

    if devices:

        upload_devices(devices)

        upload_customer_devices(
            relations
        )

    print("\nDevice generation completed.")

    print(
        f"Devices generated: "
        f"{total_devices:,}"
    )


if __name__ == "__main__":
    main()