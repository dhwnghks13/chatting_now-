import eventlet
eventlet.monkey_patch()    # ⭕ 무조건 1등으로 실행!

from flask import Flask, render_template, request # 그 다음에 Flask 불러오기
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import requests  # 👈 [NEW] 인터넷 접속용
import csv       # 👈 [NEW] 데이터 분석용
import io        # 👈 [NEW] 데이터 변환용

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#064473" 
ADMIN_PASSWORD2 = "#14141815"
users = {} 
thread = None
# 👇 아까 1단계에서 복사한 '웹에 게시' 링크를 따옴표 안에 넣어!
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQu58p5LyRjvlIq-C9ryUfWHgNAkT8-Rlxo7O2LYTuylieIk9SWFc_J8oGKLNK7pkJe-5BSqafcoczx/pub?output=csv"

# 👇 설문조사 링크
SURVEY_LINK = "https://docs.google.com/forms/d/e/1FAIpQLScWASCN8at3BE6U15UERFZX7VZ_zGafL6FT_IHed41J3T-Xug/viewform?usp=dialog"
# 👇 [수정] 백슬래시(\) 제거함
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

# [자동] 3분마다 설문 쏘는 알바생
def send_survey():
    while True:
        socketio.sleep(180) # 3분 대기
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
            role = 'admin'  # 👈 [수정] 따옴표 붙여야 함! (role=admin 은 에러남)
            real_name = "이다운"
            
    elif original_name.strip() == "오주환" or original_name.strip() == "이다운":
        role = 'normal'
        real_name = "남을 따라하려는 자신을 잊은 사람" 

    print(f"[로그] 입력닉네임: {original_name} -> 권한: {role}", flush=True)
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
        print("시스템: 관리자 권한으로 설문 전송 완료", flush=True)
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
            print("시스템: 관리자 권한으로 공지 전송 완료", flush=True)
            return
        except:
            pass

    # 5. [자동] 설문 결과 실시간 집계 (/설문결과)
    if role == 'admin' and msg == "/설문결과":
        try:
            # 1. 구글 시트에서 데이터 가져오기
            response = requests.get(CSV_URL)
            response.encoding = 'utf-8' # 한글 깨짐 방지
            
            # 2. 데이터 읽기
            csv_data = response.text
            reader = csv.reader(io.StringIO(csv_data))
            next(reader) # 첫 번째 줄(질문 제목)은 건너뛰기
            
            # 3. 투표수 세기 (두 번째 칸[1]에 답변이 있다고 가정)
            vote_counts = {}
            total_votes = 0
            
            for row in reader:
                if len(row) > 1: # 데이터가 있는 줄만
                    answer = row[1] # 0번은 타임스탬프, 1번이 첫번째 질문 답변
                    vote_counts[answer] = vote_counts.get(answer, 0) + 1
                    total_votes += 1
            
            # 4. 결과 메시지 만들기
            result_text = f"📊 [실시간 설문 결과] (총 {total_votes}명 참여)\n"
            
            # 1등부터 순서대로 보여주기
            sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
            
            rank = 1
            for answer, count in sorted_votes:
                percent = round((count / total_votes) * 100, 1)
                result_text += f"\n{rank}위. {answer}: {count}명 ({percent}%)"
                rank += 1
                
            # 5. 전송
            noti = {
                'role': 'system',
                'msg': result_text,
                'time': get_current_time()
            }
            save_msg(noti)
            emit('my_chat', noti, broadcast=True)
            print("시스템: 설문 결과 집계 완료", flush=True)
            return

        except Exception as e:
            print(f"설문 에러: {e}", flush=True)
            noti = {'role': 'system', 'msg': '🚫 설문 데이터를 가져오는데 실패했습니다. 링크를 확인해주세요.'}
            emit('my_chat', noti, broadcast=True)
            return

    # 6. 일반 메시지 전송
    mention_target = None
    
    # 1. 메시지가 '@'로 시작하는지 확인
    if msg.startswith("@"):
        # 띄어쓰기를 기준으로 딱 2동강 냄! 
        # 예: "@오주환 밥 먹자" -> ["@오주환", "밥 먹자"]
        parts = msg.split(" ", 1) 
        
        first_word = parts[0] # "@오주환"
        
        # "@" 뒤에 이름이 제대로 있다면
        if len(first_word) > 1:
            mention_target = first_word[1:] # 맨 앞 '@' 떼고 이름만 저장 ("오주환")
            
            # 2. [핵심] 메시지 본문에서 닉네임 삭제하기
            if len(parts) > 1:
                # 뒤에 할 말이 있으면, 그 할 말만 메시지로 남김!
                msg = parts[1] 
            else:
                # 할 말 없이 "@오주환" 만 보냈다면?
                msg = "🔔 (콕 찔렀습니다)" # 빈 말풍선 대신 멘트 넣기
    
    response_data = {
        'name': real_name, 
        'msg': msg, 
        'role': role, 
        'time': get_current_time(),
        'mention': mention_target 
    }
    
    save_msg(response_data)
    emit('my_chat', response_data, broadcast=True)

