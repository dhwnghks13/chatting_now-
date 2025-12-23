import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []

# 👇 진짜 주인님만 아는 비밀번호 (너만 알고 있어야 해!)
ADMIN_PASSWORD = "#064473"

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    # 저장된 대화 내용 보내기
    for data in messages:
        emit('my_chat', data)
    
    emit('my_chat', {'role': 'system', 'msg': '👋 새로운 분이 입장하셨습니다!'}, broadcast=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    msg = data.get('msg', '')
    
    # 👇 [핵심] 신원 확인 로직
    role = 'normal' # 기본은 일반인
    real_name = original_name

    # 1. 닉네임에 비밀번호가 포함되어 있는지 검사
    if ADMIN_PASSWORD in original_name:
        # 비밀번호가 맞으면? -> 진짜 오주환!
        if "오주환" in original_name: 
            role = 'admin' # 대장 계급 부여
            real_name = "오주환" # 이름 깔끔하게 정리 (비번 숨김)
    
    # 2. 비밀번호 없이 감히 '오주환' 이름을 썼다면? -> 사칭범 검거!
    elif original_name.strip() == "오주환":
        role = 'normal'
        real_name = "사칭범이라는 남을 따라하려는 자" # 강제로 이름 바꿔버림 ㅋㅋㅋ

    # 3. 데이터를 다시 포장 (role 정보 추가)
    response_data = {'name': real_name, 'msg': msg, 'role': role}

    print(f"보내는 데이터: {response_data}", flush=True)
    
    messages.append(response_data)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', response_data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)

