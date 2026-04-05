# fault_tolerance/fault_tolerance.py
# Member 1: S. L. Wijewardhana - Fault Tolerance

import requests
import time
import threading
import uuid
from datetime import datetime

SERVERS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

# Track which servers are alive
server_status = {s: True for s in SERVERS}
status_lock   = threading.Lock()


# ─────────────────────────────────────────────────────────────
# PART 1: FAILURE DETECTION (Heartbeat)
# ─────────────────────────────────────────────────────────────

def check_health(server):
    """Ping one server and update its status."""
    try:
        r = requests.get(f"{server}/health", timeout=2)
        if r.status_code == 200:
            with status_lock:
                was_down = not server_status[server]
                server_status[server] = True
            if was_down:
                print(f"[RECOVERY] {server} is back online at {now()}")
                threading.Thread(
                    target=recover_server,
                    args=(server,),
                    daemon=True
                ).start()
        else:
            mark_down(server)
    except:
        mark_down(server)

def mark_down(server):
    """Mark a server as down and log it."""
    with status_lock:
        was_alive = server_status[server]
        server_status[server] = False
    if was_alive:
        print(f"[FAILURE] {server} went DOWN at {now()}")

def heartbeat_monitor():
    """
    Runs forever in a background thread.
    Checks all servers every 3 seconds.
    """
    print("[MONITOR] Heartbeat monitor started")
    while True:
        for server in SERVERS:
            check_health(server)
        time.sleep(3)

def get_alive_servers():
    """Return list of servers currently alive."""
    with status_lock:
        return [s for s in SERVERS if server_status[s]]

def get_status_report():
    """Print a status summary of all servers."""
    print("\n--- Server Status ---")
    with status_lock:
        for s, alive in server_status.items():
            status = "ALIVE" if alive else "DOWN"
            print(f"  {s} : {status}")
    print()


# ─────────────────────────────────────────────────────────────
# PART 2: MESSAGE REPLICATION
# ─────────────────────────────────────────────────────────────

def replicate_message(message):
    """
    Send message to all alive servers simultaneously.
    Returns number of servers that confirmed.
    """
    if 'id' not in message:
        message['id'] = str(uuid.uuid4())
    if 'timestamp' not in message:
        message['timestamp'] = time.time()

    alive = get_alive_servers()
    if not alive:
        print("[REPLICATE] ERROR: No servers are alive!")
        return 0

    success_count = 0
    print(f"[REPLICATE] Sending to {len(alive)} alive server(s)...")

    for server in alive:
        try:
            r = requests.post(
                f"{server}/send",
                json=message,
                timeout=3
            )
            if r.status_code == 200:
                success_count += 1
                print(f"[REPLICATE]  OK {server}")
            else:
                print(f"[REPLICATE]  FAIL {server} "
                      f"returned {r.status_code}")
        except:
            print(f"[REPLICATE]  FAIL {server} unreachable")
            mark_down(server)

    print(f"[REPLICATE] Stored on "
          f"{success_count}/{len(SERVERS)} servers\n")
    return success_count


# ─────────────────────────────────────────────────────────────
# PART 3: AUTOMATIC FAILOVER
# ─────────────────────────────────────────────────────────────

def get_messages_with_failover():
    """
    Try to get messages from servers in order.
    If one fails, automatically move to the next.
    """
    alive = get_alive_servers()
    if not alive:
        print("[FAILOVER] All servers are down!")
        return []

    for server in alive:
        try:
            print(f"[FAILOVER] Trying {server}...")
            r = requests.get(f"{server}/messages", timeout=3)
            if r.status_code == 200:
                msgs = r.json()
                print(f"[FAILOVER] Got {len(msgs)} "
                      f"messages from {server}")
                return msgs
        except:
            print(f"[FAILOVER] {server} failed, "
                  f"trying next server...")
            mark_down(server)

    print("[FAILOVER] Could not retrieve messages "
          "from any server")
    return []


# ─────────────────────────────────────────────────────────────
# PART 4: MESSAGE RECOVERY
# ─────────────────────────────────────────────────────────────

def recover_server(recovered_server):
    """
    Copy all messages from a healthy server to
    the server that just came back online.
    """
    print(f"[RECOVERY] Starting recovery "
          f"for {recovered_server}...")

    source = None
    for server in SERVERS:
        if server != recovered_server:
            with status_lock:
                if server_status[server]:
                    source = server
                    break

    if not source:
        print("[RECOVERY] No healthy server found "
              "to recover from")
        return

    try:
        r = requests.get(f"{source}/messages", timeout=5)
        if r.status_code == 200:
            msgs = r.json()
            r2   = requests.post(
                f"{recovered_server}/sync",
                json={"messages": msgs},
                timeout=10
            )
            if r2.status_code == 200:
                result = r2.json()
                print(f"[RECOVERY] Pushed "
                      f"{result.get('added')} new messages "
                      f"to {recovered_server}")
            else:
                print("[RECOVERY] Sync failed")
    except Exception as e:
        print(f"[RECOVERY] Error: {e}")


# ─────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────

def now():
    return datetime.now().strftime('%H:%M:%S')

def start_monitor():
    """Start the heartbeat monitor in background."""
    t = threading.Thread(target=heartbeat_monitor, daemon=True)
    t.start()
    return t


# ─────────────────────────────────────────────────────────────
# MAIN — Interactive demo
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  FAULT TOLERANCE DEMO")
    print("  Member 1: S. L. Wijewardhana")
    print("=" * 50)

    start_monitor()
    time.sleep(1)
    get_status_report()

    print("Commands: send | read | status | quit\n")

    while True:
        try:
            cmd = input("Command: ").strip().lower()

            if cmd == "quit":
                print("Stopped.")
                break

            elif cmd == "send":
                sender   = input("  Your name : ").strip()
                receiver = input("  Send to   : ").strip()
                content  = input("  Message   : ").strip()

                if not sender or not receiver or not content:
                    print("  Please fill in all fields.\n")
                    continue

                msg = {
                    "id":        str(uuid.uuid4()),
                    "sender":    sender,
                    "receiver":  receiver,
                    "content":   content,
                    "timestamp": time.time()
                }
                replicate_message(msg)

            elif cmd == "read":
                msgs = get_messages_with_failover()
                if msgs:
                    print(f"\n--- {len(msgs)} messages ---")
                    for m in msgs:
                        print(f"  [{m.get('sender')} -> "
                              f"{m.get('receiver')}]: "
                              f"{m.get('content')}")
                    print()

            elif cmd == "status":
                get_status_report()

            else:
                print("  Unknown command. "
                      "Use: send | read | status | quit")

        except KeyboardInterrupt:
            print("\nStopped.")
            break