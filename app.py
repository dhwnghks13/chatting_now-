import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import subprocess
import csv
import io
import re
import requests 
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
# 관리자 비밀번호 리스트
ADMIN_PWS = ["#064473", "#14141815", "#80278027", "#20150303"]
users = {} 
thread = None

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQu58p5LyRjvlIq-C9ryUfWHgNAkT8-Rlxo7O2LYTuylieIk9SWFc_J8oGKLNK7pkJe-5BSqafcoczx/pub?output=csv"
SURVEY_LINK = "https://docs.google.com/forms/d/e/1FAIpQLScWASCN8at3BE6U15UERFZX7VZ_zGafL6FT_IHed41J3T-Xug/viewform?usp=dialog"
LINK = f'<a href="{SURVEY_LINK}" target="_blank" style="color: #007bff; font-weight: bold;">[설문 참여하기]</a>'

def save_msg(data):
    messages.append(data)
    if len(messages) > 150:
        messages.pop(0)

def extract_youtube_data(msg):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.search(youtube_regex, msg)
    if match:
        video_id = match.group(6)
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg", f"https://www.youtube.com/watch?v={video_id}"
    return None, None

def get_current_time():
    now = datetime.utcnow() + timedelta(hours=9)
    return now.strftime('%p %I:%M').replace('AM', '오전').replace('PM', '오후')

def send_survey():
    while True:
        socketio.sleep(180) 
        noti = {'role': 'system', 'msg': f'📋 [자동 알림] 더 좋은 채팅방을 위해 설문에 참여해주세요. {LINK}', 'time': get_current_time()}
        save_msg(noti)
        socketio.emit('my_chat', noti)

def get_link_preview(text):
    url_regex = r'(https?://\S+)'
    match = re.search(url_regex, text)
    if not match or "youtube.com" in match.group(1) or "youtu.be" in match.group(1):
        return None 
    try:
        url = match.group(1)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=0.5)
        soup = BeautifulSoup(response.text, 'html.parser')
        og_image = soup.select_one('meta[property="og:image"]')
        og_title = soup.select_one('meta[property="og:title"]')
        og_desc = soup.select_one('meta[property="og:description"]')
        if not og_image: return None
        return {'url': url, 'image': og_image['content'], 'title': og_title['content'] if og_title else url, 'description': og_desc['content'] if og_desc else ''}
    except: return None

def broadcast_user_list():
    socketio.emit('update_users', {'count': len(users), 'users': list(users.values())})

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global thread
    users[request.sid] = "익명"
    if thread is None:
        thread = socketio.start_background_task(target=send_survey)
    broadcast_user_list()
    for data in messages:
        emit('my_chat', data)

@socketio.on('disconnect')
def handle_disconnect():
    nick = users.pop(request.sid, "익명")
    exit_msg = {'role': 'system', 'msg': f'🚪 [{nick}]님이 퇴장하셨습니다.', 'time': get_current_time()}
    save_msg(exit_msg)
    emit('my_chat', exit_msg, broadcast=True)
    broadcast_user_list()

@socketio.on('my_chat')
def handle_my_chat(data):
    original_name = data.get('name', '익명')
    ylm = data.get('ylm', '미기입') # 사용자가 보낸 실명
    msg = data.get('msg', '')
    
    role = 'normal'
    real_name = original_name

    # 관리자 체크
    is_admin = any(pw in original_name for pw in ADMIN_PWS)
    if is_admin:
        role = 'admin'
        for name in ["오주환", "이다운", "이태윤"]:
            if name in original_name: real_name = name
    elif original_name.strip() in ["오주환", "이다운"]:
        real_name = "사칭 방지 시스템 작동 중"

    # 중복 닉네임 검사
    for sid, name in users.items():
        if sid != request.sid and name == real_name:
            emit('my_chat', {'role': 'system', 'msg': f'🚫 [{real_name}]은 사용 중인 닉네임입니다.'})
            return 

    users[request.sid] = real_name
    broadcast_user_list()

    # 관리자 명령어 처리 (강퇴, 설문결과 등은 생략 가능하나 필요시 유지)
    if role == 'admin' and msg.startswith("/강퇴 "):
        target = msg.split(" ", 1)[1]
        for sid, name in list(users.items()):
            if name == target: disconnect(sid)
        return

    yt_thumb, yt_link = extract_youtube_data(msg)
    link_data = get_link_preview(msg)

    base_res = {
        'name': real_name, 'msg': msg, 'role': role, 
        'time': get_current_time(), 'yt_thumb': yt_thumb, 
        'yt_link': yt_link, 'link_data': link_data
    }
    save_msg(base_res)

    # 개별 전송 (실명 보안의 핵심)
    for sid, target_name in users.items():
        res = base_res.copy()
        # 이 메시지를 받는 사람이 관리자인지 확인
        if any(pw in str(target_name) for pw in ADMIN_PWS):
            res['real_name_secret'] = ylm # 관리자에게만 실명 슬쩍
        emit('my_chat', res, room=sid)

if __name__ == '__main__':
    socketio.run(app, debug=True)
