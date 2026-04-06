# data_replication/data_replication.py
# Member 2: N. P. K. N. Pathirana - Data Replication & Consistency
import requests, time, uuid, hashlib, json

SERVERS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

seen_message_ids = set()

# ── 1. QUORUM-BASED REPLICATION ────────────────────────
# Quorum means: at least 2 out of 3 servers must confirm
# before we say the message was saved successfully
QUORUM = 2

def replicate_with_quorum(message):
    message['id'] = message.get('id', str(uuid.uuid4()))
    confirmations = 0
    for server in SERVERS:
        try:
            r = requests.post(f"{server}/send", json=message, timeout=3)
            if r.status_code == 200:
                confirmations += 1
                print(f"[QUORUM] Confirmed by {server} ({confirmations}/{QUORUM})")
                if confirmations >= QUORUM:
                    print(f"[QUORUM] ✓ Quorum reached! Message safely stored.")
                    return True
        except Exception as e:
            print(f"[QUORUM] {server} failed: {e}")
    print(f"[QUORUM] ✗ Only {confirmations} confirmations - below quorum!")
    return False

# ── 2. DEDUPLICATION ───────────────────────────────────
# Prevent the same message from being saved twice
def deduplicate_and_send(message):
    msg_id = message.get('id', str(uuid.uuid4()))
    message['id'] = msg_id

    # Create a fingerprint of the message content
    fingerprint = hashlib.md5(
        f"{message.get('sender')}{message.get('content')}".encode()
    ).hexdigest()

    if fingerprint in seen_message_ids:
        print(f"[DEDUP] Duplicate detected! Skipping: {message.get('content')}")
        return False

    seen_message_ids.add(fingerprint)
    print(f"[DEDUP] New message - forwarding to quorum replication")
    return replicate_with_quorum(message)

# ── 3. CONSISTENCY CHECK ───────────────────────────────
# Check all servers have the same messages
def check_consistency():
    print("\n[CONSISTENCY] Checking all servers...")
    all_counts = {}
    for server in SERVERS:
        try:
            r = requests.get(f"{server}/messages", timeout=3)
            msgs = r.json()
            all_counts[server] = len(msgs)
            print(f"  {server}: {len(msgs)} messages")
        except:
            all_counts[server] = -1
            print(f"  {server}: UNREACHABLE")

    counts = [v for v in all_counts.values() if v >= 0]
    if len(set(counts)) == 1:
        print("[CONSISTENCY] ✓ All servers are consistent!")
    else:
        print("[CONSISTENCY] ✗ Servers are out of sync - need repair")
        repair_consistency()

# ── 4. CONSISTENCY REPAIR ─────────────────────────────
def repair_consistency():
    print("[REPAIR] Starting consistency repair...")
    all_messages = {}
    for server in SERVERS:
        try:
            r = requests.get(f"{server}/messages", timeout=3)
            for msg in r.json():
                all_messages[msg.get('id', '')] = msg
        except:
            pass

    merged = list(all_messages.values())
    for server in SERVERS:
        try:
            requests.post(f"{server}/sync",
                         json={"messages": merged}, timeout=5)
            print(f"[REPAIR] Synced {len(merged)} messages to {server}")
        except:
            pass

# ── 5. DEMO ────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Data Replication Demo ===\n")

    # Send messages with quorum
    messages = [
        {"sender": "Alice", "content": "Hello Bob!", "timestamp": time.time()},
        {"sender": "Bob", "content": "Hi Alice!", "timestamp": time.time()},
        {"sender": "Alice", "content": "Meeting at 3pm", "timestamp": time.time()},
    ]

    for msg in messages:
        deduplicate_and_send(msg)
        time.sleep(0.3)

    # Try sending a duplicate
    print("\n--- Testing deduplication ---")
    deduplicate_and_send({"sender": "Alice", "content": "Hello Bob!", "timestamp": time.time()})

    # Check consistency
    time.sleep(1)
    check_consistency()