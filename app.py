import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chat_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PWS = ["#064473", "#14141815", "#80278027", "#20150303"]
users = {} 

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

def extract_youtube_data(msg):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.search(youtube_regex, msg)
    if match:
        video_id = match.group(6)
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg", f"https://www.youtube.com/watch?v={video_id}"
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    users[request.sid] = "익명"
    for data in messages:
        emit('my_chat', data)

@socketio.on('disconnect')
def handle_disconnect():
    nick = users.pop(request.sid, "익명")
    exit_msg = {'role': 'system', 'msg': f'🚪 [{nick}]님이 퇴장하셨습니다.', 'time': get_current_time()}
    emit('my_chat', exit_msg, broadcast=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = str(data.get('name', '익명')).strip()
    ylm = str(data.get('ylm', '미기입')).strip()
    msg = str(data.get('msg', '')).strip()
    if not msg: return

    role = 'normal'
    real_nickname = original_name
    is_sender_admin = any(pw in original_name for pw in ADMIN_PWS)

    if is_sender_admin:
        role = 'admin'
        for n in ["오주환", "이다운", "이태윤"]:
            if n in original_name: 
                real_nickname = n
                break
    
    users[request.sid] = real_nickname

    if role == 'admin' and msg.startswith("/강퇴 "):
        target_name = msg.replace("/강퇴 ", "").strip()
        target_sid = None
        for sid, nick in users.items():
            if nick == target_name:
                target_sid = sid
                break
        if target_sid:
            disconnect(target_sid)
            emit('my_chat', {'role': 'system', 'msg': f'🚫 [{target_name}]님이 강퇴당했습니다.'}, broadcast=True)
            return

    yt_thumb, yt_link = extract_youtube_data(msg)
    base_res = {
        'name': real_nickname, 'msg': msg, 'role': role, 
        'time': get_current_time(), 'yt_thumb': yt_thumb, 'yt_link': yt_link
    }
    
    messages.append(base_res)
    if len(messages) > 100: messages.pop(0)

    for sid, target_nick_with_pw in users.items():
        res = base_res.copy()
        if any(pw in str(target_nick_with_pw) for pw in ADMIN_PWS):
            res['real_name_secret'] = ylm
        emit('my_chat', res, room=sid)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
