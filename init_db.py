# init_db.py
from app import app, db, Person
from werkzeug.security import generate_password_hash
import os
from datetime import date

with app.app_context():
    print("기존의 모든 테이블을 삭제합니다...")
    db.drop_all() # <-- 모든 테이블 삭제!

    print("새로운 테이블을 생성합니다...")
    db.create_all() # <-- 새로운 구조로 테이블 생성!

    if not Person.query.filter_by(name='admin').first():
        admin_password = os.getenv("ADMIN_PASSWORD", "super-secret-password-to-change")

        admin_user = Person(name='admin', is_admin=True)
        admin_user.set_password("seoan1024")
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created!")
    else:
        print("Admin user already exists.")
