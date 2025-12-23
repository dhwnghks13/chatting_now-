import eventlet
eventlet.monkey_patch() # 무조건 맨 위!

from flask import Flask, render_template
from flask_socketio import SocketIO, emit # emit 추가됨!

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

# cors 설정 필수
socketio = SocketIO(app, cors_allowed_origins="*") 

@app.route('/')
def index():
    return render_template('index.html')

# 👇 [수정됨] 'message' 대신 'my_chat'이라는 이벤트를 받음
@socketio.on('my_chat')
def handle_my_chat(data):
    print(f"🔥 서버가 받은 데이터: {data}", flush=True) # 로그 강제 출력
    
    # 받은 데이터를 다시 모든 사람에게 'my_chat' 이름으로 뿌림
    emit('my_chat', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
