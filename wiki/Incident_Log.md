# Incident Log

이 문서는 `wiki/Blog_Writing_Rules.md`의 각 규칙이 왜 생겼는지 뒷받침하는 **사고/조사 기록 전문 보관소**입니다.
어떤 "필독" 목록에도 포함되지 않는 온디맨드 참고 문서이므로, 필요할 때만 아래 앵커를 따라 찾아보세요
(규칙 본문에서는 근거 한 줄 + 이 문서로의 링크만 유지합니다). 여기 담긴 문단은 원래
`Blog_Writing_Rules.md`에 있던 서술을 요약 없이 그대로 옮긴 것입니다.

---

## 2026-08-19 — fact-check rubber-stamp 1차 사례 {#factcheck-2026-08-19-1}

([`Blog_Writing_Rules.md` 12번 수칙](Blog_Writing_Rules.md)과 연결)

22개 run 중 19개가 100% verified인 상태에서 표본 재검증 결과, `mcp-2026-07-28-spec-stateless-a2a` 글의
CLAIM-005(A2A의 Linux Foundation 기증)가 공식 소스가 아닌 "업계 리포트 교차 확인"만으로 verified
판정되었고, 실제로 기증 연도가 틀렸음(글에는 2026년, 실제는 2025년 6월)이 확인되어 로컬·라이브 모두
수정함. 근거 열에 공식 문서명이 아니라 "업계 리포트"·"교차 확인" 같은 모호한 출처가 적혀 있으면 그
자체가 위험 신호이니 우선적으로 재검증할 것.

## 2026-08-19 — fact-check rubber-stamp 2차 사례 (17개 run 전수 표본 검증) {#factcheck-2026-08-19-2}

([`Blog_Writing_Rules.md` 12번 수칙](Blog_Writing_Rules.md)과 연결)

4개 fork로 병렬 재검증한 결과 5개 글에서 문제 확인. (1) `llm-agent-autogen-vs-langgraph.md`: 참고문헌의
arXiv:2401.12345가 실존하지만 완전히 무관한 논문(무선 신호처리)을 "멀티에이전트 LLM 서베이"로 둔갑시킨
인용 조작, MS Research 논문 링크도 404. (2) `kafka.md`/`4-activemq-kafka-rabbitmq-redis.md`/
`redis-distributed-lock-redlock-clock.md`/`saga-msa-choreography-vs-orchestration.md`:
`developer.confluent.io/patterns/...`, `cloud.google.com/solutions/...` 형태의 그럴듯하지만 실존하지
않는 URL이 총 9개 이상 발견(전부 404, WebFetch로 개별 확인). (3) Redis 락 글은 "Redlock 최소 5대"라는
사실 과장도 있었음(실제 알고리즘 최소치는 과반수 3대). **교훈**: `developer.confluent.io/patterns/...`나
`cloud.google.com/solutions/...`처럼 실제 서비스가 흔히 갖는 URL 패턴을 흉내낸 링크는 검증 없이는 특히
의심할 것 — 도메인이 진짜라고 해서 그 경로까지 진짜라는 보장은 없다. 참고문헌 URL은 발행 전 반드시
WebFetch/브라우저로 열어서 실제 로드되는지 확인해야 하며, `validate.py`의 "trusted domain" 체크는 도메인
신뢰도만 볼 뿐 URL 존재 여부는 검사하지 않는다는 한계가 있음(개선 검토 대상, 미착수).

## 2026-08-22 — Google 검색 "가치 없음" 판정 조사 및 차별화 규칙 도입 {#google-value-2026-08-22}

([`Blog_Writing_Rules.md` 14번 수칙](Blog_Writing_Rules.md)과 연결)

