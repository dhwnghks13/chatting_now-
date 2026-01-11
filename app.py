import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'final_safe_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PWS = ["#064473", "#14141815", "#80278027", "#20150303"]
# 유저 장부: { sid: {'display': '보여지는이름', 'raw': '비번포함이름', 'is_admin': True/False} }
users = {} 

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    users[request.sid] = {'display': '익명', 'raw': '익명', 'is_admin': False}
    for data in messages:
        emit('my_chat', data)

@socketio.on('disconnect')
def handle_disconnect():
    user_info = users.pop(request.sid, {'display': '익명'})
    emit('my_chat', {'role': 'system', 'msg': f'🚪 [{user_info["display"]}]님이 퇴장하셨습니다.'}, broadcast=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    raw_nick = str(data.get('name', '익명')).strip()
    ylm = str(data.get('ylm', '미기입')).strip()
    msg = str(data.get('msg', '')).strip()
    
    if not msg: return

    # 1. 관리자 판별 및 이름 설정
    is_sender_admin = any(pw in raw_nick for pw in ADMIN_PWS)
    role = 'admin' if is_sender_admin else 'normal'
    
    display_name = raw_nick
    if is_sender_admin:
        for n in ["오주환", "이다운", "이태윤"]:
            if n in raw_nick:
                display_name = n + " ✔️(Official)" # 체크 표시 추가
                break
    
    # 장부 업데이트 (강퇴 시 검색을 위해 비번 포함 raw 이름도 저장)
    users[request.sid] = {'display': display_name, 'raw': raw_nick, 'is_admin': is_sender_admin}

    # 2. 강퇴 기능 (관리자만 가능)
    if is_sender_admin and msg.startswith("/강퇴 "):
        target_name = msg.replace("/강퇴 ", "").strip()
        target_sid = None
        
        # 장부에서 이름 검색 (체크 표시가 있는 이름이나 없는 이름 모두 대응)
        for sid, info in users.items():
            clean_nick = info['display'].replace(" ✔️(Official)", "").strip()
            if clean_nick == target_name or info['display'] == target_name:
                target_sid = sid
                break
        
        if target_sid:
            disconnect(target_sid)
            emit('my_chat', {'role': 'system', 'msg': f'🚫 [{target_name}]님이 관리자에 의해 강퇴되었습니다.'}, broadcast=True)
            return

    # 메시지 주머니
    base_res = {
        'name': display_name, 
        'msg': msg, 
        'role': role, 
        'time': get_current_time()
    }
    
    messages.append(base_res)
    if len(messages) > 100: messages.pop(0)

    # 3. 개별 전송 (받는 사람이 관리자인 경우에만 실명 추가)
    for sid, info in users.items():
        res = base_res.copy()
        if info['is_admin']: # 장부에 기록된 관리자 여부 확인
            res['real_name_secret'] = ylm
        emit('my_chat', res, room=sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
