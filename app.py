from flask import Flask, request, jsonify
import sqlite3
import datetime

app = Flask(__name__)

DB_FILE = 'crm.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/setup', methods=['POST'])
def setup():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        phone TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY,
        contact_id INTEGER,
        type TEXT,
        timestamp TIMESTAMP,
        content TEXT,
        source TEXT,
        FOREIGN KEY (contact_id) REFERENCES contacts (id)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ai_notes (
        id INTEGER PRIMARY KEY,
        interaction_id INTEGER,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (interaction_id) REFERENCES interactions (id)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS followups (
        id INTEGER PRIMARY KEY,
        contact_id INTEGER,
        type TEXT,
        scheduled_time TIMESTAMP,
        status TEXT DEFAULT 'pending',
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (contact_id) REFERENCES contacts (id)
    )''')
    conn.commit()
    conn.close()
    return jsonify({'message': 'Database setup complete'})

@app.route('/add_contact', methods=['POST'])
def add_contact():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    notes = data.get('notes')
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO contacts (name, email, phone, notes) VALUES (?, ?, ?, ?)', (name, email, phone, notes))
    contact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': contact_id, 'message': 'Contact added'})

@app.route('/add_interaction', methods=['POST'])
def add_interaction():
    data = request.json
    contact_id = data.get('contact_id')
    type_ = data.get('type')
    timestamp = data.get('timestamp') or datetime.datetime.now().isoformat()
    content = data.get('content')
    source = data.get('source')
    if not contact_id or not type_ or not content:
        return jsonify({'error': 'contact_id, type, content required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO interactions (contact_id, type, timestamp, content, source) VALUES (?, ?, ?, ?, ?)', (contact_id, type_, timestamp, content, source))
    interaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': interaction_id, 'message': 'Interaction added'})

@app.route('/add_ai_note', methods=['POST'])
def add_ai_note():
    data = request.json
    interaction_id = data.get('interaction_id')
    note = data.get('note')
    if not interaction_id or not note:
        return jsonify({'error': 'interaction_id and note required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ai_notes (interaction_id, note) VALUES (?, ?)', (interaction_id, note))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': note_id, 'message': 'AI note added'})

@app.route('/add_followup', methods=['POST'])
def add_followup():
    data = request.json
    contact_id = data.get('contact_id')
    type_ = data.get('type')
    scheduled_time = data.get('scheduled_time')
    message = data.get('message')
    if not contact_id or not type_ or not scheduled_time or not message:
        return jsonify({'error': 'contact_id, type, scheduled_time, message required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO followups (contact_id, type, scheduled_time, message) VALUES (?, ?, ?, ?)', (contact_id, type_, scheduled_time, message))
    followup_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': followup_id, 'message': 'Followup added'})

@app.route('/check_followups', methods=['GET'])
def check_followups():
    now = datetime.datetime.now().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM followups WHERE scheduled_time <= ? AND status = "pending"', (now,))
    followups = cursor.fetchall()
    result = []
    for f in followups:
        result.append(dict(f))
        cursor.execute('UPDATE followups SET status = "sent" WHERE id = ?', (f['id'],))
    conn.commit()
    conn.close()
    return jsonify(result)

@app.route('/generate_ai_note', methods=['POST'])
def generate_ai_note():
    data = request.json
    interaction_id = data.get('interaction_id')
    if not interaction_id:
        return jsonify({'error': 'interaction_id required'}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT content FROM interactions WHERE id = ?', (interaction_id,))
    interaction = cursor.fetchone()
    if not interaction:
        conn.close()
        return jsonify({'error': 'Interaction not found'}), 404
    note = f"Interaction summary: {interaction['content'][:100]}..."
    cursor.execute('INSERT INTO ai_notes (interaction_id, note) VALUES (?, ?)', (interaction_id, note))
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': note_id, 'note': note})

if __name__ == '__main__':
    app.run(debug=True)