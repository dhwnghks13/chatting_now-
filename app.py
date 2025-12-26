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

# 👇 [추가 1] 백그라운드 작업을 위한 변수 (알바생 명부)
thread = None

@app.route('/')
def index():
    return render_template('index.html')

# 👇 [추가 2] 3분마다 설문 링크를 쏘는 알바생의 업무 내용
def send_survey():
    while True:
        # 180초(3분) 동안 대기 (서버 안 멈춤!)
        socketio.sleep(180) 
        
        # 설문조사 링크 (여기에 네 링크를 넣어!)
        survey_link = "https://naver.me/5ixdyLOe"
        
        # 시스템 메시지로 전송
        noti = {
            'role': 'system', 
            'msg': f'📋 잠깐! 더 좋은 채팅방을 위해 설문에 참여해주세요.\n{survey_link}'
        }
        socketio.emit('my_chat', noti)
        print("시스템: 설문 링크 전송 완료", flush=True)

def broadcast_user_list():
    user_list = list(users.values())
    count = len(users)
    emit('update_users', {'count': count, 'users': user_list}, broadcast=True)

@socketio.on('connect')
def handle_connect():
    global thread # 전역 변수 사용 선언
    
    users[request.sid] = "익명"
    
    # 👇 [추가 3] 알바생이 아직 없으면, 지금 고용해서 일을 시작시킴!
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

    # 1. 관리자 권한
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

    # 2. 강퇴 기능
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ")[1]
            if target_name == "all":
                all_sids = list(users.keys())
                for sid in all_sids:
                    if sid != request.sid: 
                        disconnect(sid)
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
    if role === 'admin and msg == "/설문"
        survey_link = "https://naver.me/5ixdyLOe"
        
        # 시스템 메시지로 전송
        noti = {
            'role': 'system', 
            'msg': f'📋 잠깐! 더 좋은 채팅방을 위해 설문에 참여해주세요.\n{survey_link}'
        }
        socketio.emit('my_chat', noti)
        print("시스템: 관리자 명령으로 설문 링크 전송 완료", flush=True)
    response_data = {'name': real_name, 'msg': msg, 'role': role}
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)

