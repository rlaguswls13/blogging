import os
import datetime
from typing import Dict
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.publishers.base import BlogPublisher, ArticlePayload, PublishResult

class BloggerPublisher(BlogPublisher):
    @property
    def name(self) -> str:
        return "blogger"

    def get_credentials(self, require_refresh_token: bool = True) -> Dict[str, str]:
        client_id = os.environ.get("BLOGGER_CLIENT_ID")
        client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
        refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")
        blog_id = os.environ.get("BLOGGER_BLOG_ID")

        if not client_id or not client_secret or not blog_id:
            raise ValueError(
                "Google Blogger API 설정이 누락되었습니다.\n"
                "필수 환경변수: BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_BLOG_ID"
            )

        if require_refresh_token and not refresh_token:
            raise ValueError(
                "Google Blogger API 설정이 누락되었습니다.\n"
                "필수 환경변수: BLOGGER_REFRESH_TOKEN"
            )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token if refresh_token else "",
            "blog_id": blog_id
        }

    def get_blogger_service(self, creds_dict: Dict[str, str]):
        credentials = Credentials(
            token=None,
            refresh_token=creds_dict["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds_dict["client_id"],
            client_secret=creds_dict["client_secret"]
        )
        return build("blogger", "v3", credentials=credentials)

    def update_env_file(self, refresh_token: str):
        from pathlib import Path
        import re
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
            if content and not content.endswith('\n'):
                content += "\n"
            content += f"{new_token_line}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

        print("[Blogger] .env 파일에 BLOGGER_REFRESH_TOKEN이 자동으로 업데이트되었습니다!")

    def publish(self, article: ArticlePayload, dry_run: bool) -> PublishResult:
        creds_dict = self.get_credentials(require_refresh_token=False)
        blog_id = creds_dict["blog_id"]

        if dry_run:
            print(f"[Blogger Dry-Run] {'업데이트' if article.existingPostId else '신규 게시'}")
            print(f"[Blogger Dry-Run] 제목: {article.title}")
            print(f"[Blogger Dry-Run] 태그: {', '.join(article.tags)}")
            print(f"[Blogger Dry-Run] HTML 글자 수: {len(article.htmlContent)}자")
            post_id = article.existingPostId if article.existingPostId else "dry-run-blogger-post-id"
            return PublishResult(
                platform=self.name,
                postId=post_id,
                url=f"https://draft.blogger.com/blog/post/edit/{blog_id}/{post_id}",
                publishedAt=datetime.datetime.utcnow().isoformat() + "Z"
            )

        try:
            import urllib.parse
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import webbrowser
            import requests

            shared_data = {}

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
                            shared_data["error"] = error
                            return

                        if code:
                            self.send_response(200)
                            self.send_header("Content-Type", "text/html; charset=utf-8")
                            self.end_headers()
                            self.wfile.write("<h1>인증 성공!</h1><p>터미널로 돌아가 인증 완료 결과를 확인하고 이 창을 닫으셔도 됩니다.</p>".encode("utf-8"))
                            shared_data["code"] = code
                    else:
                        self.send_response(404)
                        self.end_headers()

            PORT = 8080
            REDIRECT_URI = f"http://localhost:{PORT}/oauth2callback"

            scopes = ["https://www.googleapis.com/auth/blogger"]
            auth_params = {
                "client_id": creds_dict["client_id"],
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": " ".join(scopes),
                "access_type": "offline",
                "prompt": "consent"
            }
            auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)

            server = HTTPServer(("localhost", PORT), OAuthCallbackHandler)

            print("\n======================================================")
            print("[Blogger] 구글 Blogger OAuth 브라우저 인증 시작")
            print(f"- 대기 포트: {PORT}")
            print(f"- 리디렉션 URI: {REDIRECT_URI}")
            print("======================================================\n")
            print(f"[Blogger] 아래 URL에 접속하여 구글 인증을 완료해 주세요:\n{auth_url}\n")
            print("[Blogger] 인증 대기 중...")

            webbrowser.open(auth_url)

            while "code" not in shared_data and "error" not in shared_data:
                server.handle_request()

            server.server_close()

            if "error" in shared_data:
                raise Exception(f"OAuth 인증 중 에러 발생: {shared_data['error']}")

            code = shared_data["code"]

            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "code": code,
                "client_id": creds_dict["client_id"],
                "client_secret": creds_dict["client_secret"],
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            res = requests.post(token_url, data=payload)
            if not res.ok:
                raise Exception(f"토큰 교환 실패: {res.text}")

            tokens = res.json()
            refresh_token = tokens.get("refresh_token")
            access_token = tokens.get("access_token")

            if refresh_token:
                self.update_env_file(refresh_token)
                os.environ["BLOGGER_REFRESH_TOKEN"] = refresh_token
            else:
                print("[Blogger] 경고: Refresh Token이 발급되지 않았습니다. 기존 토큰을 유지합니다.")
                refresh_token = creds_dict.get("refresh_token")

            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=creds_dict["client_id"],
                client_secret=creds_dict["client_secret"]
            )

            service = build("blogger", "v3", credentials=credentials)
            posts = service.posts()

            body = {
                "title": article.title,
                "content": article.htmlContent,
                "labels": article.tags
            }

            if article.existingPostId:
                request = posts.update(
                    blogId=blog_id,
                    postId=article.existingPostId,
                    body=body
                )
            else:
                request = posts.insert(
                    blogId=blog_id,
                    isDraft=article.isDraft if article.isDraft is not None else False,
                    body=body
                )

            response = request.execute()

            post_id = response.get("id")
            url = response.get("url")

            if not post_id or not url:
                raise Exception("Blogger API 응답에서 postId 또는 url을 찾을 수 없습니다.")

            published_at = response.get("published", datetime.datetime.utcnow().isoformat() + "Z")

            return PublishResult(
                platform=self.name,
                postId=post_id,
                url=url,
                publishedAt=published_at
            )
        except Exception as error:
            raise Exception(f"Blogger 게시 중 오류 발생: {str(error)}")

    def validate_auth(self) -> bool:
        try:
            creds_dict = self.get_credentials(require_refresh_token=True)
            if not creds_dict.get("refresh_token"):
                return False
            service = self.get_blogger_service(creds_dict)
            service.blogs().get(blogId=creds_dict["blog_id"]).execute()
            return True
        except Exception:
            return False
