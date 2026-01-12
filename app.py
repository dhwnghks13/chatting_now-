import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'final_safe_key_2026'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PWS = ["#064473", "#14141815", "#80278027", "#20150303"]
users = {} # { sid: {'display': '이름', 'raw': '비번포함', 'is_admin': True} }

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

# 접속자 리스트를 모든 유저에게 업데이트해주는 함수
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
    user_info = users.pop(request.sid, {'display': '익명'})
    emit('my_chat', {'role': 'system', 'msg': f'🚪 [{user_info["display"]}]님이 퇴장하셨습니다.'}, broadcast=True)
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
    
    # 닉네임이 바뀌었을 수도 있으니 장부 업데이트
    users[request.sid] = {'display': display_name, 'raw': raw_nick, 'is_admin': is_sender_admin}
    update_user_list() # 닉네임 입력 후 리스트 갱신

    if is_sender_admin and msg.startswith("/강퇴 "):
        target_name = msg.replace("/강퇴 ", "").strip()
        target_sid = None
        for sid, info in users.items():
            clean_nick = info['display'].replace(" ✔️(Official)", "").strip()
            if clean_nick == target_name or info['display'] == target_name:
                target_sid = sid
                break
        if target_sid:
            disconnect(target_sid)
            emit('my_chat', {'role': 'system', 'msg': f'🚫 [{target_name}]님이 강퇴되었습니다.'}, broadcast=True)
            return

    base_res = {'name': display_name, 'msg': msg, 'role': role, 'time': get_current_time()}
    messages.append(base_res)
    if len(messages) > 100: messages.pop(0)

    for sid, info in users.items():
        res = base_res.copy()
        if info['is_admin']:
            res['real_name_secret'] = ylm
        emit('my_chat', res, room=sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
