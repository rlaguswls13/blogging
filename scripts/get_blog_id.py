import os
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

def main():
    client_id = os.environ.get("BLOGGER_CLIENT_ID")
    client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
    refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")

    if not client_id or not client_secret or not refresh_token:
        print("Error: Blogger API 설정을 .env 파일에 먼저 입력해 주세요.", file=sys.stderr)
        print("필수 환경변수:", file=sys.stderr)
        print("  - BLOGGER_CLIENT_ID", file=sys.stderr)
        print("  - BLOGGER_CLIENT_SECRET", file=sys.stderr)
        print("  - BLOGGER_REFRESH_TOKEN", file=sys.stderr)
        sys.exit(1)

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    blogger = build("blogger", "v3", credentials=credentials)
    
    blog_url = sys.argv[1] if len(sys.argv) > 1 else 'http://beji-tech.blogspot.com'

    try:
        print(f"Blogger API로 URL 조회 중: {blog_url}")
        res = blogger.blogs().getByUrl(url=blog_url).execute()
        
        print('\n======================================')
        print('✅ 블로그 정보 조회 성공!')
        print(f"- 블로그 이름: {res.get('name')}")
        print(f"- 블로그 ID (BLOGGER_BLOG_ID): {res.get('id')}")
        print(f"- 블로그 URL: {res.get('url')}")
        print('======================================')
        print('\n위 BLOGGER_BLOG_ID를 .env 파일의 BLOGGER_BLOG_ID 항목에 입력하시면 됩니다.')
    except Exception as error:
        print('\n❌ 블로그 정보 조회 실패!', file=sys.stderr)
        print('에러 메세지:', str(error), file=sys.stderr)
        print('\n참고: Blogger 기본 도메인은 .blogspot.com 입니다. 커스텀 도메인을 사용하시는 경우 정확한 URL을 전달해 주세요.', file=sys.stderr)
        print('예: python scripts/get_blog_id.py https://your-custom-domain.com', file=sys.stderr)

if __name__ == "__main__":
    main()
