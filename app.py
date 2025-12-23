# 1. 이 두 줄은 무조건 맨 위에! (순서 바꾸지 마)
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

# 2. cors_allowed_origins="*" <-- 이게 없으면 채팅 안 됨! 필수!
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    print(f"서버가 받은 메시지: {msg}") # 로그 확인용
    socketio.send(msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
