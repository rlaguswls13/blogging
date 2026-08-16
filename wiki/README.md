# AI Blogging System 프로젝트 위키 (RAG Knowledge Wiki)

본 위키 디렉터리(`wiki/`)는 AI Agent 및 개발자가 본 프로젝트(`ai-blogging`)를 운용, 개발, 포스팅 작성 시 **RAG(Retrieval-Augmented Generation) 지식으로 최우선 탐색하고 필히 참고하는 프로젝트 전용 기술 위키**입니다.

---

## 🌟 [AI Agent 필독] 룰 & 템플릿 & 주제 백로그 위키 노드

AI Agent는 글을 작성하거나 주제를 추천할 때 아래 RAG 지식 노드를 최우선으로 필히 참조해야 합니다:

1. 📌 **[`Post_Topic_Backlog.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Post_Topic_Backlog.md)**: **[기초 5개 & 심화 5개 포스팅 추천 주제 백로그]**
2. 📂 **[`wiki/rules/`](file:///d:/coding-project/2026-project/ai-blogging/wiki/rules/)**:
   - [`blogger_rules.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/rules/blogger_rules.md): 단일 진실 출처 블로그 파이프라인 통합 규칙
   - [`blogger_platform_schema.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/rules/blogger_platform_schema.md): 영역 1 Blogger 배포 & 테마 확장 스키마
   - [`blog_article_pipeline_schema.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/rules/blog_article_pipeline_schema.md): 영역 2 Blog 글 작성 & 파이프라인 스키마
3. 📂 **[`wiki/templates/`](file:///d:/coding-project/2026-project/ai-blogging/wiki/templates/)**:
   - [`article.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/templates/article.md): 마크다운 글 생성 표준 구분 템플릿
4. 📄 **[`Blog_Writing_Rules.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Blog_Writing_Rules.md)**: AI Agent 필독 수칙
5. 📄 **[`Blog_Post_Template.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Blog_Post_Template.md)**: AI Agent 필독 마크다운 템플릿 양식

---

## 📚 주요 개발/운용 위키 목록

- [`Google_Blogger_API_사용법.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Google_Blogger_API_%EC%82%AC%EC%9A%A9%EB%B2%95.md): 구글 Blogger API 인증 및 퍼블리싱 가이드
- [`Agent_Guidelines.md`](file:///d:/coding-project/2026-project/ai-blogging/wiki/Agent_Guidelines.md): AI Agent 지식 활용 및 RAG 검토 지침

---

## 🛡️ 파이프라인 5대 핵심 수칙

1. **일회성 스크립트 작성 전면 금지** (`python main.py` 정식 오케스트레이터 100% 필수)
2. **6단계 포스팅 라이프사이클 100% 이행**:
   `created → researched → drafted → fact_checked → 🛑[관리자 명시적 승인] → approved → published`
3. **`temp/runs/${run_id}/final.md` 100% 필수 보관 및 로컬 검증 원본 관리**
4. **관리자 명시적 승인 필수 (Human Approval Gate)**: `fact_checked` 완료 후 절대 자동 배포하지 않으며 관리자의 승인 지시 시 배포 진행
5. **최종 승인 글 자동 이관**: 배포 성공 시 `final.md` 내부 검증 메모 자동 Sanitization 제거 후 `content/posts/${slug}.md`로 자동 이관 보관


## 세션 기록
- [세션 작업 기록 인덱스](Session_Index.md)
  - 날짜별로 분리 저장되는 세션 원본 아카이브(`sessions/raw/`)의 인덱스입니다. 큐레이션된 최신 작업 상태는 `.agent/session-handoff.md`를 참고하세요.
