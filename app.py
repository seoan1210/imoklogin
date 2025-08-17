# app.py
import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import bcrypt
from dotenv import load_dotenv

# .env 파일에서 환경 변수 불러오기
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgresql://', 'postgresql+psycopg2://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Neon DB 접속을 위한 별도 설정 (Flask-SQLAlchemy가 psycopg2를 사용하도록 함)
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

# 데이터베이스 테이블 생성 (개발 시 한 번만 실행!)
@app.before_first_request
def create_tables():
    with app.app_context():
        db.create_all()

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

# 로그인 페이지
@app.route('/login')
def login():
    return render_template('login.html')

# 로그인 처리 API
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

# 로그아웃 API
@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('성공적으로 로그아웃되었습니다.', 'success')
    return jsonify({'message': '로그아웃 성공'}), 200

# 룰렛 페이지 (메인 페이지)
@app.route('/')
@login_required
def index():
    # 현재 로그인된 사용자 정보 가져오기
    current_user = User.query.filter_by(id=session['user_id']).first()
    return render_template('index.html', current_user=current_user)

# 사용자 목록 불러오기 API
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

# 룰렛 돌리기 API
@app.route('/api/spin_roulette', methods=['POST'])
@login_required
def api_spin_roulette():
    data = request.get_json()
    name = data.get('name')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN;")

        # 트랜잭션: 현재 사용자의 룰렛권 확인 및 차감
        cur.execute("SELECT tickets FROM users WHERE name = %s FOR UPDATE;", (name,))
        user_tickets = cur.fetchone()

        if not user_tickets or user_tickets[0] <= 0:
            cur.execute("ROLLBACK;")
            return jsonify({'message': '룰렛권이 부족합니다.'}), 400

        cur.execute("UPDATE users SET tickets = tickets - 1 WHERE name = %s;", (name,))

        # 룰렛 결과 결정 (30% 확률로 당첨)
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
    # 이 페이지는 보안상 로컬에서만 접근 가능하도록 설정하는 것이 좋음
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
    with app.app_context():
        # 데이터베이스와 테이블이 없으면 생성
        db.create_all()
    app.run(debug=True)

