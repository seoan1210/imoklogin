import os
import psycopg2
import bcrypt
from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
# 세션을 사용하려면 SECRET_KEY가 꼭 필요해!
# Vercel 환경 변수에 설정해두면 더 안전하게 쓸 수 있어!
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')

# Neon DB에 연결하는 함수
# 환경 변수 DATABASE_URL을 사용해
def get_db_connection():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

# 데이터베이스 테이블을 초기화하는 라우트!
# 이 라우트에 한 번만 접속하면 'users' 테이블이 만들어질 거야.
@app.route('/init_db')
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return "Database initialized successfully! You can now use the website."

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[0].encode('utf-8')):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid username or password", 401
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password.decode('utf-8')))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            return "Username already exists", 409
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Vercel은 이 부분을 직접 실행하지 않아.
# gunicorn이 대신 실행해 줄 거야!
# 하지만 로컬에서 테스트할 때 유용해.
if __name__ == '__main__':
    app.run(debug=True)
