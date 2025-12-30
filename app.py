import eventlet
eventlet.monkey_patch() # 1등

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import subprocess # 👈 [핵무기] 리눅스 명령어 쓰는 도구
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#064473" 
ADMIN_PASSWORD2 = "#14141815"
users = {} 
thread = None

# 👇 설문조사 결과 (CSV) 링크
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQu58p5LyRjvlIq-C9ryUfWHgNAkT8-Rlxo7O2LYTuylieIk9SWFc_J8oGKLNK7pkJe-5BSqafcoczx/pub?output=csv"

# 👇 설문조사 참여 링크
SURVEY_LINK = "https://docs.google.com/forms/d/e/1FAIpQLScWASCN8at3BE6U15UERFZX7VZ_zGafL6FT_IHed41J3T-Xug/viewform?usp=dialog"
LINK = f'<a href="{SURVEY_LINK}" target="_blank" style="color: #007bff; font-weight: bold;">[설문 참여하기]</a>'

@app.route('/')
def index():
    return render_template('index.html')

def save_msg(data):
    messages.append(data)
    if len(messages) > 150:
        messages.pop(0)

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

def send_survey():
    while True:
        socketio.sleep(180) 
        noti = {
            'role': 'system', 
            'msg': f'📋 [자동 알림] 더 좋은 채팅방을 위해 설문에 참여해주세요. {LINK}'
        }
        save_msg(noti)
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

    welcome_msg={'role': 'system', 'msg': '👋 새로운 분이 입장하셨습니다!', 'time': get_current_time()}
    save_msg(welcome_msg)
    emit('my_chat', welcome_msg, broadcast=True)
    

@socketio.on('disconnect')
def handle_disconnect():
    nickname = users.get(request.sid, "익명")
    if request.sid in users:
        del users[request.sid]

    exit_msg = {
        'role': 'system', 
        'msg': f'🚪 [{nickname}]님이 퇴장하셨습니다.',
        'time': get_current_time()
    }
    
    save_msg(exit_msg)
    emit('my_chat', exit_msg, broadcast=True)
    broadcast_user_list()
    
    print(f"[{nickname}]님이 퇴장했습니다.", flush=True)

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    msg = data.get('msg', '')
    
    role = 'normal'
    real_name = original_name

    # 1. 관리자 권한 심사
    if ADMIN_PASSWORD in original_name or ADMIN_PASSWORD2 in original_name:
        if "오주환" in original_name:
            role = 'admin'
            real_name = "오주환"
        elif "이다운" in original_name:
            role = 'admin' 
            real_name = "이다운"
            
    elif original_name.strip() == "오주환" or original_name.strip() == "이다운":
        role = 'normal'
        real_name = "남을 따라하려는 자신을 잊은 사람" 

    users[request.sid] = real_name 
    broadcast_user_list()

    # 2. 강퇴 기능
    if role == 'admin' and msg.startswith("/강퇴 "):
        try:
            target_name = msg.split(" ", 1)[1]
            if target_name == "all":
                all_sids = list(users.keys())
                for sid in all_sids:
                    if sid != request.sid: disconnect(sid)
                noti = {'role': 'system', 'msg': '☢️ 관리자가 모든 사용자를 강퇴시켰습니다!'}
                save_msg(noti)
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
                    save_msg(noti)
                    emit('my_chat', noti, broadcast=True)
                    return 
        except:
            pass

    # 3. 수동 설문 기능 (/설문)
    if role == 'admin' and msg == "/설문":
        noti = {
            'role': 'system',
            'msg': f'📢 [관리자 공지] 여러분! 설문 참여 부탁드립니다. {LINK}'
        }
        save_msg(noti)
        emit('my_chat', noti, broadcast=True)
        return 

    # 4. 수동 공지 기능 (/공지)
    if role == 'admin' and msg.startswith("/공지 "):
        try:
            content = msg.split(" ", 1)[1]
            noti = {
                'role': 'system',
                'msg': f"📢 [공지사항] {content}",
                'time': get_current_time()
            }
            save_msg(noti)
            emit('my_chat', noti, broadcast=True)
            return
        except:
            pass

    # 5. [자동] 설문 결과 실시간 집계 (/설문결과)
    if role == 'admin' and msg == "/설문결과":
        try:
            # 👇 [필살기] 리눅스 명령어(curl)로 강제 다운로드
            # 파이썬 네트워크 안 씀. 무조건 됨.
            cmd = ["curl", "-L", "-s", CSV_URL]
            result = subprocess.run(cmd, capture_output=True, text=True)
            csv_data = result.stdout
            
            reader = csv.reader(io.StringIO(csv_data))
            next(reader) 
            
            vote_counts = {}
            total_votes = 0
            
            for row in reader:
                if len(row) > 1: 
                    answer = row[1] 
                    vote_counts[answer] = vote_counts.get(answer, 0) + 1
                    total_votes += 1
            
            result_text = f"📊 [실시간 설문 결과] (총 {total_votes}명 참여)\n"
            sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
            
            rank = 1
            for answer, count in sorted_votes:
                percent = round((count / total_votes) * 100, 1)
                result_text += f"\n{rank}위. {answer}: {count}명 ({percent}%)"
                rank += 1
                
            noti = {
                'role': 'system',
                'msg': result_text,
                'time': get_current_time()
            }
            save_msg(noti)
            emit('my_chat', noti, broadcast=True)
            return

        except Exception as e:
            print(f"설문 에러: {e}", flush=True)
            noti = {'role': 'system', 'msg': '🚫 설문 데이터를 가져오는데 실패했습니다.'}
            emit('my_chat', noti, broadcast=True)
            return

    # 6. 일반 메시지 전송
    mention_target = None
    if msg.startswith("@"):
        parts = msg.split(" ", 1) 
        first_word = parts[0]
        if len(first_word) > 1:
            mention_target = first_word[1:] 
            if len(parts) > 1:
                msg = parts[1] 
            else:
                msg = "🔔 (콕 찔렀습니다)" 
    
    response_data = {
        'name': real_name, 
        'msg': msg, 
        'role': role, 
        'time': get_current_time(),
        'mention': mention_target 
    }
    
    save_msg(response_data)
    emit('my_chat', response_data, broadcast=True)
