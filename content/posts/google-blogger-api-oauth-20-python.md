---
id: "4097203026303819468"
title: "Google Blogger API 사용법: OAuth 2.0 연동과 Python을 통한 글 배포 자동화"
slug: "google-blogger-api-oauth-20-python"
status: "published"
url: "https://beji-tech.blogspot.com/2026/08/google-blogger-api-oauth-20-python.html"
publishedAt: "2026-08-05T03:37:28.782-07:00"
updatedAt: "2026-08-13T21:02:24.977-07:00"
tags: ["API-Integration","Blogger-API","Google-OAuth","Python"]
---

# Google Blogger API 사용법: OAuth 2.0 연동과 Python을 통한 글 배포 자동화

## Google Blogger API 사용법

## 요약

Google Blogger API v3는 개발자가 Python 등 프로그래밍 언어를 사용하여 블로그 포스트를 자동으로 생성, 수정, 삭제 및 관리할 수 있도록 지원하는 강력한 인터페이스입니다. 본 글에서는 Google Cloud Console을 활용한 OAuth 2.0 자격 증명 설정 방법, 로컬 인증 서버를 구축하여 브라우저 로그인 창으로 자격 증명을 획득���는 흐름(InstalledAppFlow), 그리고 획득한 토큰을 기반으로 Blogger API를 연동하여 포스트를 배포하는 전체 과정을 실전 코드와 함께 설명합니다.

목차

