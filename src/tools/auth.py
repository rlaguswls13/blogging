import os
import sys
import re
from pathlib import Path
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

PORT = 8080
REDIRECT_URI = f"http://localhost:{PORT}/oauth2callback"
client_id = os.environ.get("BLOGGER_CLIENT_ID")
client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path == "/oauth2callback":
            query_params = urllib.parse.parse_qs(parsed_url.query)
            code = query_params.get("code", [None])[0]
            error = query_params.get("error", [None])[0]
            
            if error:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h1>인증 실패</h1><p>에러 발생: {error}</p>".encode("utf-8"))
                print(f"인증 에러: {error}")
                sys.exit(1)
                
            if code:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<h1>인증 성공!</h1><p>터미널로 돌아가 인증 완료 결과를 확인하고 이 창을 닫으셔도 됩니다.</p>".encode("utf-8"))
                
                try:
                    print("Authorization code 수신 완료. Token 교환 중...")
                    token_url = "https://oauth2.googleapis.com/token"
                    payload = {
                        "code": code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": REDIRECT_URI,
                        "grant_type": "authorization_code"
                    }
                    res = requests.post(token_url, data=payload)
                    if not res.ok:
                        raise Exception(res.text)
                        
                    tokens = res.json()
                    refresh_token = tokens.get("refresh_token")
                    
                    if not refresh_token:
                        print("\n⚠️ 경고: Refresh Token이 발급되지 않았습니다.")
                        print("이미 권한 동의를 마친 계정일 수 있습니다. 구글 계정 보안 설정에서 해당 앱의 접근 권한을 삭제하고 다시 시도하시거나, prompt: consent 설정을 확인하세요.")
                    else:
                        print("\n✅ Refresh Token 획득 성공!")
                        update_env_file(refresh_token)
                except Exception as err:
                    print(f"토큰 교환 실패: {str(err)}")
                finally:
                    sys.exit(0)
        else:
            self.send_response(404)
            self.end_headers()

def update_env_file(refresh_token: str):
    env_path = Path.cwd() / ".env"
    content = ""
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
            
    token_pattern = re.compile(r"^BLOGGER_REFRESH_TOKEN=.*$", re.MULTILINE)
    new_token_line = f"BLOGGER_REFRESH_TOKEN={refresh_token}"
    
    if token_pattern.search(content):
        content = token_pattern.sub(new_token_line, content)
    else:
        content += f"\n{new_token_line}\n"
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("✅ .env 파일에 BLOGGER_REFRESH_TOKEN이 자동으로 업데이트되었습니다!")

def main():
    if not client_id or not client_secret:
        print("Error: .env 파일에 BLOGGER_CLIENT_ID와 BLOGGER_CLIENT_SECRET을 먼저 입력해 주세요.", file=sys.stderr)
        sys.exit(1)
        
    scopes = ["https://www.googleapis.com/auth/blogger"]
    auth_params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)
    
    server = HTTPServer(("localhost", PORT), OAuthCallbackHandler)
    
    print("\n======================================================")
    print("🔑 구글 Blogger OAuth 인증 프로세스 시작")
    print(f"- 대기 포트: {PORT}")
    print(f"- 리디렉션 URI: {REDIRECT_URI}")
    print("⚠️ Google Cloud Console 사용자 인증 정보에서 아래 주소를 '승인된 리디렉션 URI'에 추가해 주어야 합니다:")
    print(f"  => {REDIRECT_URI}")
    print("======================================================\n")
    print("브라우저를 열어 구글 로그인창으로 이동합니다...")
    
    webbrowser.open(auth_url)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("\n로컬 인증 서버가 종료되었습니다.")

if __name__ == "__main__":
    main()
