import eventlet
from flask import request
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#064473" 
users = {} 
thread = None

# 👇 설문조사 링크 (여기서 한 번만 고치면 다 적용되게 변수로 뺐어!)
SURVEY_LINK = "https://naver.me/5ixdyLOe"

@app.route('/')
def index():
    return render_template('index.html')

# [자동] 3분마다 설문 쏘는 알바생
def send_survey():
    while True:
        socketio.sleep(180) # 3분 대기
        noti = {
            'role': 'system', 
            'msg': f'📋 [자동 알림] 더 좋은 채팅방을 위해 설문에 참여해주세요.\n{SURVEY_LINK}'
        }
        socketio.emit('my_chat', noti)
        print("시스템: 자동 설문 전송 완료", flush=True)

def broadcast_user_list():
    user_list = list(users.values())
    count = len(users)
    emit('update_users', {'count': count, 'users': user_list}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    global thread
    users[request.sid] = "익명"
    
    if thread is None:
        thread = socketio.start_background_task(target=send_survey)

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

    # 1. 관리자 권한 심사
    if ADMIN_PASSWORD in original_name:
        if "오주환" in original_name:
            role = 'admin'
            real_name = "오주환"
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범 오주환" 

    print(f"[로그] 입력닉네임: {original_name} -> 권한: {role}", flush=True)
    users[request.sid] = real_name 
    broadcast_user_list()

    # ==========================================
    # 🔥 2. 강퇴 및 타노스 기능 (/강퇴)
    # ==========================================
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ")[1]
            if target_name == "all":
                all_sids = list(users.keys())
                for sid in all_sids:
                    if sid != request.sid: disconnect(sid)
                noti = {'role': 'system', 'msg': '☢️ 관리자가 모든 사용자를 강퇴시켰습니다!'}
                emit('my_chat', noti, broadcast=True)
                return 
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

    # ==========================================
    # 🔥 3. [NEW] 수동 설문 기능 (/설문)
    # ==========================================
    if role == 'admin' and msg == "/설문":
        # 시스템 메시지로 포장해서 전체 발송
        noti = {
            'role': 'system',
            'msg': f'📢 [관리자 공지] 여러분! 설문 참여 부탁드립니다.\n{SURVEY_LINK}'
        }
        print("시스템: 관리자 권한으로로 설문 전송 완료", flush=자 권한으
        emit('my_chat', noti, broadcast=True)
        return # 중요: "/설문"이라는 글자는 채팅창에 안 나가게 여기서 멈춤!

    # 4. 일반 메시지 전송
    response_data = {'name': real_name, 'msg': msg, 'role': role}
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)

