import eventlet
from flask import request # 이거 없으면 강퇴 못함
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#1234" # 🔑 비밀번호

# 접속자 명부 (Socket ID : 닉네임)
users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    users[request.sid] = "익명" # 일단 익명으로 등록
    
    # 지난 대화 보여주기
    for data in messages:
        emit('my_chat', data)
    
    # 입장 알림
    emit('my_chat', {'role': 'system', 'msg': '👋 새로운 분이 입장하셨습니다!'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        del users[request.sid] # 나가면 명부에서 삭제
    print("누군가 퇴장했습니다.", flush=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    msg = data.get('msg', '')
    
    # --- 1. 신원 확인 (관리자 판별) ---
    role = 'normal'
    real_name = original_name

    # 비밀번호(#1234)가 포함되어 있으면?
    if ADMIN_PASSWORD in original_name:
        if "오주환" in original_name:
            role = 'admin'     # 대장 등급 부여 👑
            real_name = "오주환" # 비번 떼고 이름만 깔끔하게
    
    # 비번 없이 오주환 이름만 썼으면?
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범 오주환" # 검거 👮‍♂️

    # 명부에 이름 최신화 (이게 있어야 강퇴 가능)
    users[request.sid] = real_name

    # --- 2. 강퇴 명령어 처리 (/강퇴 닉네임) ---
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ")[1] # 강퇴할 놈 이름
            target_sid = None
            
            # 명부 뒤져서 그 놈 찾기
            for sid, nickname in users.items():
                if nickname == target_name:
                    target_sid = sid
                    break
            
            if target_sid:
                disconnect(target_sid) # ✂️ 연결 끊기!
                
                # 처형 공지
                noti = {'role': 'system', 'msg': f'🚫 관리자가 [{target_name}]님을 강퇴시켰습니다.'}
                emit('my_chat', noti, broadcast=True)
                return # 강퇴 명령어는 채팅창에 안 띄움
        except:
            pass # 명령어 실수하면 그냥 무시

    # --- 3. 일반 메시지 전송 ---
    response_data = {'name': real_name, 'msg': msg, 'role': role}
    
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
