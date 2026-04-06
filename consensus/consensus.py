"""
Consensus & Agreement (Member 4)

Leader election, majority-based proposal, commit to all reachable servers,
partition awareness, and cross-server message-count verification.
"""
import requests
import time
import uuid

SERVERS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003",
]

current_leader = None
current_term = 0


def elect_leader():
    """Pick a leader: each candidate is scored by how many peers respond to /health."""
    global current_leader, current_term
    current_term += 1
    print(f"\n[ELECTION] Starting election for term {current_term}")

    votes = {}
    for candidate in SERVERS:
        vote_count = 0
        for voter in SERVERS:
            try:
                r = requests.get(f"{voter}/health", timeout=2)
                if r.status_code == 200:
                    vote_count += 1
            except Exception:
                pass
        votes[candidate] = vote_count
        print(f"[ELECTION] {candidate} got {vote_count} votes")

    winner = max(votes, key=votes.get)
    current_leader = winner
    print(f"[ELECTION] Leader elected: {winner}")
    return winner


def get_leader():
    global current_leader
    if current_leader is None:
        return elect_leader()
    return current_leader


def propose_message(message):
    """
    Coordinator path: require a majority of servers alive, then POST the same
    payload to each server /send (2-of-3 with three servers).
    """
    leader = get_leader()
    message["id"] = message.get("id", str(uuid.uuid4()))
    message["term"] = current_term

    content = message.get("content", "")
    print(f"\n[CONSENSUS] Leader {leader} is proposing message: {content}")

    approvals = 0
    majority = len(SERVERS) // 2 + 1

    for server in SERVERS:
        try:
            r = requests.get(f"{server}/health", timeout=2)
            if r.status_code == 200:
                approvals += 1
                print(f"[CONSENSUS] {server} approved (alive)")
        except Exception:
            print(f"[CONSENSUS] {server} did not respond")

    if approvals >= majority:
        print(f"[CONSENSUS] Majority reached ({approvals}/{len(SERVERS)})")
        committed = 0
        for server in SERVERS:
            try:
                r = requests.post(f"{server}/send", json=message, timeout=3)
                if r.status_code == 200:
                    committed += 1
            except Exception:
                pass
        print(f"[CONSENSUS] Message committed to {committed} server(s)")
        return True

    print(f"[CONSENSUS] No majority. Message rejected.")
    return False


def simulate_partition(available_servers):
    """Demo helper: majority exists iff len(available) > half of cluster."""
    print(f"\n[PARTITION] Available servers: {available_servers}")
    majority = len(SERVERS) // 2 + 1

    if len(available_servers) >= majority:
        print("[PARTITION] Majority exists. System can continue.")
        return True

    print("[PARTITION] No majority. System must pause.")
    return False


def verify_agreement():
    """Compare message counts across /messages on all servers."""
    print("\n[VERIFY] Checking whether all servers agree...")
    counts = {}

    for server in SERVERS:
        try:
            r = requests.get(f"{server}/messages", timeout=3)
            counts[server] = len(r.json())
            print(f"{server}: {counts[server]} messages")
        except Exception:
            counts[server] = -1
            print(f"{server}: UNREACHABLE")

    alive_counts = [c for c in counts.values() if c >= 0]

    if not alive_counts:
        print("[VERIFY] No reachable servers.")
        return

    if len(set(alive_counts)) == 1:
        print("[VERIFY] All working servers agree (same message count).")
    else:
        print("[VERIFY] Servers do not agree (different message counts).")


if __name__ == "__main__":
    print("=== Consensus & Agreement Demo ===")

    elect_leader()

    demo_messages = [
        {
            "sender": "Alice",
            "receiver": "broadcast",
            "content": "Consensus message 1",
            "timestamp": time.time(),
        },
        {
            "sender": "Bob",
            "receiver": "broadcast",
            "content": "Consensus message 2",
            "timestamp": time.time(),
        },
    ]

    for msg in demo_messages:
        propose_message(msg)
        time.sleep(0.5)

    verify_agreement()

    print("\n--- Partition test ---")
    simulate_partition(
        ["http://localhost:5001", "http://localhost:5002"]
    )
    simulate_partition(["http://localhost:5001"])
