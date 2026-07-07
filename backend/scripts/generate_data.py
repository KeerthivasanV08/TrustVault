import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
NUM_USERS = 30000
NUM_TRANSACTIONS = 30000

BASE_TIME = datetime(2025, 3, 1, 10, 0)

AML_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = AML_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
REFERENCE_DIR = DATA_DIR / "reference"
RAW_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)


def resolve_data_file(primary_dir, fallback_dir, filename):
    primary_path = primary_dir / filename
    if primary_path.exists():
        return primary_path

    fallback_path = fallback_dir / filename
    if fallback_path.exists():
        return fallback_path

    return primary_path

# -----------------------------
# LOAD REFERENCE DATA
# -----------------------------
device_ref = pd.read_csv(
    resolve_data_file(
        RAW_DIR,
        RAW_DIR,
        "device_age_reference.csv"
    )
)

ip_ref = pd.read_csv(
    resolve_data_file(
        REFERENCE_DIR,
        REFERENCE_DIR,
        "ip_risk_reference.csv"
    )
)

# -----------------------------
# CLEAN / NORMALIZE IP DATA
# -----------------------------
bool_cols = [
    "is_proxy",
    "is_hosting",
    "is_vpn"
]

for col in bool_cols:
    ip_ref[col] = (
        ip_ref[col]
        .astype(str)
        .str.lower()
        .isin(["1", "true", "yes"])
    )

# normalize risk level
if ip_ref["risk_level"].dtype == object:
    mapping = {
        "low": 10,
        "medium": 50,
        "high": 90
    }

    ip_ref["risk_level"] = (
        ip_ref["risk_level"]
        .astype(str)
        .str.lower()
        .map(mapping)
        .fillna(50)
    )

# -----------------------------
# FILTER PROFILES
# -----------------------------
normal_ips = ip_ref[
    (~ip_ref["is_vpn"]) &
    (~ip_ref["is_hosting"]) &
    (~ip_ref["is_proxy"])
]

risky_ips = ip_ref[
    (ip_ref["is_vpn"]) |
    (ip_ref["is_hosting"]) |
    (ip_ref["is_proxy"])
]

high_risk_ips = ip_ref[
    (ip_ref["is_hosting"]) |
    (ip_ref["is_proxy"])
]

modern_devices = device_ref[
    device_ref["Released Year"] >= 2018
]

old_devices = device_ref[
    device_ref["Released Year"] < 2015
]

# -----------------------------
# HELPERS
# -----------------------------
def ts(minutes):
    return (
        BASE_TIME + timedelta(minutes=minutes)
    ).strftime("%Y-%m-%d %H:%M:%S")


def generate_ip_from_network(network):
    """
    Convert CIDR/prefix into random realistic IP
    """

    network = str(network)

    if "/" in network:
        prefix = network.split("/")[0]
    else:
        prefix = network

    parts = prefix.split(".")

    while len(parts) < 4:
        parts.append(str(random.randint(1, 254)))

    parts[2] = str(random.randint(1, 254))
    parts[3] = str(random.randint(1, 254))

    return ".".join(parts[:4])

# -----------------------------
# USER GENERATION
# -----------------------------
users = []

# -----------------------------
# NORMAL USERS (70%)
# -----------------------------
for i in range(21000):

    ip_row = normal_ips.sample(1).iloc[0]
    dev_row = modern_devices.sample(1).iloc[0]

    registered_imsi = f"IMSI_{100000+i}"

    users.append({
        "user_id": f"U{i}",

        "kyc_status": "verified",

        "kyc_city": ip_row["city"],

        "device_id": f"DEV_{i}",

        "device_model_name":
            f"{dev_row['Brand']} {dev_row['Model']}",

        "device_year":
            dev_row["Released Year"],

        "root_status": False,

        "app_cloner_flag": False,

        "ip_address":
            generate_ip_from_network(
                ip_row["network"]
            ),

        "vpn_detected":
            bool(ip_row["is_vpn"]),

        "isp_name":
            ip_row["as_name"],

        "registered_imsi":
            registered_imsi,

        "current_imsi":
            registered_imsi,

        "sim_present": True,

        "sim_slot_count":
            random.choice([1, 2]),

        "biometric_enabled": True,

        "onboarding_speed_ms":
            random.randint(120000, 420000),

        "created_at":
            ts(random.randint(0, 100000)),
    })

