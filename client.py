# client.py - Interactive client to send and read messages
import requests
import uuid
import time

SERVERS = [
    "http://localhost:5001",
    "http://localhost:5002",
    "http://localhost:5003"
]

def send_message(sender, receiver, content, port=5001):
    payload = {
        "id":        str(uuid.uuid4()),
        "sender":    sender,
        "receiver":  receiver,
        "content":   content,
        "timestamp": time.time()
    }
    try:
        r = requests.post(
            f"http://localhost:{port}/send",
            json=payload,
            timeout=3
        )
        print(f"[SENT] -> {r.json()}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def get_messages(port=5001):
    try:
        r = requests.get(
            f"http://localhost:{port}/messages",
            timeout=3
        )
        msgs = r.json()
        print(f"\n--- {len(msgs)} messages ---")
        for i, m in enumerate(msgs, 1):
            print(f"  {i}. [{m.get('sender')} -> "
                  f"{m.get('receiver')}]: {m.get('content')}")
        print()
        return msgs
    except Exception as e:
        print(f"[ERROR] {e}")
        return []

def check_all_servers():
    print("\n--- Server Status ---")
    for port in [5001, 5002, 5003]:
        try:
            r = requests.get(
                f"http://localhost:{port}/health",
                timeout=2
            )
            info = r.json()
            print(f"  Port {port} ({info.get('server')}): "
                  f"ALIVE | Messages: {info.get('message_count')}")
        except:
            print(f"  Port {port}: DOWN")
    print()

if __name__ == "__main__":
    print("=" * 50)
    print("  MESSAGING CLIENT")
    print("=" * 50)

    while True:
        print("\nWhat do you want to do?")
        print("  1. Send a message")
        print("  2. Read messages")
        print("  3. Check server status")
        print("  4. Quit")

        choice = input("\nChoice [1-4]: ").strip()

        if choice == "1":
            sender      = input("Your name : ").strip()
            receiver    = input("Send to   : ").strip()
            content     = input("Message   : ").strip()
            print("Which server? 1=5001  2=5002  3=5003")
            port_choice = input("Server [1]: ").strip() or "1"
            port        = [5001, 5002, 5003][int(port_choice) - 1]

            if sender and receiver and content:
                send_message(sender, receiver, content, port)
            else:
                print("Please fill in all fields.")

        elif choice == "2":
            print("Which server? 1=5001  2=5002  3=5003")
            port_choice = input("Server [1]: ").strip() or "1"
            port        = [5001, 5002, 5003][int(port_choice) - 1]
            get_messages(port)

        elif choice == "3":
            check_all_servers()

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Enter 1, 2, 3 or 4.")
            