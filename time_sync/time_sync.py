# time_sync.py - IT24104006 
# Member 3: J. W. C. Jananjana - Time Synchronization

import time, requests, uuid, threading
from datetime import datetime

SERVERS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

clock_offsets = {
    "http://localhost:5001": 0.0,
    "http://localhost:5002": 0.05,
    "http://localhost:5003": -0.03,
}

# ── 1. CLOCK SYNCHRONIZATION (NTP-style) ──────────────
def get_synchronized_time(server):
    try:
        t1 = time.time()
        r = requests.get(f"{server}/health", timeout=2)
        t4 = time.time()
        server_time = r.json().get('time', t4)
        offset = ((server_time - t1) + (server_time - t4)) / 2
        print(f"[NTP] {server} offset: {offset*1000:.2f}ms")
        return offset
    except:
        return 0.0

def synchronize_all_clocks():
    print("[SYNC] Synchronizing clocks across all servers...")
    for server in SERVERS:
        offset = get_synchronized_time(server)
        clock_offsets[server] = offset
    print("[SYNC] Clock synchronization complete\n")

def corrected_timestamp(server):
    return time.time() + clock_offsets.get(server, 0)

# ── 2. LOGICAL CLOCK (Lamport Timestamps) ─────────────
lamport_clock = 0
lamport_lock = threading.Lock()

def lamport_tick():
    global lamport_clock
    with lamport_lock:
        lamport_clock += 1
        return lamport_clock

def lamport_receive(received_time):
    global lamport_clock
    with lamport_lock:
        lamport_clock = max(lamport_clock, received_time) + 1
        return lamport_clock

# ── 3. SEND MESSAGE WITH CORRECTED TIMESTAMP ──────────
def send_with_timestamp(sender, content, target_server):
    logical = lamport_tick()
    physical = corrected_timestamp(target_server)
    message = {
        "id": str(uuid.uuid4()),
        "sender": sender,
        "content": content,
        "physical_time": physical,
        "logical_time": logical,
        "human_time": datetime.fromtimestamp(physical).strftime('%H:%M:%S.%f')[:-3]
    }
    try:
        r = requests.post(f"{target_server}/send", json=message, timeout=3)
        print(f"[SEND] '{content}' | logical={logical} | time={message['human_time']}")
        return r.status_code == 200
    except Exception as e:
        print(f"[SEND] Failed: {e}")
        return False

# ── 4. REORDER OUT-OF-SEQUENCE MESSAGES ───────────────
def reorder_messages(messages):
    sorted_msgs = sorted(messages,
        key=lambda m: (m.get('logical_time', 0), m.get('physical_time', 0)))
    print(f"[ORDER] Reordered {len(sorted_msgs)} messages by logical clock")
    return sorted_msgs

def get_ordered_messages():
    for server in SERVERS:
        try:
            r = requests.get(f"{server}/messages", timeout=3)
            msgs = r.json()
            return reorder_messages(msgs)
        except:
            continue
    return []

if __name__ == "__main__":
    print("=== Time Synchronization Demo ===\n")
    synchronize_all_clocks()

    send_with_timestamp("Alice", "First message", SERVERS[0])
    time.sleep(0.1)
    send_with_timestamp("Bob", "Second message", SERVERS[1])
    time.sleep(0.1)
    send_with_timestamp("Alice", "Third message", SERVERS[2])

    print("\n--- Ordered messages ---")
    ordered = get_ordered_messages()
    for i, msg in enumerate(ordered, 1):
        print(f"  {i}. [{msg.get('human_time','?')}] "
              f"logical={msg.get('logical_time','?')} "
              f"| {msg.get('sender')}: {msg.get('content')}")