사용자가 Search Console 색인 상태에서 게시글이 "가치 없음"으로 판단되는 신호(크롤됨-현재 색인 생성되지
않음 계열)를 확인해 조사한 결과다. Google 공식 문서
[Creating Helpful, Reliable, People-First Content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)는
"단순 요약을 넘어서는 원본 정보·통찰·분석"을 요구하며, "많은 주제에 대해 광범위한 자동화로 콘텐츠를
생성"하거나 "다수의 작성자에게 대량 아웃소싱/생산"된 것처럼 보이는 콘텐츠를 검색엔진-우선
(search-engine-first) 콘텐츠의 대표 경고 신호로 명시한다.
[Spam Policies의 "Scaled content abuse"](https://developers.google.com/search/docs/essentials/spam-policies)
항목은 "AI 등으로 사용자 가치 추가 없이 대량 페이지 생성"을 스팸으로 규정하며, 개별 글이 아니라 **사이트
전체 패턴**으로 판단해 색인에서 배제될 수 있다고 명시한다.

**실사 발견 사항(2026-08-22)**: 당시 발행된 47개 글 전부가 SOLID/MVC/GoF 패턴(14개)/RDBMS/SQL 등 이미
공식문서·Baeldung·refactoring.guru 같은 최상위 권위 사이트가 포화 상태로 다루는 CS 101 주제였고,
"작성자의 견해" 섹션도 실제 프로덕션 수치·사건 같은 1인칭 경험 신호 없이 일반론적 재서술 수준이었다.

## 2026-08-22 — 백링크 라이브 미렌더링 버그 {#backlink-bug-2026-08-22}

([`Blog_Writing_Rules.md` 15번 수칙](Blog_Writing_Rules.md)과 연결)

`src/pipeline/converter.py`가 `## 백링크` 섹션을 라이브 HTML 변환 시 그냥 통째로 삭제하고 있었다 —
참고문헌은 별도 렌더링됐지만 백링크는 대응 렌더링이 없어, 에이전트가 넣은 내부링크가 실제로는 단 한 번도
라이브 페이지에 노출된 적이 없었다. Google은 내부링크가 없는 orphan page를 중요도 신호 부족으로 낮게
평가하므로 이는 14번 수칙의 "가치 없음" 문제와 직결되는 버그였다. 2026-08-22부터 `## 백링크`는 라이브
HTML에 "🔗 관련 글" 블록으로 실제 렌더링되도록 수정됨.

## 2026-08-22 — 세션 핸드오프/wiki 아카이브 관리 개편 {#doc-cleanup-2026-08-22}

사용자가 "관리 편의성과 토큰 절약을 위한 파이프라인 개편"을 요청해 진행. 발견한 문제 3가지:
(1) `.agent/session-handoff.md`의 Session log가 세션마다 한 줄 append 규칙을 어기고 여러 문장짜리
문단을 계속 추가해와 26KB까지 불어남 — `src/tools/archive_session_log.py` 신규 도입으로 최신 3건만
남기고 나머지를 `wiki/sessions/changelog.md`로 이동. (2) 필독 wiki 문서 8개(`Blog_Writing_Rules.md`,
`Blog_Post_Template.md`, `templates/article.md`, `theme/blogger_layout_thema_widget.md`,
`rules/blogger_rules.md`, `rules/blogger_platform_schema.md`, `rules/blog_article_pipeline_schema.md`,
`Google_Blogger_API_사용법.md`)가 전부 `## 관련 세션` 백링크로 최대 2.7MB짜리
`wiki/sessions/raw/2026-08-16.md`를 직접 가리키고 있었다(2026-08-17 `split_session_history.py` 1회성
마이그레이션의 부산물, 이후 아무도 열어본 적 없어 사고는 안 났지만 잠재적 토큰 폭탄). (3) `Blog_Writing_Rules.md`의
12/14/15번 규칙이 날짜 스탬프 찍힌 사고 서사를 규칙 본문에 그대로 인라인해 파일이 18KB까지 커졌음 —
본 `Incident_Log.md`를 신설해 전문을 이관하고 규칙 본문은 "무엇을/왜 한 줄/언제"로 압축.

(2)는 처음엔 8개 문서 전부를 `wiki/Session_Index.md`(19줄) 한 줄 링크로 단순화했으나, 사용자가
"백링크를 더 상세하게 만들고 이들의 lint를 자주 검사하면, raw 데이터는 유지하되 파일 단위가 아니라
파일명-줄 범위로 연결하면 입력 토큰이 현저히 줄어들 것"이라고 제안해 즉시 반영 — 파일 전체 대신
`build_session_backlink_index.py`(raw 아카이브를 `### 세션 기록` 블록 단위로 파싱해 태그별 줄 범위
인덱스 `wiki/sessions/raw-index.json` 생성) + `apply_session_backlinks.py`(문서 태그와 일치하는 최신
블록 최대 2개를 `경로/2026-08-16.md:1234-1567` 형식으로 삽입) + `lint_session_backlinks.py`(파일
존재·범위·블록 헤더 일치를 읽기 전용으로 검사, 깨지면 exit 1) 3종 도구로 구현. 결과적으로 백링크가
파일 전체(최대 2.7MB) 대신 실제 관련 블록만(대부분 16~120줄) 가리키게 되어, 이전 방식보다 더
구체적이면서도 훨씬 적은 토큰으로 필요한 슬라이스만 `Read(offset=, limit=)`로 읽을 수 있게 됨.
