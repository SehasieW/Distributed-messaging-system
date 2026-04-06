# server.py - Shared base server used by all members
from flask import Flask, request, jsonify
import json, os, time

app = Flask(__name__)
messages = []
SERVER_ID = os.environ.get("SERVER_ID", "server1")
PORT = int(os.environ.get("PORT", 5000))

@app.route('/send', methods=['POST'])
def receive_message():
    data = request.json
    data['received_at'] = time.time()
    data['received_by'] = SERVER_ID
    messages.append(data)
    save_messages()
    print(f"[{SERVER_ID}] Message saved: {data.get('content', '')}")
    return jsonify({"status": "ok", "server": SERVER_ID})

@app.route('/messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "alive",
        "server": SERVER_ID,
        "time": time.time(),
        "message_count": len(messages)
    })

@app.route('/sync', methods=['POST'])
def sync():
    global messages
    incoming = request.json.get('messages', [])
    existing_ids = {m.get('id') for m in messages}
    added = 0
    for msg in incoming:
        if msg.get('id') not in existing_ids:
            messages.append(msg)
            added += 1
    save_messages()
    return jsonify({"status": "synced", "added": added, "total": len(messages)})

@app.route('/clear', methods=['POST'])
def clear():
    global messages
    messages = []
    save_messages()
    return jsonify({"status": "cleared"})

def save_messages():
    with open(f"{SERVER_ID}_data.json", "w") as f:
        json.dump(messages, f, indent=2)

def load_messages():
    global messages
    try:
        with open(f"{SERVER_ID}_data.json") as f:
            messages = json.load(f)
        print(f"[{SERVER_ID}] Loaded {len(messages)} messages from disk")
    except FileNotFoundError:
        messages = []

if __name__ == '__main__':
    load_messages()
    print(f"[{SERVER_ID}] Starting on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)