- [1. Google Blogger API 소개 및 준비 단계](#1-google-blogger-api-소개-및-준비-단계)

- [2. OAuth 2.0 프로토콜과 브라우저 기반 인증 처리](#2-oauth-20-프로토콜과-브라우저-기반-인증-처리)

- [3. Python을 이용한 Blogger API 연동 및 글 배포 코드 구현](#3-python을-이용한-blogger-api-연동-및-글-배포-코드-구현)

## 본문

### 1. Google Blogger API 소개 및 준비 단계

Google Blogger는 신속하고 쉽게 블로그를 생성하고 글을 게시할 수 있는 플랫폼입니다. Blogger API v3는 RESTful 형식의 API로, 대량의 글 작성이나 외부 플랫폼과의 동기화 자동화를 구현하는 데 필수적입니다 [1].

Blogger API를 사용하기 위해 가장 먼저 진행해야 할 작업은 Google Cloud Console 프로젝트 설정입니다.

- **Google Cloud Console 접속 및 프로젝트 생성**: Google 계정으로 로그인한 뒤 신규 프로젝트를 생성합니다.

- **Blogger API 활성화**: 'API 및 서비스 > 라이브러리' 메뉴에서 'Blogger API v3'를 검색하고 활성화합니다.

- **OAuth 동의 화면 설정**: 외부 사용자를 위한 동의 화면을 설정하고 필요한 스코프(`<https://www.googleapis.com/auth/blogger`>)를 추가합니다. 테스트 사용자에 본인의 Gmail 계정을 추가해 두어야 테스트 중 로그인 제한이 걸리지 않습니다 [2].

- **사용자 인증 정보 생성**: '사용자 인증 정보 만들기 > OAuth 클라이언트 ID'를 클릭하고 애플리케이션 유형을 '데스크톱 앱' 또는 '웹 애플리케이션'으로 지정하여 생성합니다. 생성 후 다운로드한 클라이언트 보안 비밀번호(Client ID 및 Client Secret)는 로컬 환경에 보관합니다.

### 2. OAuth 2.0 프로토콜과 브라우저 기반 인증 처리

Blogger API는 사용자의 민감한 데이터에 접근하므로 OAuth 2.0 인증 토큰(Access Token 및 Refresh Token)이 필수적입니다.
특히 로컬 스크립트나 데스크톱 환경에서는 `google-auth-oauthlib` 패키지의 `InstalledAppFlow`를 사용하는 것이 표준 권장사항입니다.

`InstalledAppFlow`는 다음과 같이 동작합니다:

- 애플리케이션이 로컬 HTTP 서버(예: `localhost:8080`)를 실행합니다.

- 기본 웹 브라우저를 자동으로 열어 Google OAuth 로그��� 동의 페이지로 리디렉션합니다 [2].

- 사용자가 브라우저에서 계정을 선택하고 권한을 부여하면, Google은 설정된 리디렉션 URI(`<http://localhost:8080/oauth2callback`>)로 인가 코드(Authorization Code)를 전송합니다.

- 로컬 HTTP 서버가 이 코드를 감지하고 구글 토큰 서버와 통신하여 `Access Token` 및 `Refresh Token`을 획득합니다.

오프라인 상태에서도 주기적인 글 작성을 하려면 `prompt='consent'` 및 `access_type='offline'` 매개변수를 지정해 리프레시 토큰을 강제로 만료하지 않고 계속해서 갱신하여 사용하는 구조를 구축하는 것이 중요합니다 [2].

### 3. Python을 이용한 Blogger API 연동 및 글 배포 코드 구현

Blogger API 연동의 핵심 라이브러리는 `google-api-python-client`입니다. 다음은 획득한 credentials 정보를 활용해 Blogger 서비스 객체를 만들고 글을 게시하는 예시 흐름입니다.

`from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 1. 획득한 토큰을 기반으로 Credentials 객체 생성
credentials = Credentials(
    token=access_token,
    refresh_token=refresh_token,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=client_id,
    client_secret=client_secret
)

# 2. Blogger API 서비스 빌드
blogger = build("blogger", "v3", credentials=credentials)

# 3. 배포할 글 내용 구성
body = {
    "title": "Blogger API를 통한 자동 배포 테스트",
    "content": "<p>이 글은 Python Blogger API v3를 활용해 자동으로 생성된 글입니다.</p>",
    "labels": ["API", "Python", "Blogger"]
}

# 4. 글 게시 API 호출
response = blogger.posts().insert(
    blogId="YOUR_BLOG_ID",
    isDraft=False,
    body=body
).execute()

print(f"글 배포 완료! ID: {response.get('id')}")
print(f"글 URL: {response.get('url')}")
`
Blogger API의 주요 리소스인 `posts()`는 글 생성을 위한 `insert`, 기존 글 수정을 위한 `update` 및 `patch`, 삭제를 위한 `delete` 메서드를 모두 안정적으로 지원합니다 [1].

## 작성자의 견해

> 

이 섹션은 사실 전달이 아니라 작성자의 해석과 견해를 담고 있습니다.

필자는 WordPress나 Medium에 비해 Blogger API가 구조적으로 단순하며 구글 클라우드 플랫폼의 견고한 IAM/OAuth 생태계 위에 구축되어 있어 강력한 보안성을 가지고 있다고 평가합니다. 특히 로컬 셸 스크립트나 GitHub Actions와 연동하여 마크다운 파일 빌드 후 정적 HTML로 변환하여 Blogger에 자동으로 주입하는 파이프라인을 매우 적은 라인 수로 개발할 수 있어 1인 기술 블로거의 운영 오버헤드를 낮추는 데 낮추는 데 탁월합니다. 다만 구글의 계정 승인 및 테스트 계정 등록 절차가 타 플랫폼의 단순 API Key 획득 모델에 비해 복잡한 것은 사실입니다.

## 한계와 반론

Blogger API 사용에도 몇 가지 분명한 한계가 존재합니다.

- **배포 제한(API Quota)**: Blogger API는 일일 호출량과 게시량에 제한(하루 최대 배포 수 제한 등)을 두고 있습니다. 대량의 스팸 글 생성을 막기 위한 구글의 정책이지만 대규모 포털 수준의 배포에는 맞지 않을 수 있습니다.

- **OAuth 동의 만료**: 구글 앱의 게시 상태가 '테스트(Testing)' 상태인 경우, 획득한 refresh token은 7일이 지나면 만료되므로 계속해서 브라우저 재인증을 해야 합니다. 이를 방지하려면 앱의 게시 상태를 '운영(Production)'으로 업그레이드해야 하는 추가 단계가 필요합니다.

## 종합적 의견

Google Blogger API v3는 소규모 블로그 운영 자동화를 원하는 개발자에게 적합한 검증된 기술입니다. 초기 OAuth 2.0 세팅 오버헤드만 극복한다면 API 구조의 높은 네이티브 완성도와 Google의 공식 파이썬 라이브러리 덕분에 안정적으로 블로깅 자동화 파이프라인을 운영할 수 있습니다.

  📚 참고문헌 (클릭하여 열기)
  
    

- Google Developers - Blogger API v3 Reference ([https://developers.google.com/blogger/docs/3.0/reference](https://developers.google.com/blogger/docs/3.0/reference))

- Google Identity Platform - OAuth 2.0 for Desktop Apps ([https://developers.google.com/identity/protocols/oauth2/native-app](https://developers.google.com/identity/protocols/oauth2/native-app))
