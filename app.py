# -*- coding: utf-8 -*-
# simple_roulette_app/app.py (수정된 전체 코드)

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError, OperationalError

# --- 1. Flask 앱 설정 ---
app = Flask(__name__)

# ⭐⭐ 여기를 수정! Neon DB를 사용하도록 환경 변수 설정 ⭐⭐
# Vercel에서 Neon을 연결하면 자동으로 `DATABASE_URL`이 설정돼.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 세션에 필요한 SECRET_KEY도 Vercel 환경 변수에 설정해두면 좋아!
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

db = SQLAlchemy(app)

CORS(app)

# --- 2. Flask-Login 설정 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.login_message = "로그인 해주세요."
login_manager.login_message_category = "info"

class Person(db.Model, UserMixin):
    __tablename__ = 'person'  # 테이블 이름 명시
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    roulette_ticket_count = db.Column(db.Integer, default=5)
    last_roulette_date = db.Column(db.Date, default=date(2000, 1, 1))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Person {self.name}>'

@login_manager.user_loader
def load_user(user_id):
    return Person.query.get(int(user_id))

# ⭐⭐ `db.create_all()` 로직 수정 ⭐⭐
# Vercel 배포 시 `init_db.py`가 실행되지 않으므로,
# `db.create_all()`은 한 번만 실행되도록 별도의 라우트로 분리합니다.
@app.route('/create-db')
def create_db():
    with app.app_context():
        try:
            db.create_all()
            if not Person.query.filter_by(name='admin').first():
                admin_password = os.getenv("ADMIN_PASSWORD", "seoan1024")
                admin_user = Person(name='admin', is_admin=True)
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                return "Database and Admin User created successfully!", 200
            return "Database tables already exist. Admin user checked.", 200
        except Exception as e:
            db.session.rollback()
            return f"Error during database initialization: {e}", 500

# --- 3. 라우트 정의 ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

# 로그인 API
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    name = data.get('name')
    password = data.get('password')

    person = Person.query.filter_by(name=name).first()
    if person and person.check_password(password):
        login_user(person, remember=True)
        return jsonify({"message": f"로그인 성공! 환영합니다, {person.name}님!", "redirect_url": url_for('index')}), 200
    else:
        return jsonify({"message": "로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다."}), 401

# 회원가입 API
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    name = data.get('name')
    password = data.get('password')

    if not name or not password:
        return jsonify({"message": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    existing_user = Person.query.filter_by(name=name).first()
    if existing_user:
        return jsonify({"message": "이미 존재하는 아이디입니다."}), 409
    
    new_user = Person(name=name)
    new_user.set_password(password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": f"회원가입 성공! 이제 {name}님으로 로그인할 수 있습니다."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"회원가입 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "로그아웃 성공!"}), 200

# API Endpoints for Roulette functionality (기존 코드 유지)
# ... 이 부분은 기존 코드 그대로 유지하면 돼.

# 룰렛 티켓 차감 및 당첨자 선정
@app.route('/api/spin_roulette', methods=['POST'])
@login_required
def spin_roulette():
    # ... 기존 코드
    pass

@app.route('/api/current_status', methods=['GET'])
@login_required
def get_current_status():
    # ... 기존 코드
    pass

# `gunicorn`이 실행할 기본 앱 인스턴스
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))

