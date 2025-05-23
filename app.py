from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key_here'

VALID_USERNAME = "admin"
VALID_PASSWORD = "password123"

# Login required decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return render_template('progressnote.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('index'))
    else:
        flash('Please check your ID and Password again', 'error')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)