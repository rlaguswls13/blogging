# AI Blogging Project Wiki Index (Operations & Dev)

이 위키는 `ai-blogging` 프로젝트의 아키텍처 설계, 자동화 빌드 스크립트(`main.py`) 사용 가이드, Blogger API 연동 방법, 에이전트별 지침 가이드라인 등 **프로젝트 개발 및 운영 전반**을 관리하고 기록하는 개발팀 운영 위키입니다.

*(주제 작성 시 참고하는 기술 콘텐츠 지식 문서는 [content/wiki/](../content/wiki/) 디렉토리를 참조해 주세요.)*

## 주요 운영 문서 목록

- [세션 작업 기록](Session_History.md)
  - 개발 에이전트와 나눈 대화 세션 및 파일 수정/실행 이력이 종료 시점마다 자동으로 누적 기록되는 시스템 작업 로그입니다.
- [Google Blogger API 사용법](Google_Blogger_API_사용법.md)
  - 구글 블로거 API OAuth 2.0 흐름, 데스크톱 인증, 그리고 파이썬 포스팅 배포를 위한 연동 가이드입니다.
- [에이전트별 지침 및 아키텍처 가이드](Agent_Guidelines.md)
  - `agents/` 디렉토리에 정의된 각 포스팅 빌드 에이전트(Topic, Research, Writer, Fact-check, Editor 등)의 역할과 산출 파일, 그리고 작업 연계 흐름을 정리한 개발 위키입니다.

## 개발 스크립트 (`main.py`) 퀵 레퍼런스
- `python main.py new --topic "주제"` : 신규 기획 런(Run) 생성
- `python main.py validate --run <run_id> [--preflight]` : 빌드 상태 정합성 검증
- `python main.py approve --run <run_id>` : 배포 전 사람 최종 검토 승인
- `python main.py publish --run <run_id> [--platform blogger]` : 구글 블로거 배포 실행
