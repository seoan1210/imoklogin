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

class Person(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    tickets = db.Column(db.Integer, default=0, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    stars = db.Column(db.Integer, default=0, nullable=False)
    last_star_reset_date = db.Column(db.Date, default=date.today)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<Person {self.name} Admin: {self.is_admin} Tickets: {self.tickets} Stars: {self.stars}>'

@login_manager.user_loader
def load_user(user_id):
    return Person.query.get(int(user_id))

def check_and_reset_stars(person):
    today = date.today()
    
    if person.stars >= 2:
        person.tickets += 1
        person.stars = 0
        db.session.commit()
        print(f"[{person.name}]의 별점 2개가 모여 룰렛권 1개가 지급되었습니다! (남은 룰렛권: {person.tickets})")


# --- 4. 웹 페이지 라우트 (HTML 파일 렌더링) ---

@app.route('/login')
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('roulette_page'))
    return render_template('login.html')

@app.route('/register')
@login_required
def register_page():
    if not current_user.is_admin:
        flash("관리자만 사용자 등록 페이지에 접근할 수 있습니다.", "error")
        return redirect(url_for('login_page'))
    
    html_content = """
    """
    return render_template_string(html_content)

@app.route('/admin')
@login_required 
def admin_page():
    if not current_user.is_admin:
        flash("관리자만 접근할 수 있는 페이지입니다.", "error")
        return redirect(url_for('roulette_page')) 

    # ✨ 관리자 페이지에 별점/룰렛권 삭제 버튼을 추가하기 위해 JS 코드가 수정되었습니다.
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>관리자: 사용자 & 룰렛권 관리</title>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
        <style>
            /* 전체적인 스타일 */
            body { 
                font-family: 'Noto Sans KR', sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                min-height: 100vh; 
                margin: 0; 
                background: linear-gradient(135deg, #f0f4f8, #e6e9ee); 
                color: #333;
            }
            .container { 
                background-color: #ffffff; 
                padding: 40px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); 
                text-align: center; 
                max-width: 900px; 
                width: 90%; 
                position: relative;
            }
            h1 { 
                color: #4a69bd; 
                margin-bottom: 25px; 
                font-size: 2.2em;
                font-weight: 700;
            }
            p { 
                color: #555; 
                margin-bottom: 20px; 
            }
            .form-section { 
                margin-bottom: 35px; 
                border-bottom: 1px solid #e0e0e0; 
                padding-bottom: 25px; 
            }
            /* 입력 필드 */
            input[type="text"], input[type="password"] { 
                padding: 12px; 
                border: 1px solid #ced4da; 
                border-radius: 8px; 
                width: calc(30% - 25px); 
                margin-right: 15px; 
                font-size: 1em;
                box-sizing: border-box; 
            }
            input[type="checkbox"] {
                margin-left: 10px;
                margin-right: 5px;
            }

            /* 버튼 스타일 */
            button { 
                background-color: #007bff; 
                color: white; 
                padding: 12px 20px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 1em; 
                font-weight: 700;
                transition: background-color 0.3s ease, transform 0.2s ease; 
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); 
            }
            button:hover { 
                background-color: #0056b3; 
                transform: translateY(-2px); 
            }
            .add-button { background-color: #28a745; }
            .add-button:hover { background-color: #218838; }
            .delete-button { background-color: #dc3545; margin-left: 10px; }
            .delete-button:hover { background-color: #c82333; }
            .give-ticket-button { background-color: #ffc107; color: #333; margin-left: 10px; }
            .give-ticket-button:hover { background-color: #e0a800; }
            .remove-ticket-button { background-color: #b33939; color: white; margin-left: 10px; }
            .remove-ticket-button:hover { background-color: #8c2a2a; }
            .give-star-button { background-color: #ff9800; color: white; margin-left: 10px; }
            .give-star-button:hover { background-color: #e68a00; }
            .remove-star-button { background-color: #9c27b0; color: white; margin-left: 10px; }
            .remove-star-button:hover { background-color: #7b1fa2; }
            .reset-password-button { background-color: #6f42c1; margin-left: 10px; } 
            .reset-password-button:hover { background-color: #563691; }

            .logout-button { 
                position: absolute; 
                top: 20px; 
                right: 30px; 
                background-color: #6c757d; 
                padding: 8px 15px; 
                font-size: 0.9em; 
                box-shadow: none;
            }
            .logout-button:hover { background-color: #5a6268; transform: none; }

            /* 테이블 스타일 */
            table { 
                width: 100%; 
                border-collapse: separate; 
                border-spacing: 0 10px; 
                margin-top: 30px; 
                background-color: #f8f9fa; 
                border-radius: 10px;
                overflow: hidden; 
            }
            th, td { 
                border: none; 
                padding: 15px; 
                text-align: left; 
            }
            th { 
                background-color: #4a69bd; 
                color: white; 
                font-weight: 700;
                text-transform: uppercase; 
                letter-spacing: 0.5px;
            }
            td {
                background-color: #ffffff; 
                border-bottom: 1px solid #eee; 
            }
            tbody tr:last-child td {
                border-bottom: none; 
            }
            tbody tr {
                box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
                transition: transform 0.2s ease;
            }
            tbody tr:hover {
                transform: translateY(-3px); 
            }

            /* 메시지 박스 */
            .message { 
                margin-top: 25px; 
                padding: 12px; 
                border-radius: 8px; 
                font-weight: bold; 
                font-size: 0.95em;
                animation: fadeIn 0.5s ease-out; 
            }
            .message.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .message.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .hidden { display: none; }

            /* 플래시 메시지 (Flask에서 옴) */
            .flash {
                background-color: #ffe0b2; 
                color: #e65100; 
                border: 1px solid #ffcc80;
                padding: 12px;
                margin-bottom: 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 0.95em;
                text-align: center;
            }

            /* 애니메이션 */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* 반응형 디자인 (간단하게) */
            @media (max-width: 768px) {
                input[type="text"], input[type="password"] {
                    width: calc(100% - 22px); 
                    margin-right: 0;
                    margin-bottom: 10px;
                }
                .form-section button {
                    width: 100%;
                    margin-top: 10px;
                }
                table, thead, tbody, th, td, tr {
                    display: block; 
                }
                th {
                    display: none; 
                }
                td {
                    border: none;
                    position: relative;
                    padding-left: 50%; 
                    text-align: right;
                }
                td:before { 
                    content: attr(data-label);
                    position: absolute;
                    left: 0;
                    width: 45%;
                    padding-left: 15px;
                    font-weight: bold;
                    text-align: left;
                }
                /* 모바일에서 액션 버튼들 정렬 */
                td:nth-of-type(6) { 
                    text-align: center;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: center;
                }
                td:nth-of-type(6) button {
                    width: calc(50% - 10px);
                    margin: 5px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <button class="logout-button" onclick="logout()">로그아웃</button>
            <h1>관리자: 사용자 & 룰렛권 관리</h1>
            <p>환영합니다, {{ current_user.name }}님! (관리자)</p>

            <div class="form-section">
                <h2>새로운 사용자(이름) 등록</h2>
                <input type="text" id="addUserNameInput" class="add-user-input" placeholder="사용자 이름">
                <input type="password" id="addUserPasswordInput" class="add-user-input" placeholder="비밀번호">
                <label><input type="checkbox" id="addIsAdmin"> 관리자 계정</label>
                <button id="addUserButton" class="add-button">사용자 추가</button>
                <p id="addUserMessage" class="message hidden"></p>
            </div>

            <div class="list-section">
                <h2>등록된 사용자 목록</h2>
                <table id="personTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>이름</th>
                            <th>관리자</th>
                            <th>룰렛권</th>
                            <th>별점</th>
                            <th>액션</th>
                        </tr>
                    </thead>
                    <tbody>
                        </tbody>
                </table>
                <p id="listMessage" class="message hidden"></p>
            </div>
        </div>

        <script>
            // JavaScript 로직
            document.addEventListener('DOMContentLoaded', () => {
                const addUserNameInput = document.getElementById('addUserNameInput');
                const addUserPasswordInput = document.getElementById('addUserPasswordInput');
                const addIsAdminCheckbox = document.getElementById('addIsAdmin');
                const addUserButton = document.getElementById('addUserButton');
                const personTableBody = document.querySelector('#personTable tbody');
                const addUserMessageElement = document.getElementById('addUserMessage');
                const listMessageElement = document.getElementById('listMessage');

                const API_BASE_URL = window.location.origin; 
                const API_ADD_PERSON = API_BASE_URL + '/api/register';
                const API_DELETE_PERSON = API_BASE_URL + '/api/delete_person/';
                const API_GIVE_TICKET = API_BASE_URL + '/api/give_ticket/';
                const API_REMOVE_TICKET = API_BASE_URL + '/api/remove_ticket/';
                const API_GIVE_STAR = API_BASE_URL + '/api/give_star/';
                const API_REMOVE_STAR = API_BASE_URL + '/api/remove_star/';
                const API_GET_PEOPLE = API_BASE_URL + '/api/get_people'; 
                const API_RESET_PASSWORD = API_BASE_URL + '/api/reset_password/'; 
                const API_LOGOUT = API_BASE_URL + '/api/logout';


                function showMessage(element, text, type) {
                    element.textContent = text;
                    element.className = `message ${type}`;
                    element.classList.remove('hidden');
                    setTimeout(() => {
                        element.classList.add('hidden');
                    }, 3000);
                }

                async function fetchPeople() {
                    try {
                        const response = await fetch(API_GET_PEOPLE); 
                        const data = await response.json();
                        
                        personTableBody.innerHTML = '';
                        if (response.ok && data.people && data.people.length > 0) {
                            data.people.forEach(person => {
                                const row = personTableBody.insertRow();
                                row.insertCell(0).setAttribute('data-label', 'ID:'); row.cells[0].textContent = person.id;
                                row.insertCell(1).setAttribute('data-label', '이름:'); row.cells[1].textContent = person.name;
                                row.insertCell(2).setAttribute('data-label', '관리자:'); row.cells[2].textContent = person.is_admin ? '✅' : '❌';
                                row.insertCell(3).setAttribute('data-label', '룰렛권:'); row.cells[3].textContent = person.tickets;
                                row.insertCell(4).setAttribute('data-label', '별점:'); row.cells[4].textContent = person.stars;
                                
                                const actionCell = row.insertCell(5);
                                actionCell.setAttribute('data-label', '액션:');

                                const giveStarBtn = document.createElement('button');
                                giveStarBtn.textContent = '별점 주기';
                                giveStarBtn.className = 'give-star-button';
                                giveStarBtn.onclick = () => giveStar(person.id, person.name);
                                actionCell.appendChild(giveStarBtn);

                                const removeStarBtn = document.createElement('button');
                                removeStarBtn.textContent = '별점 삭제';
                                removeStarBtn.className = 'remove-star-button';
                                removeStarBtn.onclick = () => removeStar(person.id, person.name);
                                actionCell.appendChild(removeStarBtn);

                                const giveTicketBtn = document.createElement('button');
                                giveTicketBtn.textContent = '룰렛권 주기';
                                giveTicketBtn.className = 'give-ticket-button';
                                giveTicketBtn.onclick = () => giveTicket(person.id, person.name);
                                actionCell.appendChild(giveTicketBtn);

                                const removeTicketBtn = document.createElement('button');
                                removeTicketBtn.textContent = '룰렛권 삭제';
                                removeTicketBtn.className = 'remove-ticket-button';
                                removeTicketBtn.onclick = () => removeTicket(person.id, person.name);
                                actionCell.appendChild(removeTicketBtn);


                                const resetPasswordBtn = document.createElement('button');
                                resetPasswordBtn.textContent = '비밀번호 재설정';
                                resetPasswordBtn.className = 'reset-password-button'; 
                                resetPasswordBtn.onclick = () => resetPassword(person.id, person.name);
                                actionCell.appendChild(resetPasswordBtn);

                                const deleteBtn = document.createElement('button');
                                deleteBtn.textContent = '삭제';
                                deleteBtn.className = 'delete-button';
                                deleteBtn.onclick = () => deletePerson(person.id, person.name);
                                actionCell.appendChild(deleteBtn);
                            });
                        } else {
                            const row = personTableBody.insertRow();
                            const cell = row.insertCell(0);
                            cell.colSpan = 6;
                            cell.textContent = '등록된 사용자가 없습니다.';
                        }
                    } catch (error) {
                        showMessage(listMessageElement, '🚫 사용자 목록 불러오기 실패: 네트워크 오류', 'error');
                        console.error('Error fetching people:', error);
                    }
                }

                // ✨ 새로운 별점 삭제 함수
                async function removeStar(personId, personName) {
                    if (!confirm(`'${personName}' 님의 별점 1개를 삭제하시겠습니까?`)) {
                        return;
                    }
                    try {
                        const response = await fetch(API_REMOVE_STAR + personId, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({})
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(listMessageElement, `✅ '${personName}' 님의 별점 1개 삭제 성공! (총 ${data.stars}개)`, 'success');
                            fetchPeople();
                        } else {
                            showMessage(listMessageElement, `❌ 별점 삭제 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(listMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error removing star:', error);
                    }
                }

                // ✨ 새로운 룰렛권 삭제 함수
                async function removeTicket(personId, personName) {
                    if (!confirm(`'${personName}' 님의 룰렛권 1개를 삭제하시겠습니까?`)) {
                        return;
                    }
                    try {
                        const response = await fetch(API_REMOVE_TICKET + personId, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({})
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(listMessageElement, `✅ '${personName}' 님의 룰렛권 1개 삭제 성공! (총 ${data.tickets}개)`, 'success');
                            fetchPeople();
                        } else {
                            showMessage(listMessageElement, `❌ 룰렛권 삭제 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(listMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error removing ticket:', error);
                    }
                }

                async function giveStar(personId, personName) {
                    if (!confirm(`'${personName}' 님에게 별점 1개를 부여하시겠습니까?`)) {
                        return;
                    }
                    try {
                        const response = await fetch(API_GIVE_STAR + personId, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({})
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(listMessageElement, `✅ '${personName}' 님에게 별점 1개 부여 성공! (총 ${data.stars}개)`, 'success');
                            fetchPeople();
                        } else {
                            showMessage(listMessageElement, `❌ 별점 부여 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(listMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error giving star:', error);
                    }
                }

                async function giveTicket(personId, personName) {
                    if (!confirm(`'${personName}' 님에게 룰렛권 1개를 부여하시겠습니까?`)) {
                        return;
                    }
                    try {
                        const response = await fetch(API_GIVE_TICKET + personId, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({})
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(listMessageElement, `✅ '${personName}' 님에게 룰렛권 1개 부여 성공! (총 ${data.tickets}개)`, 'success');
                            fetchPeople();
                        } else {
                            showMessage(listMessageElement, `❌ 룰렛권 부여 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(listMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error giving ticket:', error);
                    }
                }

                // ... (이전의 addUserButton.addEventListener, resetPassword, deletePerson, logout 함수들은 그대로 둡니다) ...

                addUserButton.addEventListener('click', async () => {
                    const name = addUserNameInput.value.trim();
                    const password = addUserPasswordInput.value.trim();
                    const isAdmin = addIsAdminCheckbox.checked;

                    if (!name || !password) {
                        showMessage(addUserMessageElement, '⚠️ 이름과 비밀번호를 모두 입력해주세요!', 'error');
                        return;
                    }
                    if (password.length < 6) { // 비밀번호 최소 길이 설정
                        showMessage(addUserMessageElement, '⚠️ 비밀번호는 최소 6자 이상이어야 합니다.', 'error');
                        return;
                    }


                    try {
                        const response = await fetch(API_ADD_PERSON, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ name: name, password: password, is_admin: isAdmin })
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(addUserMessageElement, `✅ '${name}' 사용자가 등록되었습니다!`, 'success');
                            addUserNameInput.value = '';
                            addUserPasswordInput.value = '';
                            addIsAdminCheckbox.checked = false;
                            fetchPeople();
                        } else {
                            showMessage(addUserMessageElement, `❌ 사용자 등록 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(addUserMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error adding user:', error);
                    }
                });


                async function resetPassword(personId, personName) {
                    const newPassword = prompt(`'${personName}' 님의 새 비밀번호를 입력하세요:`);
                    if (!newPassword) {
                        showMessage(listMessageElement, '⚠️ 비밀번호 재설정이 취소되었습니다.', 'info');
                        return;
                    }
                    if (newPassword.length < 6) { 
                        showMessage(listMessageElement, '⚠️ 비밀번호는 최소 6자 이상이어야 합니다.', 'error');
                        return;
                    }

                    if (!confirm(`'${personName}' 님의 비밀번호를 '${newPassword}'로 재설정하시겠습니까?`)) {
                        return;
                    }

                    try {
                        const response = await fetch(API_RESET_PASSWORD + personId, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ new_password: newPassword })
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(listMessageElement, `✅ ${data.message}`, 'success');
                        } else {
                            showMessage(listMessageElement, `❌ 비밀번호 재설정 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(listMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error resetting password:', error);
                    }
                }

                async function deletePerson(personId, personName) {
                    if (!confirm(`'${personName}' 님을 정말 삭제하시겠습니까?`)) {
                        return;
                    }
                    try {
                        const response = await fetch(API_DELETE_PERSON + personId, {
                            method: 'DELETE'
                        });
                        const data = await response.json();

                        if (response.ok) {
                            showMessage(listMessageElement, `✅ '${personName}' 님이 삭제되었습니다!`, 'success');
                            fetchPeople();
                        } else {
                            showMessage(listMessageElement, `❌ 삭제 실패: ${data.message || '알 수 없는 에러'}`, 'error');
                        }
                    } catch (error) {
                        showMessage(listMessageElement, `🚫 네트워크 에러: ${error.message}`, 'error');
                        console.error('Error deleting person:', error);
                    }
                }

                window.logout = async () => {
                    try {
                        const response = await fetch(API_LOGOUT, { method: 'POST' });
                        if (response.ok) {
                            window.location.href = '/login'; 
                        } else {
                            alert('로그아웃 실패!');
                        }
                    } catch (error) {
                        console.error('Logout error:', error);
                        alert('로그아웃 중 네트워크 오류 발생!');
                    }
                };

                fetchPeople();
                setInterval(fetchPeople, 5000); 
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content, current_user=current_user)

@app.route('/')
@login_required 
def roulette_page():
    check_and_reset_stars(current_user)
    return render_template('index.html', current_user=current_user)

# --- 5. API 엔드포인트 ---

@app.route('/api/register', methods=['POST'])
def register_api():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"message": "관리자만 사용자를 등록할 수 있습니다."}), 403

    data = request.get_json()
    name = data.get('name')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not name or not password:
        return jsonify({"message": "아이디와 비밀번호를 모두 입력해주세요."}), 400
    if len(password) < 6:
        return jsonify({"message": "비밀번호는 최소 6자 이상이어야 합니다."}), 400
    
    existing_person = Person.query.filter_by(name=name).first()
    if existing_person:
        return jsonify({"message": "이미 존재하는 아이디(이름)입니다."}), 409

    try:
        new_person = Person(name=name, is_admin=is_admin)
        new_person.set_password(password) 
        db.session.add(new_person)
        db.session.commit()
        print(f"Registered new user: {name} (Admin: {is_admin})")
        return jsonify({"message": "사용자가 성공적으로 등록되었습니다.", "user_id": new_person.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error registering user: {e}")
        return jsonify({"message": "서버 오류로 사용자 등록 실패", "details": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()
    name = data.get('name')
    password = data.get('password')

    if not name or not password:
        return jsonify({"message": "아이디와 비밀번호를 모두 입력해주세요."}), 400

    user = Person.query.filter_by(name=name).first()

    if user and user.check_password(password):
        login_user(user) 
        print(f"User {user.name} logged in successfully.")
        if user.is_admin:
            return jsonify({"message": "로그인 성공!", "redirect_url": url_for('admin_page')}), 200
        else:
            return jsonify({"message": "로그인 성공!", "redirect_url": url_for('roulette_page')}), 200
    else:
        return jsonify({"message": "잘못된 아이디 또는 비밀번호입니다."}), 401 

@app.route('/api/logout', methods=['POST'])
@login_required 
def logout_api():
    logout_user() 
    print(f"User logged out.")
    return jsonify({"message": "로그아웃 되었습니다."}), 200

@app.route('/api/reset_password/<int:person_id>', methods=['POST'])
@login_required
def reset_password_api(person_id):
    if not current_user.is_admin:
        return jsonify({"message": "관리자만 비밀번호를 재설정할 수 있습니다."}), 403

    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password:
        return jsonify({"message": "새 비밀번호를 입력해주세요."}), 400
    if len(new_password) < 6:
        return jsonify({"message": "비밀번호는 최소 6자 이상이어야 합니다."}), 400

    try:
        person = Person.query.get(person_id)
        if not person:
            return jsonify({"message": "해당 ID의 사용자를 찾을 수 없습니다."}), 404
        
        person.set_password(new_password) 
        db.session.commit()
        print(f"Password for user '{person.name}' (ID: {person_id}) has been reset.")
        return jsonify({"message": f"'{person.name}' 님의 비밀번호가 성공적으로 재설정되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error resetting password for user (ID: {person_id}): {e}")
        return jsonify({"message": "서버 오류로 비밀번호 재설정 실패", "details": str(e)}), 500

@app.route('/api/delete_person/<int:person_id>', methods=['DELETE'])
@login_required
def delete_person_api(person_id):
    if not current_user.is_admin:
        return jsonify({"message": "관리자만 사용자를 삭제할 수 있습니다."}), 403

    try:
        person_to_delete = Person.query.get(person_id)
        if not person_to_delete:
            return jsonify({"message": "해당 ID의 이름을 찾을 수 없습니다."}), 404
        
        if person_to_delete.name == 'admin' and person_to_delete.is_admin:
            return jsonify({"message": "기본 관리자 계정은 삭제할 수 없습니다."}), 403

        db.session.delete(person_to_delete)
        db.session.commit()
        print(f"Deleted person: {person_to_delete.name} (ID: {person_id})")
        return jsonify({"message": "이름이 성공적으로 삭제되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting person (ID: {person_id}): {e}")
        return jsonify({"message": "서버 오류로 이름 삭제 실패", "details": str(e)}), 500

@app.route('/api/give_ticket/<int:person_id>', methods=['POST'])
@login_required
def give_ticket_api(person_id):
    if not current_user.is_admin:
        return jsonify({"message": "관리자만 룰렛권을 부여할 수 있습니다."}), 403

    try:
        person = Person.query.get(person_id)
        if not person:
            return jsonify({"message": "해당 ID의 이름을 찾을 수 없습니다."}), 404
        
        person.tickets += 1 
        db.session.commit()
        print(f"Gave 1 ticket to {person.name}. Total tickets: {person.tickets}")
        return jsonify({"message": "룰렛권이 성공적으로 부여되었습니다.", "tickets": person.tickets}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error giving ticket to person (ID: {person_id}): {e}")
        return jsonify({"message": "서버 오류로 룰렛권 부여 실패", "details": str(e)}), 500

# ✨✨ 새로운 룰렛권 삭제 API! ✨✨
@app.route('/api/remove_ticket/<int:person_id>', methods=['POST'])
@login_required
def remove_ticket_api(person_id):
    if not current_user.is_admin:
        return jsonify({"message": "관리자만 룰렛권을 삭제할 수 있습니다."}), 403

    try:
        person = Person.query.get(person_id)
        if not person:
            return jsonify({"message": "해당 ID의 이름을 찾을 수 없습니다."}), 404
        
        if person.tickets <= 0:
            return jsonify({"message": "룰렛권이 이미 0개입니다."}), 400

        person.tickets -= 1 
        db.session.commit()
        print(f"Removed 1 ticket from {person.name}. Total tickets: {person.tickets}")
        return jsonify({"message": "룰렛권이 성공적으로 삭제되었습니다.", "tickets": person.tickets}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error removing ticket from person (ID: {person_id}): {e}")
        return jsonify({"message": "서버 오류로 룰렛권 삭제 실패", "details": str(e)}), 500

@app.route('/api/give_star/<int:person_id>', methods=['POST'])
@login_required
def give_star_api(person_id):
    if not current_user.is_admin:
        return jsonify({"message": "관리자만 별점을 부여할 수 있습니다."}), 403

    try:
        person = Person.query.get(person_id)
        if not person:
            return jsonify({"message": "해당 ID의 이름을 찾을 수 없습니다."}), 404
        
        person.stars += 1
        db.session.commit()
        check_and_reset_stars(person)
        
        print(f"Gave 1 star to {person.name}. Total stars: {person.stars}")
        return jsonify({"message": "별점이 성공적으로 부여되었습니다.", "stars": person.stars}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error giving star to person (ID: {person_id}): {e}")
        return jsonify({"message": "서버 오류로 별점 부여 실패", "details": str(e)}), 500

# ✨✨ 새로운 별점 삭제 API! ✨✨
@app.route('/api/remove_star/<int:person_id>', methods=['POST'])
@login_required
def remove_star_api(person_id):
    if not current_user.is_admin:
        return jsonify({"message": "관리자만 별점을 삭제할 수 있습니다."}), 403

    try:
        person = Person.query.get(person_id)
        if not person:
            return jsonify({"message": "해당 ID의 이름을 찾을 수 없습니다."}), 404
        
        if person.stars <= 0:
            return jsonify({"message": "별점이 이미 0개입니다."}), 400

        person.stars -= 1
        db.session.commit()
        print(f"Removed 1 star from {person.name}. Total stars: {person.stars}")
        return jsonify({"message": "별점이 성공적으로 삭제되었습니다.", "stars": person.stars}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error removing star from person (ID: {person_id}): {e}")
        return jsonify({"message": "서버 오류로 별점 삭제 실패", "details": str(e)}), 500

@app.route('/api/get_people', methods=['GET'])
@login_required 
def get_people_api():
    try:
        people = Person.query.all() 
        people_data = [{
            'id': p.id,
            'name': p.name,
            'tickets': p.tickets,
            'is_admin': p.is_admin,
            'stars': p.stars
        } for p in people]
        return jsonify({"people": people_data}), 200
    except Exception as e:
        print(f"Error getting people data: {e}")
        return jsonify({"message": "서버 오류로 이름 목록 가져오기 실패", "details": str(e)}), 500

@app.route('/api/spin_roulette', methods=['POST'])
@login_required 
def spin_roulette():
    data = request.get_json()
    user_name = data.get('name') 

    if not user_name:
        return jsonify({'message': '사용자 이름이 필요합니다.'}), 400

    if current_user.name != user_name:
        return jsonify({'message': '본인의 룰렛만 돌릴 수 있습니다.'}), 403

    person = Person.query.filter_by(name=user_name).first()

    if not person:
        return jsonify({'message': '해당 사용자를 찾을 수 없습니다.'}), 404

    if person.tickets <= 0:
        return jsonify({'message': f'{user_name}님은 룰렛권이 없습니다.'}), 400

    person.tickets -= 1
    db.session.commit()

    return jsonify({
        'message': f'{user_name}님의 룰렛권이 1개 차감되었습니다.',
        'remaining_tickets': person.tickets
    }), 200


if __name__ == '__main__':
    with app.app_context():
        if os.environ.get('DATABASE_URL'):
            print("Using external database from DATABASE_URL environment variable.")
            try:
                db.create_all()
                print("External database tables initialized (if not already existing).")
            except OperationalError as e:
                print(f"Error initializing external database tables: {e}")
                print("Please ensure your external database is properly configured and accessible.")
            except Exception as e:
                print(f"Unexpected error during external database table creation: {e}")
        else:
            if not os.path.exists('site_data.db'):
                db.create_all()
                print("Database 'site_data.db' created and tables initialized.")
            else:
                print("Database 'site_data.db' already exists. Skipping table creation.")
        
        try:
            existing_admin = Person.query.filter_by(name='admin').first()
            
            if not existing_admin:
                admin_user = Person(name='admin', is_admin=True)
                admin_user.set_password('seoan1024')
                db.session.add(admin_user)
                db.session.commit()
                print("Initial admin user 'admin' created successfully during first run.")
            else:
                print("Admin user 'admin' already exists. Skipping creation.")
        except IntegrityError:
            db.session.rollback()
            print("Admin user 'admin' already exists due to IntegrityError (likely race condition). Skipping creation.")
        except OperationalError as e:
            db.session.rollback()
            print(f"OperationalError during admin user check/creation: {e}. This might occur if tables were not fully created or DB connection is unstable.")
            print("If you are on Railway, please ensure your database service is healthy and connected.")
        except Exception as e:
            db.session.rollback()
            print(f"Unexpected error during admin user check/creation: {e}")

    app.run(debug=False, port=5000)


