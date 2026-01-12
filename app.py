import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'final_boss_key'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PWS = ["#064473", "#14141815", "#80278027", "#20150303"]
users = {}
current_poll_link = "" # 현재 활성화된 설문 링크 저장

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

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
    for data in messages:
        emit('my_chat', data)

@socketio.on('disconnect')
def handle_disconnect():
    users.pop(request.sid, None)
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
    
    users[request.sid] = {'display': display_name, 'raw': raw_nick, 'is_admin': is_sender_admin}

    # --- 관리자 명령어 세트 ---
    if is_sender_admin:
        # 1. 설문 링크 뿌리기 (/설문 링크)
        if msg.startswith("/설문 "):
            global current_poll_link
            current_poll_link = msg.replace("/설문 ", "").strip()
            poll_title = "새로운 설문조사"
            try:
                # 링크 제목 크롤링
                res = requests.get(current_poll_link, timeout=3)
                soup = BeautifulSoup(res.text, 'html.parser')
                poll_title = soup.title.string if soup.title else "설문조사 참여"
            except:
                pass
            
            notice = {
                'role': 'system', 
                'msg': f'📝 [설문 시작]\n제목: {poll_title}\n링크: {current_poll_link}\n모두 참여해 주세요!'
            }
            emit('my_chat', notice, broadcast=True)
            return

        # 2. 설문 결과 공지 (/설문결과 내용)
        if msg.startswith("/설문결과 "):
            result_text = msg.replace("/설문결과 ", "").strip()
            emit('my_chat', {'role': 'system', 'msg': f'📊 [설문 결과 발표]\n{result_text}'}, broadcast=True)
            return

        # 3. 공지사항 (/공지 내용)
        if msg.startswith("/공지 "):
            content = msg.replace("/공지 ", "").strip()
            emit('my_chat', {'role': 'system', 'msg': f'📢 [공지]: {content}'}, broadcast=True)
            return

        # 4. 강퇴 (/강퇴 닉네임 또는 /강퇴 all)
        if msg.startswith("/강퇴 "):
            target = msg.replace("/강퇴 ", "").strip()
            if target == "all":
                for sid in list(users.keys()):
                    if sid != request.sid: disconnect(sid)
                emit('my_chat', {'role': 'system', 'msg': '☢️ 전원 강퇴 완료'}, broadcast=True)
            else:
                for sid, info in users.items():
                    if info['display'].replace(" ✔️(Official)", "") == target:
                        disconnect(sid)
                        emit('my_chat', {'role': 'system', 'msg': f'🚫 {target} 강퇴'}, broadcast=True)
                        break
            return

    # 일반 메시지 전송 로직
    base_res = {'name': display_name, 'msg': msg, 'role': role, 'time': get_current_time()}
    messages.append(base_res)
    if len(messages) > 100: messages.pop(0)

    for sid, info in users.items():
        res = base_res.copy()
        if info['is_admin']: res['real_name_secret'] = ylm
        emit('my_chat', res, room=sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
