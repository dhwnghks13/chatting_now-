import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chat_secret_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PWS = ["#064473", "#14141815", "#80278027", "#20150303"]
users = {} 

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

# 접속자 명단을 모든 유저에게 전송하는 함수
def update_user_list():
    user_names = [info['display'] for info in users.values()]
    socketio.emit('update_users', {'count': len(users), 'users': user_names})

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    users[request.sid] = {'display': '익명', 'raw': '익명', 'is_admin': False}
    update_user_list()
    # 기존 메시지 불러오기
    for data in messages:
        emit('my_chat', data)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        users.pop(request.sid)
    update_user_list()

@socketio.on('my_chat')
def handle_my_chat(data):
    raw_nick = str(data.get('name', '익명')).strip()
    ylm = str(data.get('ylm', '미기입')).strip()
    msg = str(data.get('msg', '')).strip()
    if not msg: return

    is_sender_admin = any(pw in raw_nick for pw in ADMIN_PWS)
    role = 'admin' if is_sender_admin else 'normal'
    
    display_name = raw_nick
    if is_sender_admin:
        for n in ["오주환", "이다운", "이태윤"]:
            if n in raw_nick:
                display_name = n + " ✔️(Official)"
                break
    
    # 유저 정보 갱신 및 리스트 업데이트
    users[request.sid] = {'display': display_name, 'raw': raw_nick, 'is_admin': is_sender_admin}
    update_user_list()

    # --- 관리자 명령어 세트 ---
    if is_sender_admin:
        # 1. 공지 명령어
        if msg.startswith("/공지 "):
            txt = msg.replace("/공지 ", "").strip()
            emit('my_chat', {'role': 'system', 'msg': f'📢 [공지]\n{txt}'}, broadcast=True)
            return
        
        # 2. 설문 명령어 (지정된 구글 폼 링크)
        if msg.startswith("/설문 "):
            link = "https://docs.google.com/forms/d/e/1FAIpQLScWASCN8at3BE6U15UERFZX7VZ_zGafL6FT_IHed41J3T-Xug/viewform?usp=dialog"
            
            # \n 대신 <br>을 쓰고, 링크를 <a> 태그로 감싸기! (target="_blank"는 새 창에서 열리게 해줘)
            html_msg = f'📝 [설문 시작]<br>링크: <a href="{link}" target="_blank" style="color: #2196f3; font-weight: bold; text-decoration: underline;">여기를 눌러서 설문 참여하기</a><br>참여부탁'
            
            emit('my_chat', {'role': 'system', 'msg': html_msg}, broadcast=True)
            return
        
        # 3. 강퇴 명령어 (all 또는 특정 닉네임)
        if msg.startswith("/강퇴 "):
            target = msg.replace("/강퇴 ", "").strip()
            if target == "all":
                for sid in list(users.keys()):
                    if sid != request.sid: # 명령어를 친 관리자 본인은 제외
                        disconnect(sid)
                emit('my_chat', {'role': 'system', 'msg': '☢️ 관리자가 전원을 강퇴시켰습니다.'}, broadcast=True)
            else:
                for sid, info in users.items():
                    if info['display'].replace(" ✔️(Official)", "") == target:
                        disconnect(sid)
                        emit('my_chat', {'role': 'system', 'msg': f'🚫 [{target}] 강퇴 완료.'}, broadcast=True)
                        break
            return

    # 일반 메시지 구성
    base_res = {
        'name': display_name, 
        'msg': msg, 
        'role': role, 
        'time': get_current_time()
    }
    
    messages.append(base_res)
    if len(messages) > 100: messages.pop(0)

    # 유저별로 실명 포함 여부 결정해서 전송
    for sid, info in users.items():
        res = base_res.copy()
        if info['is_admin']: 
            res['real_name_secret'] = ylm # 관리자 화면에만 실명 노출
        emit('my_chat', res, room=sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
