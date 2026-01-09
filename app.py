<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💬 실시간 채팅방</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: 'Apple SD Gothic Neo', sans-serif; background: #f0f2f5; padding: 20px; margin: 0; }
        #chatBox { height: 75vh; background: white; border-radius: 12px; overflow-y: auto; padding: 20px; border: 1px solid #ddd; display: flex; flex-direction: column; gap: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .input-area { display: flex; gap: 8px; margin-top: 15px; }
        input { border: 1px solid #ddd; border-radius: 8px; padding: 10px; font-size: 14px; }
        #nickname { width: 15%; }
        #name { width: 15%; }
        #chatInput { flex-grow: 1; }
        button { background: #2196f3; color: white; border: none; border-radius: 8px; cursor: pointer; padding: 0 20px; font-weight: bold; }
        button:hover { background: #1976d2; }
        
        .msg { max-width: 80%; padding: 10px 14px; border-radius: 15px; position: relative; font-size: 15px; word-break: break-all; }
        .normal { align-self: flex-start; background: #e9efff; color: #333; border-bottom-left-radius: 2px; }
        .admin { align-self: flex-end; background: #e3f2fd; border: 2px solid #2196f3; color: #1a237e; border-bottom-right-radius: 2px; }
        .system { align-self: center; background: #f5f5f5; font-size: 12px; color: #777; border-radius: 20px; padding: 5px 15px; }
        
        .nick-label { font-size: 12px; font-weight: bold; margin-bottom: 4px; display: block; }
        .time { font-size: 10px; color: #999; margin-top: 5px; display: block; }
        .real-name { color: #ff5722; font-weight: normal; font-size: 11px; margin-left: 4px; }
        .yt-preview img { max-width: 250px; border-radius: 8px; margin-top: 8px; display: block; }
    </style>
</head>
<body>
    <div id="chatBox"></div>
    <div class="input-area">
        <input type="text" id="nickname" placeholder="닉네임">
        <input type="text" id="name" placeholder="실명(관리자용)">
        <input type="text" id="chatInput" placeholder="메시지를 입력하세요..." onkeypress="if(event.keyCode==13)send()">
        <button id="sendBtn" onclick="send()">전송</button>
    </div>

    <script>
        var socket = io();

        function send() {
            var nick = document.getElementById('nickname').value.trim();
            var real = document.getElementById('name').value.trim();
            var msg = document.getElementById('chatInput').value.trim();
            
            if(!nick || !real || !msg) {
                alert("모든 칸을 채워주세요!");
                return;
            }

            socket.emit('my_chat', { name: nick, ylm: real, msg: msg });
            document.getElementById('chatInput').value = "";
            document.getElementById('chatInput').focus();
        }

        socket.on('my_chat', function(data) {
            var chatBox = document.getElementById('chatBox');
            var div = document.createElement('div');
            
            if(data.role === 'system') {
                div.className = "msg system";
                div.innerText = data.msg;
            } else {
                div.className = "msg " + (data.role === 'admin' ? 'admin' : 'normal');
                
                var nameDisplay = data.name;
                // 관리자에게만 실명이 포함된 데이터가 전달됨
                if(data.real_name_secret) {
                    nameDisplay += `<span class="real-name">(${data.real_name_secret})</span>`;
                }

                var media = "";
                if(data.yt_thumb) {
                    media = `<div class="yt-preview"><a href="${data.yt_link}" target="_blank"><img src="${data.yt_thumb}"></a></div>`;
                }

                div.innerHTML = `<span class="nick-label">${nameDisplay}</span>` + 
                                `<div>${data.msg}${media}</div>` + 
                                `<span class="time">${data.time || ''}</span>`;
            }
            
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        });

        // 연결 끊김 처리
        socket.on('disconnect', function() {
            var chatBox = document.getElementById('chatBox');
            var div = document.createElement('div');
            div.className = "msg system";
            div.style.color = "red";
            div.style.fontWeight = "bold";
            div.innerText = "🚫 서버와 연결이 끊겼습니다. 새로고침이 필요합니다.";
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;

            document.getElementById('chatInput').disabled = true;
            document.getElementById('sendBtn').disabled = true;
            document.getElementById('sendBtn').style.background = "#ccc";
        });
    </script>
</body>
</html>
