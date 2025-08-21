from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os
import random

# Flask 애플리케이션 초기화
app = Flask(__name__)

# 데이터베이스 설정 (SQLite 사용)
# os.urandom(24)로 세션 암호화 키 설정
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///roulette.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 데이터베이스 모델 정의 ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    tickets = db.Column(db.Integer, default=10) # 기본 룰렛 티켓 10개

    def __repr__(self):
        return f'<User {self.name}>'

# --- 초기 데이터베이스 생성 ---
# 이 함수는 처음 한 번만 실행하면 됩니다.
def create_initial_data():
    with app.app_context():
        db.create_all()
        # 관리자 계정이 없으면 생성
        if not User.query.filter_by(is_admin=True).first():
            # 비밀번호는 실제로는 해시 처리해야 하지만, 예시이므로 간단히 작성
            admin_user = User(name='admin', password='password123', is_admin=True, tickets=999)
            db.session.add(admin_user)
            db.session.commit()
            print("관리자 계정 'admin'이 생성되었습니다.")
        
        # 일반 사용자 계정이 없으면 생성
        if not User.query.filter_by(name='user1').first():
            user1 = User(name='user1', password='password123', is_admin=False, tickets=5)
            db.session.add(user1)
            db.session.commit()
            print("일반 사용자 'user1'이 생성되었습니다.")

# --- 라우팅(URL 경로) 설정 ---

# 로그인 페이지
@app.route('/login', methods=['GET'])
def login():
    # 세션에 사용자 정보가 있으면 바로 index 페이지로 리다이렉트
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# 로그인 API
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('name')
    password = data.get('password')

    user = User.query.filter_by(name=username, password=password).first()

    if user:
        session['user_id'] = user.id
        session['username'] = user.name
        return jsonify(
            message='로그인 성공!', 
            redirect_url=url_for('index')
        ), 200
    else:
        return jsonify(
            message='로그인 실패. 아이디 또는 비밀번호를 확인해주세요.'
        ), 401

# 로그아웃 API
@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify(message='로그아웃 성공'), 200

# 룰렛 메인 페이지
@app.route('/')
def index():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.')
        return redirect(url_for('login'))
    
    # 세션에 있는 사용자 정보를 바탕으로 현재 사용자를 찾음
    current_user_id = session.get('user_id')
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        flash('사용자 정보를 찾을 수 없습니다. 다시 로그인해주세요.')
        session.pop('user_id', None)
        return redirect(url_for('login'))

    # Jinja2 템플릿에 `current_user` 변수 전달
    return render_template('index.html', current_user=current_user)

# 룰렛 대상 목록 가져오는 API
@app.route('/api/get_people', methods=['GET'])
def get_people():
    # 룰렛 대상은 관리자가 아닌 모든 사용자
    people = User.query.filter_by(is_admin=False).all()
    # 필요한 정보만 JSON 형식으로 변환
    people_data = [
        {'name': p.name, 'tickets': p.tickets, 'is_admin': p.is_admin} for p in people
    ]
    return jsonify(people=people_data), 200

# 룰렛 돌리는 API
@app.route('/api/spin_roulette', methods=['POST'])
def spin_roulette():
    if 'user_id' not in session:
        return jsonify(message='로그인이 필요합니다.'), 401
    
    data = request.json
    username = data.get('name')

    user = User.query.filter_by(name=username).first()
    if not user:
        return jsonify(message='사용자를 찾을 수 없습니다.'), 404

    if user.tickets <= 0:
        return jsonify(message='룰렛권이 부족합니다.'), 400

    # 룰렛권 1개 차감
    user.tickets -= 1
    db.session.commit()

    return jsonify(message='룰렛권이 차감되었습니다.'), 200

if __name__ == '__main__':
    create_initial_data() # 데이터베이스 초기화 및 초기 사용자 생성
    app.run(debug=True)
