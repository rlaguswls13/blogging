# Blogging Agent Harness

Markdown 계약으로 sub-agent를 통제하고, 조사·작성·사실 검증·견해·승인·게시를 파일 기반으로 추적하는 하네스입니다.

## 보안 경계

- Notion 쓰기는 로컬의 `.env.local`에 있는 `NOTION_WRITE_TOKEN`만 사용합니다.
- 배포 환경은 `NOTION_READ_TOKEN`만 사용해 승인된 글을 MDX로 변환합니다.
- 브라우저 번들에는 어떤 Notion 토큰도 포함하지 않습니다.
- `temp/runs`와 생성된 MDX는 기본적으로 Git에서 제외됩니다.

## 설치

```powershell
Set-Location D:\blogging
Copy-Item .env.example .env.local
npm install
```

## 기본 흐름

```powershell
# 새 실행 디렉터리 생성
npm run article:new -- --topic "AI 에이전트 하네스 설계"

# agents/*.md 계약에 따라 각 sub-agent가 산출물을 채운 뒤 사전 검사
npm run article:validate -- --run <run-id> --preflight

# 사람이 final.md와 fact-check.md를 검토한 뒤 승인
npm run article:approve -- --run <run-id>
npm run article:validate -- --run <run-id>

# 로컬에서만 Notion에 게시
npm run notion:publish -- --run <run-id> --dry-run
npm run notion:publish -- --run <run-id>

# 배포 빌드에서 Notion 페이지를 MDX로 생성
npm run content:sync
```

## 상태 흐름

`created → researched → drafted → fact_checked → approved → published`

`final.md`의 필수 섹션은 다음과 같습니다.

- 요약
- 본문
- 사실 검증 결과
- 작성자의 견해
- 한계와 반론
- 참고문헌

게시 게이트는 참고문헌 2개 이상, 고위험 미검증 주장 0개, 반박된 주장 0개, 사람의 승인 여부를 검사합니다.

## 에이전트 실행 연결

이 저장소는 LLM 공급자에 독립적인 하네스입니다. 사용하는 에이전트 런타임에서:

1. 해당 역할의 `agents/*.md`를 system/task 지침으로 읽습니다.
2. `temp/runs/<run-id>`만 작업 경로로 제공합니다.
3. 계약에 명시된 출력 파일만 쓰도록 제한합니다.
4. 작업 후 `article:validate`를 실행합니다.

에이전트 프로세스 자체의 파일 권한도 가능하면 OS 또는 컨테이너 수준에서 제한하십시오.

## Notion 데이터 소스

로컬 게시와 배포 동기화가 같은 글을 바라보도록 `NOTION_BLOG_PARENT_ID`와
`NOTION_BLOG_DATA_SOURCE_ID`에는 같은 데이터 소스 ID를 지정합니다.

데이터 소스에는 기본적으로 다음 속성이 필요합니다.

- `Name`: 제목 속성
- `Status`: 상태 속성
- `Status`에 `Published` 옵션

이름이 다르면 `.env.local`의 `NOTION_TITLE_PROPERTY`,
`NOTION_STATUS_PROPERTY`, `NOTION_PUBLISHED_STATUS`를 변경합니다.

`article:approve`는 사람의 검토를 대체하지 않습니다. 사람이 검토를 끝낸 후
승인 사실을 상태 파일에 기록하는 명령입니다.
