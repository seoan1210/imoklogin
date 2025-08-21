# simple_roulette_app/app.py (전체 코드 - 오류 검사 및 최신화 완료)

from flask import Flask, request, jsonify, render_template_string, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError, OperationalError

# --- 1. Flask 앱 설정 ---
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///site_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-super-duper-secret-key-please-change-me-12345'

db = SQLAlchemy(app)

CORS(app)

# --- 2. Flask-Login 설정 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.login_message = "로그인 해주세요."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Person, int(user_id))

# --- 3. 데이터베이스 모델 정의 ---
class Person(db.Model, UserMixin):
    __tablename__ = 'person'  # 명시적으로 테이블 이름 설정
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    tickets = db.Column(db.Integer, default=10)
    is_admin = db.Column(db.Boolean, default=False)
    stars = db.Column(db.Integer, default=0)
    last_star_reset_date = db.Column(db.Date, default=date.today)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Person {self.name}>'
        
# --- 4. 초기 테이블 및 계정 생성 함수 ---
# 이 함수는 서버 시작 시 한 번만 실행하면 됩니다.
def create_database_and_admin_user():
    with app.app_context():
        print("Database 'person' 테이블을 생성합니다...")
        db.create_all()
        print("테이블 생성 완료.")
        
        try:
            existing_admin = Person.query.filter_by(name='admin').first()
            if not existing_admin:
                admin_user = Person(name='admin', is_admin=True)
                admin_user.set_password('seoan1024')
                db.session.add(admin_user)
                db.session.commit()
                print("초기 관리자 계정 'admin'이 생성되었습니다.")
            else:
                print("관리자 계정 'admin'이 이미 존재합니다. 생성을 건너뜁니다.")
        except IntegrityError:
            db.session.rollback()
            print("관리자 계정 'admin'이 이미 존재합니다.")
        except Exception as e:
            db.session.rollback()
            print(f"관리자 계정 생성 중 오류 발생: {e}")

# --- 5. 라우팅 (URL 경로) ---

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.json
    name = data.get('name')
    password = data.get('password')
    
    user = Person.query.filter_by(name=name).first()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify(message='로그인 성공!', redirect_url=url_for('index')), 200
    else:
        return jsonify(message='아이디 또는 비밀번호가 올바르지 않습니다.'), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout_api():
    logout_user()
    return jsonify(message='로그아웃 성공'), 200

@app.route('/')
@login_required
def index():
    return render_template('index.html', current_user=current_user)

# 룰렛 대상 목록 가져오는 API
@app.route('/api/get_people', methods=['GET'])
@login_required
def get_people():
    people = Person.query.filter(Person.is_admin.is_(False)).all()
    people_data = [
        {'name': p.name, 'tickets': p.tickets, 'stars': p.stars} for p in people
    ]
    return jsonify(people=people_data), 200

# 룰렛 돌리기 API
@app.route('/api/spin_roulette', methods=['POST'])
@login_required
def spin_roulette():
    if current_user.tickets <= 0:
        return jsonify(message='룰렛권이 부족합니다.'), 400
    
    current_user.tickets -= 1
    db.session.commit()
    
    # 룰렛 결과는 프론트엔드에서 결정되므로, 백엔드는 룰렛권만 차감
    return jsonify(message='룰렛권이 차감되었습니다.'), 200

# 매주 일요일 별점 초기화 (자동화)
def reset_stars():
    today = date.today()
    if today.weekday() == 6:  # 일요일 (0=월, 6=일)
        # 마지막 초기화 날짜를 확인
        last_reset_date = Person.query.first().last_star_reset_date if Person.query.first() else None
        
        if last_reset_date and last_reset_date.weekday() == 6 and (today - last_reset_date).days < 7:
            print("이번 주 별점 초기화는 이미 완료되었습니다.")
            return

        users = Person.query.all()
        for user in users:
            if user.stars >= 5:
                user.tickets += user.stars // 5
            user.stars = 0
            user.last_star_reset_date = today
            db.session.commit()
        print("모든 사용자의 별점과 룰렛권이 업데이트되었습니다.")

@app.route('/api/reset_stars', methods=['POST'])
@login_required
def manual_reset_stars():
    if not current_user.is_admin:
        return jsonify(message='관리자만 접근 가능합니다.'), 403
    reset_stars()
    return jsonify(message='별점 초기화 완료!')

# 룰렛 당첨 시 별점 추가
@app.route('/api/add_star', methods=['POST'])
@login_required
def add_star():
    current_user.stars += 1
    db.session.commit()
    return jsonify(message='별점이 추가되었습니다.'), 200

# 관리자 API (CRUD)
@app.route('/api/admin/users', methods=['GET', 'POST', 'DELETE'])
@login_required
def admin_users_api():
    if not current_user.is_admin:
        return jsonify(message='관리자만 접근 가능합니다.'), 403

    if request.method == 'GET':
        users = Person.query.all()
        users_data = [
            {
                'name': u.name, 
                'is_admin': u.is_admin, 
                'tickets': u.tickets, 
                'stars': u.stars
            } for u in users
        ]
        return jsonify(users=users_data)
        
    elif request.method == 'POST':
        data = request.json
        name = data.get('name')
        password = data.get('password')
        is_admin = data.get('is_admin', False)

        if Person.query.filter_by(name=name).first():
            return jsonify(message='이미 존재하는 사용자입니다.'), 400
        
        new_user = Person(name=name, is_admin=is_admin)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return jsonify(message=f'{name} 계정이 성공적으로 생성되었습니다.'), 200
    
    elif request.method == 'DELETE':
        data = request.json
        name = data.get('name')
        
        user_to_delete = Person.query.filter_by(name=name).first()
        if not user_to_delete:
            return jsonify(message='사용자를 찾을 수 없습니다.'), 404
            
        if user_to_delete.is_admin and user_to_delete.name == 'admin':
            return jsonify(message='기본 관리자 계정은 삭제할 수 없습니다.'), 400

        db.session.delete(user_to_delete)
        db.session.commit()
        return jsonify(message=f'{name} 계정이 삭제되었습니다.'), 200

@app.route('/api/admin/tickets', methods=['POST'])
@login_required
def admin_tickets_api():
    if not current_user.is_admin:
        return jsonify(message='관리자만 접근 가능합니다.'), 403
    
    data = request.json
    name = data.get('name')
    amount = data.get('amount')
    
    user = Person.query.filter_by(name=name).first()
    if not user:
        return jsonify(message='사용자를 찾을 수 없습니다.'), 404
        
    user.tickets = max(0, user.tickets + amount)
    db.session.commit()
    return jsonify(message=f'{name}의 룰렛권이 {amount}개 업데이트되었습니다.'), 200

@app.route('/api/admin/stars', methods=['POST'])
@login_required
def admin_stars_api():
    if not current_user.is_admin:
        return jsonify(message='관리자만 접근 가능합니다.'), 403
    
    data = request.json
    name = data.get('name')
    amount = data.get('amount')
    
    user = Person.query.filter_by(name=name).first()
    if not user:
        return jsonify(message='사용자를 찾을 수 없습니다.'), 404
        
    user.stars = max(0, user.stars + amount)
    db.session.commit()
    return jsonify(message=f'{name}의 별점이 {amount}개 업데이트되었습니다.'), 200

# 애플리케이션 시작
if __name__ == '__main__':
    # 이 부분은 로컬 테스트용입니다.
    # 렌더에서는 `gunicorn app:app` 명령어를 사용하므로 실행되지 않습니다.
    create_database_and_admin_user() 
    app.run(debug=True)
