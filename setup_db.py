# setup_db.py

import os
from app import app, db, Person

def create_database_and_admin_user():
    with app.app_context():
        try:
            print("데이터베이스 테이블을 생성합니다...")
            db.create_all()
            print("테이블 생성 완료.")
        except Exception as e:
            print(f"테이블 생성 중 오류 발생: {e}")
            return
            
        try:
            existing_admin = Person.query.filter_by(name='admin').first()
            if not existing_admin:
                print("초기 관리자 계정 'admin'을 생성합니다...")
                admin_user = Person(name='admin', is_admin=True)
                admin_user.set_password(os.environ.get('ADMIN_PASSWORD') or 'seoan1024')
                db.session.add(admin_user)
                db.session.commit()
                print("관리자 계정 'admin' 생성 완료.")
            else:
                print("관리자 계정 'admin'이 이미 존재합니다. 생성을 건너뜁니다.")
        except Exception as e:
            db.session.rollback()
            print(f"관리자 계정 생성 중 오류 발생: {e}")

if __name__ == '__main__':
    create_database_and_admin_user()
