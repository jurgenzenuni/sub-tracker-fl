from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase_client import supabase
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============ PAGES ============

@app.route('/')
def home():
    user = session.get('user')
    user_id = session.get('user_id')
    subscriptions = []
    
    if user_id:
        response = supabase.table('subscriptions').select('*').eq('user_id', user_id).eq('is_active', True).execute()
        subscriptions = response.data
    
    return render_template('dashboard.html', user=user, subscriptions=subscriptions)

# ============ AUTH API ============

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    try:
        response = supabase.auth.sign_up({
            'email': data['email'],
            'password': data['password']
        })
        return jsonify({'success': True, 'message': 'Check your email to confirm!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    try:
        response = supabase.auth.sign_in_with_password({
            'email': data['email'],
            'password': data['password']
        })
        session['user'] = response.user.email
        session['user_id'] = response.user.id
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user', None)
    session.pop('user_id', None)
    return jsonify({'success': True})

# ============ SUBSCRIPTIONS API ============

@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    response = supabase.table('subscriptions').select('*').eq('user_id', user_id).order('next_billing_date').execute()
    return jsonify(response.data)

@app.route('/api/subscriptions', methods=['POST'])
def add_subscription():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    data['user_id'] = user_id
    
    response = supabase.table('subscriptions').insert(data).execute()
    return jsonify(response.data[0])

@app.route('/api/subscriptions/<sub_id>', methods=['PUT'])
def update_subscription(sub_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    response = supabase.table('subscriptions').update(data).eq('id', sub_id).eq('user_id', user_id).execute()
    return jsonify(response.data[0] if response.data else {})

@app.route('/api/subscriptions/<sub_id>', methods=['DELETE'])
def delete_subscription(sub_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    supabase.table('subscriptions').delete().eq('id', sub_id).eq('user_id', user_id).execute()
    return jsonify({'success': True})

# ============ STATS API ============

@app.route('/api/stats', methods=['GET'])
def get_stats():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    response = supabase.table('subscriptions').select('*').eq('user_id', user_id).eq('is_active', True).execute()
    subs = response.data
    
    monthly_total = 0
    for sub in subs:
        price = float(sub['price'])
        cycle = sub['billing_cycle']
        if cycle == 'weekly':
            monthly_total += price * 4
        elif cycle == 'monthly':
            monthly_total += price
        elif cycle == 'yearly':
            monthly_total += price / 12
    
    return jsonify({
        'total_subscriptions': len(subs),
        'monthly_total': round(monthly_total, 2),
        'yearly_total': round(monthly_total * 12, 2)
    })

if __name__ == '__main__':
    app.run(debug=True)
