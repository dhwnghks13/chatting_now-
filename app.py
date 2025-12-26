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

# 접속자 명단 방송 함수
def broadcast_user_list():
    user_list = list(users.values())
    count = len(users)
    emit('update_users', {'count': count, 'users': user_list}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    users[request.sid] = "익명"
    broadcast_user_list()
    
    for data in messages:
        emit('my_chat', data)
    
    emit('my_chat', {'role': 'system', 'msg': '👋 새로운 분이 입장하셨습니다!'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        del users[request.sid]
    broadcast_user_list()
    print("누군가 퇴장했습니다.", flush=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    msg = data.get('msg', '')
    
    role = 'normal'
    real_name = original_name

    # 1. 관리자 인증
    if ADMIN_PASSWORD in original_name:
        if "오주환" in original_name:
            role = 'admin'
            real_name = "오주환"
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범 오주환"

    # 2. 명단 업데이트
    users[request.sid] = real_name 
    broadcast_user_list()

    # ======================================================
    # 🔥 3. 강퇴 기능 (개별 강퇴 + 전체 강퇴 추가됨!)
    # ======================================================
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ")[1] # "/강퇴" 뒤에 쓴 단어 가져오기
            
            # 🛑 [타노스 모드] /강퇴 all 입력 시
            if target_name == "all":
                # 현재 접속한 모든 소켓 ID를 가져옴
                all_sids = list(users.keys())
                
                for sid in all_sids:
                    # 나(관리자)는 강퇴하면 안 되니까 제외!
                    if sid != request.sid:
                        disconnect(sid) # 너 나가 ✂️
                
                # 처형 완료 메시지
                noti = {'role': 'system', 'msg': '☢️ 관리자가 모든 사용자를 강퇴시켰습니다! (방 폭파)'}
                emit('my_chat', noti, broadcast=True)
                return # 여기서 끝냄

            # 🔫 [일반 모드] /강퇴 닉네임 입력 시
            else:
                target_sid = None
                for sid, nickname in users.items():
                    if nickname == target_name:
                        target_sid = sid
                        break
                
                if target_sid:
                    disconnect(target_sid)
                    noti = {'role': 'system', 'msg': f'🚫 관리자가 [{target_name}]님을 강퇴시켰습니다.'}
                    emit('my_chat', noti, broadcast=True)
                    return 
        except:
            pass # 명령어 실수하면 무시

    # 4. 일반 메시지 전송
    response_data = {'name': real_name, 'msg': msg, 'role': role}
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
