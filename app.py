import eventlet
eventlet.monkey_patch() # 1등

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, disconnect
from datetime import datetime, timedelta
import subprocess # 👈 [핵무기] 리눅스 명령어 쓰는 도구
import csv
import io
import re
import requests 
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*")

messages = []
ADMIN_PASSWORD = "#064473" 
ADMIN_PASSWORD2 = "#14141815"
ADMIN_PASSWORD3 = "#80278027"
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

# 👇 [NEW] 유튜브 링크에서 썸네일과 영상 주소를 추출하는 함수
def extract_youtube_data(msg):
    # 유튜브 주소를 찾아내는 강력한 정규표현식 (짧은 주소, 긴 주소 다 됨)
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    
    match = re.search(youtube_regex, msg)
    if match:
        video_id = match.group(6) # 정규식에서 11자리 영상 ID만 쏙 뽑아냄
        # 유튜브 공식 썸네일 이미지 주소 (hqdefault.jpg가 고화질)
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        # 실제 클릭해서 이동할 영상 주소
        video_link = f"https://www.youtube.com/watch?v={video_id}"
        return thumbnail_url, video_link
    return None, None

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

# 👇 [NEW] 일반 웹사이트 미리보기 정보(Open Graph) 긁어오기
def get_link_preview(text):
    # 1. 메시지에서 URL 찾기 (http로 시작하는 주소)
    url_regex = r'(https?://\S+)'
    match = re.search(url_regex, text)
    
    if not match:
        return None # 주소 없으면 포기
        
    url = match.group(1)
    
    # 2. 이미 유튜브 로직이 있다면 유튜브는 패스! (유튜브는 전용 함수가 더 예쁘니까)
    if "youtube.com" in url or "youtu.be" in url:
        return None 

    try:
        # 3. 사이트 접속 (봇이 아니라 사람인 척 'User-Agent' 헤더 추가)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=2) # 2초 안에 응답 없으면 포기
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 4. 정보 찾기 (og:image, og:title 같은 태그 찾기)
        og_image = soup.select_one('meta[property="og:image"]')
        og_title = soup.select_one('meta[property="og:title"]')
        og_desc = soup.select_one('meta[property="og:description"]')
        
        # 5. 찾은 정보 정리 (없으면 빈칸)
        data = {
            'url': url,
            'image': og_image['content'] if og_image else '',
            'title': og_title['content'] if og_title else url,
            'description': og_desc['content'] if og_desc else ''
        }
        
        # 이미지가 없으면 미리보기 안 함
        if not data['image']: return None
        
        return data

    except Exception as e:
        print(f"링크 미리보기 실패: {e}")
        return None

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
    if ADMIN_PASSWORD in original_name or ADMIN_PASSWORD2 in original_name or ADMIN_PASSWORD3 in original_name:
        if "오주환" in original_name:
            role = 'admin'
            real_name = "오주환"
        elif "이다운" in original_name:
            role = 'admin'
            real_name = "이다운"
        elif "이태윤" in original_name:
            role = 'admin'
            real_name = "이태윤"
            
    elif original_name.strip() == "오주환" or original_name.strip() == "이다운":
        role = 'normal'
        real_name = "남을 따라하려는 자신을 잊은 사람" 

    # 🚨 [NEW] 닉네임 중복 검사 (여기가 추가된 핵심!) 🚨
    # users 장부를 한 명씩 확인한다.
    for sid, name in users.items():
        # 내 아이디(request.sid)가 아닌데, 나랑 똑같은 이름을 쓰는 사람이 있다면?
        if sid != request.sid and name == real_name:
            # 에러 메시지 보내고 함수 끝내기 (전송 안 함)
            noti = {'role': 'system', 'msg': f'🚫 [{real_name}] 닉네임은 이미 사용 중입니다!(이 메세지는 당신에게만 보여요!)'}
            emit('my_chat', noti) # 나한테만 보냄 (broadcast=True 안 씀)
            return 

    # 중복이 아니면 장부에 기록
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
    # 5. [자동] 설문 결과 실시간 집계 (/설문결과)
    if role == 'admin' and msg == "/설문결과":
        try:
            # 1. 리눅스 명령어로 데이터 가져오기 (성공한 그 코드!)
            cmd = ["curl", "-L", "-s", CSV_URL]
            result = subprocess.run(cmd, capture_output=True, text=True)
            csv_data = result.stdout
            
            # 2. 데이터 읽기
            reader = csv.reader(io.StringIO(csv_data))
            header = next(reader) # 첫 줄(제목) 건너뛰기
            
            # 저장할 변수들
            good_points = []   # 1번: 좋은점
            new_features = []  # 2번: 추가 기능
            bad_points = []    # 3번: 불편한점
            ratings = {}       # 4번: 평점 (숫자 세기)
            total_count = 0
            
            for row in reader:
                # 데이터가 꽉 찬 줄만 읽기 (최소 5칸: 타임스탬프+질문4개)
                if len(row) >= 5:
                    total_count += 1
                    
                    # 텍스트 내용 저장 (비어있지 않으면)
                    if row[1].strip(): good_points.append(row[1])
                    if row[2].strip(): new_features.append(row[2])
                    if row[3].strip(): bad_points.append(row[3])
                    
                    # 평점 카운트
                    rating = row[4].strip()
                    if rating:
                        ratings[rating] = ratings.get(rating, 0) + 1
            
            # 3. 결과 메시지 예쁘게 만들기
            result_text = f"📊 [설문 상세 분석] (총 {total_count}명 참여)\n"
            
            # (1) 평점 통계
            result_text += "\n⭐ [평점 현황]\n"
            sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
            for r, c in sorted_ratings:
                result_text += f"- {r}: {c}명\n"
                
            # (2) 서술형 답변 보여주기 (너무 길면 최신 3개만 보여주기)
            def get_summary(title, data_list):
                text = f"\n🗣️ [{title} (최신 의견)]\n"
                # 뒤에서부터 3개만 자르기 (최신순)
                for item in data_list[-3:]:
                    text += f"- {item}\n"
                if len(data_list) == 0: text += "- (의견 없음)\n"
                return text

            result_text += get_summary("🥰 채팅방의 좋은점", good_points)
            result_text += get_summary("💡 추가됐으면 하는 기능", new_features)
            result_text += get_summary("😤 채팅방의 불편한점", bad_points)
            
            result_text += "\n(더 자세한 내용은 엑셀에서 확인하세요!)"

            # 4. 전송
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
            noti = {'role': 'system', 'msg': '🚫 설문 데이터를 분석하는 중 에러가 발생했습니다.'}
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

    yt_thumb, yt_link = extract_youtube_data(msg)
    link_preview_data = get_link_preview(msg)
    
    response_data = {
        'name': real_name, 
        'msg': msg, 
        'role': role, 
        'time': get_current_time(),
        'mention': mention_target, 
        'yt_thumb': yt_thumb,
        'yt_link': yt_link,
        'link_data': link_preview_data
    }
    
    save_msg(response_data)
    emit('my_chat', response_data, broadcast=True)









