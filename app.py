import eventlet
from flask import request
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#1234" # 🔑 관리자 비밀번호
users = {} # {소켓ID : 닉네임} 저장소

@app.route('/')
def index():
    return render_template('index.html')

# 👇 [함수] 접속자 명단 갱신해서 방송하기
def broadcast_user_list():
    user_list = list(users.values()) # 닉네임들만 뽑기
    count = len(users)
    # 'update_users' 라는 채널로 명단과 인원수 쏨
    emit('update_users', {'count': count, 'users': user_list}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    users[request.sid] = "익명" # 일단 들어오면 익명 등록
    broadcast_user_list() # 인원수 갱신 방송
    
    for data in messages:
        emit('my_chat', data)
    
    emit('my_chat', {'role': 'system', 'msg': '👋 새로운 분이 입장하셨습니다!'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        del users[request.sid] # 명부에서 삭제
    broadcast_user_list() # 나갔으니까 인원수 갱신 방송
    print("누군가 퇴장했습니다.", flush=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    msg = data.get('msg', '')
    
    role = 'normal'
    real_name = original_name

    # 1. 관리자 인증 (#1234)
    if ADMIN_PASSWORD in original_name:
        if "오주환" in original_name:
            role = 'admin'
            real_name = "오주환"
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범 오주환"

    # 2. 닉네임 업데이트 및 명단 갱신
    # (채팅을 쳐야 비로소 닉네임이 확정되므로 이때 명단 다시 뿌림)
    users[request.sid] = real_name 
    broadcast_user_list()

    # 3. 강퇴 명령어 (/강퇴 닉네임)
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ")[1]
            target_sid = None
            for sid, nickname in users.items():
                if nickname == target_name:
                    target_sid = sid
                    break
            if target_sid:
                disconnect(target_sid) # 연결 끊기 ✂️
                noti = {'role': 'system', 'msg': f'🚫 관리자가 [{target_name}]님을 강퇴시켰습니다.'}
                emit('my_chat', noti, broadcast=True)
                return 
        except:
            pass

    response_data = {'name': real_name, 'msg': msg, 'role': role}
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
