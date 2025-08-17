# app.py
import os
import bcrypt
import psycopg2
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# .env 파일에서 환경 변수 불러오기
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# PostgreSQL 드라이버를 명시적으로 지정하도록 수정
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgresql://', 'postgresql+psycopg2://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Neon DB 접속을 위한 별도 설정 (Flask-SQLalchemy 외에 psycopg2 직접 사용)
def get_db_connection():
    conn_string = os.environ.get('DATABASE_URL')
    if not conn_string:
        raise ValueError("DATABASE_URL is not set!")
    conn = psycopg2.connect(conn_string)
    return conn

# 데이터베이스 모델 (테이블) 정의
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    tickets = db.Column(db.Integer, default=0)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<User {self.name}>'

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

# Vercel 환경에서는 @app.before_first_request가 적합하지 않으므로 삭제!
# 대신, Neon DB 대시보드에서 테이블을 직접 생성해야 함.

# 로그인 확인 데코레이터
def login_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# --- 라우팅 (URL 경로) 설정 ---

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')

    user = User.query.filter_by(name=name).first()

    if user and user.check_password(password):
        session['user_id'] = user.id
        session['user_name'] = user.name
        return jsonify({'message': '로그인 성공!', 'redirect_url': url_for('index')}), 200
    else:
        return jsonify({'message': '아이디 또는 비밀번호가 잘못되었습니다.'}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('성공적으로 로그아웃되었습니다.', 'success')
    return jsonify({'message': '로그아웃 성공'}), 200

@app.route('/')
@login_required
def index():
    current_user = User.query.filter_by(id=session['user_id']).first()
    return render_template('index.html', current_user=current_user)

@app.route('/api/get_people', methods=['GET'])
@login_required
def api_get_people():
    try:
        users = User.query.filter_by(is_admin=False).order_by(User.name).all()
        user_list = [{'name': user.name, 'tickets': user.tickets, 'is_admin': user.is_admin} for user in users]
        return jsonify({'people': user_list}), 200
    except Exception as e:
        print(f"Error fetching people: {e}")
        return jsonify({'message': '사용자 목록을 불러오는 데 실패했습니다.'}), 500

@app.route('/api/spin_roulette', methods=['POST'])
@login_required
def api_spin_roulette():
    data = request.get_json()
    name = data.get('name')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN;")

        cur.execute("SELECT tickets FROM users WHERE name = %s FOR UPDATE;", (name,))
        user_tickets = cur.fetchone()

        if not user_tickets or user_tickets[0] <= 0:
            cur.execute("ROLLBACK;")
            return jsonify({'message': '룰렛권이 부족합니다.'}), 400

        cur.execute("UPDATE users SET tickets = tickets - 1 WHERE name = %s;", (name,))

        is_win = os.urandom(1)[0] < 256 * 0.3
        
        cur.execute("COMMIT;")
        
        return jsonify({'message': '룰렛 성공!', 'isWin': is_win}), 200

    except Exception as e:
        cur.execute("ROLLBACK;")
        print(f"Error spinning roulette: {e}")
        return jsonify({'message': '룰렛을 돌리는 중 오류가 발생했습니다.'}), 500
    finally:
        cur.close()
        conn.close()

# 관리자 계정 등록 (개발용)
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')

    if not name or not password:
        return jsonify({'message': '모든 필드를 입력하세요.'}), 400

    existing_user = User.query.filter_by(name=name).first()
    if existing_user:
        return jsonify({'message': '이미 존재하는 사용자 이름입니다.'}), 409

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(name=name, password_hash=hashed_password, is_admin=True)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': '관리자 계정이 생성되었습니다.'}), 201

# 앱 실행
if __name__ == '__main__':
    # Vercel은 이 부분을 실행하지 않으므로, 이 코드는 로컬 테스트용
    with app.app_context():
        # 데이터베이스와 테이블이 없으면 생성
        db.create_all()
    app.run(debug=True)
