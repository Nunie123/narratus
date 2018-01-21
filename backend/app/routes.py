from app import app

@app.route('/')
@app.route('/api/users', methods=['GET', 'POST'])
def get_all_users():
    return 'stub'
