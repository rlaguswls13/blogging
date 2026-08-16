# Google Blogger API 사용법

구글 블로거(Blogger) API v3를 활용하여 이 저장소의 Python 파이프라인(`src/publishers/blogger.py`, `src/tools/auth.py`, `src/tools/get_blog_id.py`)이 실제로 어떻게 자동 게시를 처리하는지 정리한 가이드입니다. `token.json` 파일 기반이 **아니라 `.env` 환경변수 + Refresh Token 자동 갱신** 방식을 사용합니다.

## 1. 필요한 환경변수 (`.env`)

Google Cloud Console에서 **데스크톱 앱(Desktop App)** 타입 OAuth 2.0 클라이언트를 생성한 뒤, 프로젝트 루트 `.env`에 아래 값을 채웁니다.

| 변수 | 설명 | 획득 방법 |
| --- | --- | --- |
| `BLOGGER_CLIENT_ID` | OAuth 클라이언트 ID | Google Cloud Console |
| `BLOGGER_CLIENT_SECRET` | OAuth 클라이언트 시크릿 | Google Cloud Console |
| `BLOGGER_BLOG_ID` | 게시 대상 블로그 ID | `python src/tools/get_blog_id.py <블로그 URL>` |
| `BLOGGER_REFRESH_TOKEN` | 인증 갱신 토큰 | 최초 1회 `python src/tools/auth.py` 실행 시 자동 저장 |

`BLOGGER_CLIENT_ID`/`SECRET`/`BLOG_ID`는 게시 시 필수이며, `BLOGGER_REFRESH_TOKEN`이 없으면 대화형 브라우저 인증으로 폴백합니다(3절 참고).

## 2. 최초 인증: `src/tools/auth.py`

```bash
python src/tools/auth.py
```

동작 순서:
1. 로컬 `http://localhost:8080/oauth2callback`에 대기용 HTTP 서버를 띄웁니다.
2. 브라우저로 구글 OAuth 동의 화면(`scope=https://www.googleapis.com/auth/blogger`, `access_type=offline`, `prompt=consent`)을 자동으로 엽니다.
3. 사용자가 로그인/동의를 완료하면 로컬 서버가 `code`를 수신하고, `https://oauth2.googleapis.com/token`으로 교환해 `refresh_token`을 발급받습니다.
4. 발급된 `refresh_token`을 `.env`의 `BLOGGER_REFRESH_TOKEN=` 줄에 정규식으로 자동 치환(없으면 추가) 저장합니다.

> ⚠️ Google Cloud Console의 OAuth 클라이언트 "승인된 리디렉션 URI" 목록에 **`http://localhost:8080/oauth2callback`**을 미리 등록해 두어야 합니다.

`BLOGGER_BLOG_ID`를 아직 모른다면 먼저 조회합니다.

```bash
python src/tools/get_blog_id.py https://beji-tech.blogspot.com
```

## 3. 실제 게시 흐름 (`src/publishers/blogger.py::BloggerPublisher`)

`BloggerPublisher.publish()`는 `python main.py publish --run <runId> --platform blogger`를 통해 호출되며, 다음 순서로 동작합니다.

1. **기존 refresh_token 우선 시도**: `.env`의 `BLOGGER_REFRESH_TOKEN`으로 `google.oauth2.credentials.Credentials` 객체를 만들고 `googleapiclient.discovery.build("blogger", "v3", ...)`로 서비스 생성 → `posts().insert()`(신규) 또는 `posts().update()`(`existingPostId`가 있으면 수정) 호출.
2. **실패 시 대화형 브라우저 OAuth 폴백**: `auth.py`와 별도로 `publish()` 내부에 동일한 로컬 8080 포트 OAuth 루프가 내장되어 있어, refresh_token이 없거나 만료됐으면 자동으로 브라우저를 열어 재인증하고 새 refresh_token을 `.env`에 갱신합니다.
3. **응답 처리**: `postId`/`url`을 받아 `PublishResult`로 반환. 새로 발급된 refresh_token은 `update_env_file()`로 즉시 `.env`에 반영됩니다.
4. **`isDraft`**: `article.isDraft`(기본 `False`)로 초안/즉시 게시 여부 결정.

`--dry-run` 플래그를 주면 실제 API를 호출하지 않고 제목/태그/HTML 글자 수만 로그로 출력합니다.

```python
# src/publishers/blogger.py 핵심 로직 요약
body = {"title": article.title, "content": article.htmlContent, "labels": article.tags}
if article.existingPostId:
    posts.update(blogId=blog_id, postId=article.existingPostId, body=body).execute()
else:
    posts.insert(blogId=blog_id, isDraft=article.isDraft, body=body).execute()
```

전체 게시 파이프라인(`content/posts/`로의 자산 이관, `state.json` 갱신 등)은 [Agent_Guidelines.md](Agent_Guidelines.md)를 참고하세요.

## 4. 제한 및 모범 사례 (Best Practices)

- **일일 할당량**: Blogger API v3는 기본적으로 하루에 배포할 수 있는 포스팅 수 및 API 호출 수 제한(기본 100건 등)이 있습니다. 대량 배포가 필요한 경우 Google Cloud Console을 통해 할당량 증설을 별도 요청해야 합니다.
- **테스팅 상태**: OAuth 동의 화면의 게시 상태가 `Testing`인 경우, 지정된 테스트 사용자(최대 100명)만 로그인 및 API 이용이 가능하며 토큰이 주기적으로 만료됩니다. 운영 환경(Production)으로 전환하려면 앱 검증 과정을 통과해야 합니다.
- **refresh_token 회전**: 이 프로젝트는 매 게시 시도마다 새 refresh_token이 발급되면 `.env`를 자동으로 덮어씁니다. `.env`를 버전관리에 커밋하지 않도록 주의합니다.

## 5. 후속 연구 및 꼬리질문

- Blogger API의 포스팅 개수 증설을 요청하는 세부 절차와 조건은 무엇인가?
- OAuth 동의 화면 게시 상태 변경을 위해 필요한 심사 규격은 무엇인가?

## 관련 문서
- [위키 인덱스](README.md)
- [Agent Guidelines](Agent_Guidelines.md)
