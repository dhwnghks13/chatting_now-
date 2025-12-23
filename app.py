from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret' # 보안 키 (아무거나 적어도 됨)
socketio = SocketIO(app, cors_allowed_origins="*") # 중요: 다른 주소 접속 허용!

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    print(f"메시지: {msg}")
    socketio.send(msg, broadcast=True)

if __name__ == '__main__':
    # 서버에서는 이 부분 대신 gunicorn을 쓸 거라 괜찮지만,
    # 로컬 테스트용으로 남겨둬.
    socketio.run(app, debug=True)