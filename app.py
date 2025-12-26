import eventlet
from flask import request
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []

# 👇 [수정 완료] 이제 진짜 비밀번호는 '#064473'
ADMIN_PASSWORD = "#064473" 
users = {} 

@app.route('/')
def index():
    return render_template('index.html')

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

    # ==========================================
    # 👑 1. 관리자 권한 심사 (비밀번호 #064473)
    # ==========================================
    if ADMIN_PASSWORD in original_name:
        if "오주환" in original_name:
            role = 'admin'     # 합격!
            real_name = "오주환" # 화면에는 비번 떼고 보여줌
            
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범 오주환" 

    print(f"[로그] 입력닉네임: {original_name} -> 권한: {role}", flush=True)

    users[request.sid] = real_name 
    broadcast_user_list()

    # ==========================================
    # 💥 2. 타노스 & 강퇴 기능 (/강퇴 all)
    # ==========================================
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ")[1]
            
            # [타노스 모드] 방 폭파
            if target_name == "all":
                all_sids = list(users.keys())
                for sid in all_sids:
                    if sid != request.sid: 
                        disconnect(sid)
                
                noti = {'role': 'system', 'msg': '☢️ 관리자가 모든 사용자를 강퇴시켰습니다! (방 폭파)'}
                emit('my_chat', noti, broadcast=True)
                return 

            # [일반 강퇴] 한 명 저격
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
            pass

    response_data = {'name': real_name, 'msg': msg, 'role': role}
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
