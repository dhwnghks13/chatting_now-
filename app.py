import eventlet
from flask import request # 👈 request 추가 필수! (여기에 소켓 ID가 들어있음)
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect # 👈 disconnect 추가

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#1234"

# 👇 [핵심] 현재 접속한 사람들의 명부 (Socket ID : 닉네임)
users = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # 접속하면 명부에 일단 등록 (아직 닉네임 모름)
    users[request.sid] = "익명"
    
    for data in messages:
        emit('my_chat', data)
    emit('my_chat', {'role': 'system', 'msg': '👋 새로운 분이 입장하셨습니다!'}, broadcast=True)

# 👇 누군가 나갔을 때 명부에서 지우기
@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        del users[request.sid]
    print("누군가 퇴장했습니다.", flush=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    msg = data.get('msg', '')
    
    # 1. 신원 확인 (관리자 여부 판단)
    role = 'normal'
    real_name = original_name

    if ADMIN_PASSWORD in original_name:
        if "오주환" in original_name:
            role = 'admin'
            real_name = "오주환"
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범 오주환"

    # 👇 [중요] 이 사람이 누군지 명부에 최신화 (Socket ID -> 닉네임 매핑)
    users[request.sid] = real_name

    # ----------------------------------------------------
    # 🔥 2. 강퇴 명령어 처리 (관리자만 가능)
    # 명령어 형식: /강퇴 [닉네임]
    if role == 'admin' and msg.startswith("/강퇴 "):
        target_name = msg.split(" ")[1] # 띄어쓰기 뒤에 있는 이름 가져오기
        
        # 명부를 뒤져서 그 이름 가진 사람 찾기
        target_sid = None
        for sid, nickname in users.items():
            if nickname == target_name:
                target_sid = sid
                break
        
        if target_sid:
            # ✂️ 가차없이 연결 끊기
            disconnect(target_sid)
            
            # 모두에게 처형 소식 알림
            noti = {'role': 'system', 'msg': f'🚫 관리자가 [{target_name}]님을 강퇴시켰습니다.'}
            emit('my_chat', noti, broadcast=True)
            return # 강퇴 명령 자체는 채팅창에 안 띄움
    # ----------------------------------------------------

    # 3. 일반 메시지 전송
    response_data = {'name': real_name, 'msg': msg, 'role': role}
    
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
