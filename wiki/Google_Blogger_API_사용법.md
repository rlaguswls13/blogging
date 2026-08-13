# Google Blogger API 사용법

구글 블로거(Blogger) API v3를 활용하여 외부(예: Python 스크립트)에서 자동으로 블로그 글을 배포하고 관리하는 가이드라인입니다.

## 1. API 연동 준비 및 OAuth 2.0 인증

Blogger API와 연동하기 위해 Google Cloud Console에서 프로젝트를 설정하고 OAuth 2.0 사용자 인증 정보를 생성해야 합니다.

- **OAuth 2.0 Native Flow**: 데스크톱 및 로컬 환경에서 실행되는 자동화 파이프라인의 경우 데스크톱 앱(Desktop App) 타입의 사용자 인증 정보를 다운로드해 로컬 클라이언트로 브라우저 인증 루프를 처리합니다.
- **인증 토큰 저장**: 첫 인증 완료 후 발급되는 `token.json` (또는 `credentials.json` 기반 토큰) 파일을 안전하게 보관하여 무인 자동 실행 시 백그라운드 갱신(Refresh Token)이 가능하도록 처리합니다.

## 2. Python 배포 연동 코드 구성

Python `google-api-python-client` 패키지를 활용한 기본적인 포스팅 배포 예시입니다.

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 인증 정보를 로드하고 빌드합니다.
creds = Credentials.from_authorized_user_file('token.json')
service = build('blogger', 'v3', credentials=creds)

# 포스팅 데이터 구조를 선언합니다.
body = {
    "kind": "blogger#post",
    "title": "자동화 배포 테스트",
    "content": "<p>이 글은 Blogger API를 통해 업로드되었습니다.</p>"
}

# 특정 블로그 ID로 포스팅을 요청합니다.
posts = service.posts()
result = posts.insert(blogId='YOUR_BLOG_ID', body=body).execute()
print(f"배포 완료: {result.get('url')}")
```

## 3. 제한 및 모범 사례 (Best Practices)

- **일일 할당량**: Blogger API v3는 기본적으로 하루에 배포할 수 있는 포스팅 수 및 API 호출 수 제한(기본 100건 등)이 있습니다. 대량 배포가 필요한 경우 Google Cloud Console을 통해 할당량 증설을 별도 요청해야 합니다.
- **테스팅 상태**: OAuth 동의 화면의 게시 상태가 `Testing`인 경우, 지정된 테스트 사용자(최대 100명)만 로그인 및 API 이용이 가능하며 토큰이 주기적으로 만료됩니다. 운영 환경(Production)으로 전환하려면 앱 검증 과정을 통과해야 합니다.

## 4. 후속 연구 및 꼬리질문

- Blogger API의 포스팅 개수 증설을 요청하는 세부 절차와 조건은 무엇인가?
- OAuth 동의 화면 게시 상태 변경을 위해 필요한 심사 규격은 무엇인가?

## 관련 문서
- [위키 인덱스](README.md)
