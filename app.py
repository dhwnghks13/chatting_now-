import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 대화 내용 저장소
messages = []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print("누군가 접속했습니다!", flush=True)
    
    # 1. 들어온 사람한테 지난 대화 내용 보여주기 (개인 귓속말)
    for msg in messages:
        emit('my_chat', msg)

    # 2. [추가된 기능] 모든 사람에게 입장 알림 쏘기! (방송)
    emit('my_chat', "👋 새로운 분이 입장하셨습니다!", broadcast=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    print(f"받은 메시지: {data}", flush=True)
    
    # 메시지 저장
    messages.append(data)
    
    # 3. [추가된 기능] 기억 제한을 150개로 늘림!
    if len(messages) > 150:
        messages.pop(0) # 150개 넘으면 제일 옛날 거 삭제
        
    emit('my_chat', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
