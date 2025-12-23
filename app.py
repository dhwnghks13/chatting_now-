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
    
    # 1. 들어온 사람한테 지난 대화 보여주기
    for data in messages:
        emit('my_chat', data)

    # 2. 입장 알림 (이름을 '📢 알림'으로 설정해서 보냄)
    emit('my_chat', {'name': '📢 알림', 'msg': '👋 새로운 분이 입장하셨습니다!'}, broadcast=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    # data는 이제 {'name': '닉네임', 'msg': '내용'} 형태의 덩어리임
    print(f"받은 데이터: {data}", flush=True)
    
    # 메시지 저장
    messages.append(data)
    
    # 기억력 제한 (150개)
    if len(messages) > 150:
        messages.pop(0) 
        
    emit('my_chat', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