# -----------------------------
# MULE CLUSTERS (20%)
# -----------------------------
for i in range(21000, 27000):

    cluster = i // 6

    ip_row = risky_ips.sample(1).iloc[0]

    dev_row = old_devices.sample(1).iloc[0]

    registered_imsi = f"IMSI_{100000+i}"

    users.append({
        "user_id": f"U{i}",

        "kyc_status": "partial",

        "kyc_city": ip_row["city"],

        "device_id":
            f"MULE_DEVICE_{cluster}",

        "device_model_name":
            f"{dev_row['Brand']} {dev_row['Model']}",

        "device_year":
            dev_row["Released Year"],

        "root_status": True,

        "app_cloner_flag": True,

        "ip_address":
            generate_ip_from_network(
                ip_row["network"]
            ),

        "vpn_detected":
            bool(ip_row["is_vpn"]),

        "isp_name":
            ip_row["as_name"],

        "registered_imsi":
            registered_imsi,

        "current_imsi":
            f"SWAP_{random.randint(1,9999)}",

        "sim_present": True,

        "sim_slot_count":
            random.choice([2, 3, 4]),

        "biometric_enabled": False,

        "onboarding_speed_ms":
            random.randint(5000, 40000),

        "created_at":
            ts(random.randint(0, 2000)),
    })

# -----------------------------
# BOT / HIGH-RISK USERS (10%)
# -----------------------------
for i in range(27000, 30000):

    ip_row = high_risk_ips.sample(1).iloc[0]

    dev_name = (
        "Android_Emulator_x86"
        if random.random() > 0.5
        else "Legacy_Device_v1"
    )

    dev_year = (
        2012
        if "Emulator" in dev_name
        else 2008
    )

    users.append({
        "user_id": f"U{i}",

        "kyc_status": "failed",

        "kyc_city": "Unknown",

        "device_id": f"EMU_{i//3}",

        "device_model_name": dev_name,

        "device_year": dev_year,

        "root_status": True,

        "app_cloner_flag": True,

        "ip_address":
            generate_ip_from_network(
                ip_row["network"]
            ),

        "vpn_detected": True,

        "isp_name":
            ip_row["as_name"],

        "registered_imsi":
            f"IMSI_{100000+i}",

        "current_imsi": "NONE",

        "sim_present": False,

        "sim_slot_count": 0,

        "biometric_enabled": False,

        "onboarding_speed_ms":
            random.randint(1000, 10000),

        "created_at":
            ts(random.randint(0, 500)),
    })

users_df = pd.DataFrame(users)

users_df.to_csv(
    RAW_DIR / "users.csv",
    index=False
)

print("✅ users.csv created")

# -----------------------------
# TRANSACTION GENERATION
# -----------------------------
transactions = []

all_user_ids = users_df["user_id"].tolist()

balances = {
    uid: random.randint(15000, 150000)
    for uid in all_user_ids
}

master_accounts = random.sample(
    all_user_ids[:5000],
    50
)

for i in range(NUM_TRANSACTIONS):

    if i < 18000:

        sender = random.choice(
            all_user_ids[:21000]
        )

        receiver = random.choice(
            all_user_ids[:21000]
        )

        while receiver == sender:
            receiver = random.choice(
                all_user_ids[:21000]
            )

        amount = random.randint(100, 15000)

        fraud_type = "normal"

    elif i < 27000:

        sender = random.choice(
            all_user_ids[21000:27000]
        )

        receiver = random.choice(
            master_accounts
        )

        amount = min(
            random.randint(5000, 30000),
            max(balances[sender] - 100, 1000)
        )

        fraud_type = "mule"

    else:

        sender = random.choice(
            all_user_ids[27000:]
        )

        receiver = random.choice(
            all_user_ids
        )

        amount = min(
            random.randint(20000, 80000),
            max(balances[sender] - 50, 5000)
        )

        fraud_type = "burst"

    sender_before = balances[sender]

    if sender_before <= amount:
        amount = max(
            100,
            sender_before * 0.7
        )

    sender_after = sender_before - amount

    balances[sender] = sender_after

    sender_row = users_df[
        users_df["user_id"] == sender
    ].iloc[0]

    transactions.append({
        "trans_id": f"T{i}",

        "sender_id": sender,

        "receiver_id": receiver,

        "amount": round(amount, 2),

        "transaction_type":
            (
                "UPI"
                if fraud_type == "normal"
                else random.choice(
                    ["IMPS", "RTGS"]
                )
            ),

        "channel":
            random.choice(
                ["Mobile", "Web"]
            ),

        "sender_bal_before":
            round(sender_before, 2),

        "sender_bal_after":
            round(sender_after, 2),

        "receiver_bal_after":
            random.randint(5000, 300000),

        "timestamp":
            ts(random.randint(0, 120000)),

        "location":
            sender_row["kyc_city"],

        "is_sim_bound":
            (
                sender_row["registered_imsi"]
                ==
                sender_row["current_imsi"]
            ),

        "device_id":
            sender_row["device_id"],

        "time_to_pay_ms":
            (
                random.randint(12000, 60000)
                if fraud_type == "normal"
                else random.randint(500, 2500)
            ),
    })

transactions_df = pd.DataFrame(transactions)

transactions_df.to_csv(
    RAW_DIR / "transactions.csv",
    index=False
)

print("✅ transactions.csv created")
print("✅ Data generation complete")