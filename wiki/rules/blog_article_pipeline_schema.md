# [Blog 글 작성 & 파이프라인 스키마] (Blog Article Pipeline Schema)

> 이 문서는 [`AGENTS.md`](../../AGENTS.md) §1·§3이 참조하는 Blog 글 작성 영역 SSOT입니다.

이 문서 본문은 **실행 순서를 그대로 코드에서 역산한 시퀀스(액션) 스키마**입니다(2026-08-22 개편 —
이전엔 산문형 "5대 구성 요소" 설명이었으나, 사용자 요청으로 "사용자 지시든 스크립트든 md 규칙이든
전부 하나의 파일에 액션 시퀀스로" 재작성). 각 스텝은 `enforced_by`로 코드 강제(`code:`)와 문서/관례
강제(`convention:`, 자동 검증 없음 — 사람이 지켜야 함)를 구분합니다. 수정 지시를 내릴 땐 `id`로
콕 집어 말하면 됩니다(예: "`validate` 스텝의 `min_words.본문`을 900으로 바꿔줘").

이 YAML은 아래 소스 코드/설정 파일에서 직접 도출했고, 필드명·값은 그 파일들과 항상 일치해야 합니다
(스키마가 코드와 어긋나면 이 문서가 아니라 스키마 쪽을 코드에 맞게 고칠 것):
`main.py`, `src/pipeline/new_run.py`, `src/pipeline/validate.py`, `src/pipeline/approve.py`,
`src/pipeline/converter.py`, `src/publishers/__init__.py`, `src/publishers/blogger.py`,
`src/core/types.py`, `src/core/publish_gate.json`, `wiki/templates/article.md`.

```yaml
pipeline: blog-article-lifecycle
version: 2026-08-22
entrypoint: "python main.py <command> [options]"

state_machine:  # src/core/types.py::WorkflowStatus
  states: [created, researched, drafted, fact_checked, approved, published]
  note: >
    researched/drafted/fact_checked는 별도 파일로 강제되지 않는 내부 절차 상태다(문서상 라벨일 뿐,
    코드가 검사하지 않음) — 실제 코드가 다루는 상태 전이는 created → approved → published뿐이다.

phases:  # 2026-08-22 추가 — 사용자가 정의한 상위 모델: 작성-검사-휴먼검증-lint-배포.
  # steps.*와의 매핑 + 현재 코드가 실제로 이 모델과 어긋나는 지점을 정직하게 표시한다.
  write:
    maps_to_steps: [topic_selection, new_run, draft]
    note: "element_matrix의 각 요소를 작성"
  check:
    maps_to_steps: [draft, validate]
    note: >
      의미/품질 검증(요소가 '적절한지'). element_matrix에서 automated=false인 항목은 아직 자동화가
      없어 작성자(에이전트) 자신의 판단에 의존한다 — wiki/Blog_Writing_Rules.md 13번 수칙이 이미
      "자동 게이트로 완전히 검출 어려움"이라고 명시한 부분과 같은 얘기다. automated=true인 항목만
      validate 스텝이 실제로 체크한다.
  human_verify:
    maps_to_steps: [human_review, approve]
    note: "🛑 필수 관문, 자동화 대상 아님"
  lint:
    maps_to_steps: [publish.gate_revalidation]
    note: >
      구조/기계적 검증(요소가 '존재/형식이 맞는지'). 현재 코드는 check와 lint를 같은 validate_run()
      하나로 처리한다(코드상 분리 안 돼 있음) — publish 스텝이 발행 직전 이걸 다시 호출해 최종
      안전망 역할을 한다. 사용자가 요청한 "작성-검사-lint 사이 1:1:1"을 코드 레벨에서 물리적으로
      분리하려면 validate.py를 check_run()/lint_run() 두 함수로 쪼개야 하는데, 이번 라운드는
      스키마/보고서 재구성까지만 범위(사용자 확인, 2026-08-22).
  deploy:
    maps_to_steps: [platform_choice, publish, convert_html, publish_blogger, archive_and_transfer]

element_matrix:  # 2026-08-22 추가 — 작성 요소별 write→check→lint 1:1:1 매핑(사용자 요청)
  - element: 토픽(topic)
    written_in: topic_selection
    check: {rule: "동일/유사 토픽이 이미 발행된 글과 겹치지 않는지", automated: true, aid: "src/tools/check_topic_duplication.py", note: "2026-08-23 신설 — 태그/제목 키워드 겹침(Dice 계수)으로 유사도 채점. 임계값 이상이면 경고만 하지 않고 wiki/Blog_Writing_Rules.md 14번 수칙의 차별화 각도들을 원 주제와 결합한 대안을 자동 생성해 다시 채점, 실제로 임계값 아래로 내려간 것만 제시(사용자 요청 반영). 표면적 키워드 유사도라 다른 표현으로 같은 개념을 다루는 경우까지는 못 잡음."}
    lint: {rule: "차별화 포인트 섹션 존재 + 최소 40단어", check_id: [required_sections, section_min_words], automated: true}
  - element: 이미지(image)
    written_in: draft (본문)
    check: {rule: "이미지가 내용과 실제로 맞고 화질/저작권 문제 없는지", automated: false, note: "2026-08-23 재확인 — 비전 모델 API가 파이프라인에 없어 코드 자동화 보류 결정(비용/복잡도 대비 실익 낮음). 대신 wiki/Blog_Writing_Rules.md 16번 수칙으로 '에이전트가 Read 툴로 직접 이미지를 열어보고 확인'을 명시적 필수 단계로 문서화."}
    lint: {rule: "코드 또는 이미지 최소 1개 존재", check_id: code_or_image_presence, automated: true, note: "존재 여부만 봄, '알맞은지'는 안 봄"}
  - element: 코드(code)
    written_in: draft (본문)
    check: {rule: "코드가 실제로 동작하고 설명과 일치하는지", automated: true, aid: "src/tools/check_code_blocks.py", note: "2026-08-23 신설 — python/bash/json은 실제 파서로 구문 검사(compile()/bash -n/json.loads(), 실행은 안 함=부작용 없음). '설명과 일치하는지'는 코드펜스 직전 문단의 백틱 인용 식별자가 실제 코드 안에 등장하는지 교차 확인(사용자 요청으로 추가) — 식별자가 맞아도 로직 자체가 다를 수 있어 완전하지 않음, 그 외 언어(Go/SQL 등)는 구문 검사기 없음."}
    lint: {rule: "코드 또는 이미지 최소 1개 존재", check_id: code_or_image_presence, automated: true, note: "'잘 작성됐는지'는 안 봄, 존재만"}
  - element: 공식문서 참고(reference)
    written_in: draft (참고문헌)
    check: {rule: "Tier1/2 신뢰 도메인 최소 1개 포함", check_id: reference_credibility_tier, automated: true, aid: "src/tools/check_reference_domains.py"}
    lint: {rule: "URL이 실제로 접속되는지(HEAD/GET)", check_id: reference_link_liveness, automated: true, note: "--skip-link-check로 생략 가능"}
  - element: 백링크(backlink)
    written_in: draft (백링크)
    check: {rule: "연결한 글이 주제와 실제로 관련 있는지", automated: true, aid: "src/tools/check_backlink_relevance.py", note: "2026-08-23 신설 — suggest_internal_links.py와 동일한 태그 겹침*2 + 제목 키워드 스코어링을 거꾸로 적용해, 이미 써놓은 백링크의 관련성을 점수 매김(순수 텍스트 유사도는 긴 제목끼리 구조적으로 낮게 나와 오탐이 많아 태그 중심으로 조정)."}
    lint: {rule: "자사 블로그 내부링크 개수 >= minimumInternalLinks(2)", check_id: internal_link_count, automated: true, aid: "src/tools/suggest_internal_links.py"}
  - element: 의견/차별화(opinion, differentiation)
    written_in: "draft (작성자의 견해, 차별화 포인트, 종합적 의견)"
    check: {rule: "실제로 통찰 있는 내용인지, 할루시네이션/패딩 없는지", automated: true, aid: "src/tools/check_opinion_insight.py", note: "2026-08-23 신설 — '통찰이 있는가' 자체는 여전히 판단 불가(human_verify가 실질 방어선, wiki/Blog_Writing_Rules.md 13번 수칙). 대신 서로 다른 실패 유형을 구분한 5개 하위 지표(사용자 요청으로 단일 점수 대신 세분화): (1)구체성-숫자/URL/버전/기술식별자 개수, (2)상투구 비율, (3)타 글과의 bigram 유사도(재탕 탐지), (4)차별화 포인트가 주장한 유형(벤치마크/장애/비교표/직접실행/예상밖)이 본문에서 실제로 뒷받침되는지 교차 확인, (5)어휘 다양성(TTR)."}
    lint: {rule: "인용구(>) + 의견 키워드 존재, 최소 분량", check_id: [opinion_disclaimer, section_min_words], automated: true, note: "형식/분량만 봄, 통찰 여부는 안 봄"}
  - element: 사실검증(fact-check)
    written_in: draft (사실 검증 결과)
    check: {rule: "실제 원문 대조로 판정했는지(rubber-stamp 아닌지)", automated: "partial", note: "wiki/Blog_Writing_Rules.md 12번 수칙 — '실제로 원문을 봤는지' 자체는 여전히 판단 불가하고 python src/tools/report_fact_check_stats.py 사후 표본 감사만 가능. 다만 2026-08-23부터 근거 열의 모호한 표현 패턴(vague_evidence check_id, 아래 lint 참고)은 실시간 차단됨 — wiki/Incident_Log.md#factcheck-2026-08-19-1/-2에 실제 등장한 '업계 리포트'/'교차 확인'(구체적 출처 없이) 같은 표현을 잡는다."}
    lint: {rule: "unverified/contradicted 없음 + 모든 판정에 근거 열 존재 + 근거가 모호한 표현만은 아님", check_id: [fact_check_verdicts, unsupported_claims, vague_evidence], automated: true}
  - element: 구조(frontmatter, 섹션)
    written_in: draft 전체
    check: {rule: "(구조는 판단 요소가 아니라 형식 요소 — check 단계 없음)", automated: null}
    lint: {rule: "frontmatter 스키마 + 9개 필수 섹션 + 인코딩 손상 없음", check_id: [frontmatter, required_sections, min_references, encoding_corruption], automated: true}
  - element: "SEO 메타 description (2026-08-22 신설)"
    written_in: "draft (## 요약 섹션 — 별도 필드 없음)"
    check: {rule: "요약 도입부가 검색 스니펫으로 쓰기에 자연스러운지(문장이 어색하게 안 잘리는지, 상투구로 시작 안 하는지)", automated: true, note: "src/pipeline/seo_check.py — validate_run() 8개 게이트와 물리적으로 분리된 독립 모듈. 통과 실패해도 발행 자체는 막지 않음(정보/경고 수준)."}
    lint: {rule: "(없음 — validate_run()의 필수 섹션 존재 여부와 무관하게 요약 섹션 콘텐츠 품질만 봄)", automated: null}
    background: >
      Blogger API v3 Posts 리소스는 글별 검색 설명 필드를 제공하지 않는다(2026-08-22 확인,
      developers.google.com/blogger/docs/3.0/reference/posts + Blogger 공식 커뮤니티 답변
      support.google.com/blogger/thread/343506660, 2025-05 — "customMetadata는 Blogger가
      쓰지 않아 문서에서 제거했다, 편집기에서 수동 입력하는 수밖에 없다"). content/theme/
      blogger_site_theme.xml에서 data:post.body를 <head>의 snippet()으로 잘라 자동 채우려는
      시도도 2026-08-23에 실패로 확인됐다 — data:post.*는 Blog 위젯의 글 목록 루프 밖(=<head>)
      에서는 항상 비어 있어 결과가 빈 문자열이 된다(라이브에서 <meta content=''/> 직접 확인).
      결론: <meta name="description">를 글마다 채우는 프로그래밍적 방법은 API로도 테마로도
      없다 — Blogger 글 편집기의 "검색 설명" 칸에 사람이 직접 입력하거나(수동), 그 입력창을
      브라우저 자동화로 대신 채우는 것(미착수, 논의 중) 둘 중 하나뿐이다. seo_check.py는 대신
      "구글이 크롤링 시 본문에서 자동으로 뽑아갈 가능성이 높은 '## 요약' 첫 문장이 검색 노출용
      으로 자연스러운지"를 점검하는 용도로 재해석해서 유지한다.
    cli: "python main.py validate --run <run_id> --seo  (또는 python src/pipeline/seo_check.py --run <run_id> 단독 실행)"

steps:
  - id: topic_selection
    order: 1
    name: 주제 선정
    trigger: 사용자 지시("주제 추천해줘"/특정 주제 지정) 또는 에이전트가 백로그에서 선택
    actor: human_or_agent
    enforced_by: "convention: wiki/Blog_Writing_Rules.md#14, #17, #18, wiki/Post_Topic_Backlog.md"
    inputs: [wiki/Post_Topic_Backlog.md]
    action: >
      미발행(🟡) 백로그 항목을 고르거나, "트렌드" 요청이면 매번 WebSearch로 최근 1~2개월 이슈를 새로
      조사한다. 2026-08-22부터 "이 글이 상위 검색결과 대비 무엇을 더하는지"(차별화 각도) 없이는
      신규 채택을 지양한다(규칙 14, 배경: `wiki/Incident_Log.md#google-value-2026-08-22`).
      기존 시리즈(GoF/NoSQL/RDBMS 등)의 다음 편이거나 새 시리즈의 1편이면, frontmatter tags에
      `{시리즈명}_Series` 태그를 반드시 포함한다(규칙 17) — 이 태그가 있어야 아래 중복 검사의
      임계값 완화(규칙 18, SERIES_THRESHOLD)가 정확히 적용된다.
    outputs: {topic: string, differentiation_angle: string, series_tag: "string | null"}
    authoring_aids:  # 2026-08-23 신설
      - {cmd: "src/tools/check_topic_duplication.py --topic \"...\" [--tags \"...,{시리즈명}_Series\"]", purpose: "기존 발행 글과의 유사도 채점 + 임계값 이상이면 차별화 각도를 결합한 대안 주제를 자동 생성해 재검증. --tags에 _Series 태그를 넣으면 같은 시리즈 내 정상적 유사도를 오탐으로 잡지 않음(규칙 18)"}
      - {cmd: "src/tools/manage_series_tags.py --scan", purpose: "전체 발행 글을 다시 스캔해 시리즈 소속인데 _Series 태그가 빠진 글이 없는지 점검(소급 감사용)"}
    checks: []  # 여전히 강제 게이트는 아님(주제 선정은 사람/에이전트 판단) — 위 도구는 권고용 aid
    next: new_run

  - id: new_run
    order: 2
    name: 실행 디렉토리 생성
    trigger: "python main.py new --topic \"<topic>\""
    actor: agent
    enforced_by: "code: src/pipeline/new_run.py::create_run()"
    inputs: {topic: string}
    action: >
      run_id = UTC 타임스탬프(YYYYMMDDHHMMSS, src/pipeline/new_run.py::make_run_id). temp/runs/<run_id>/
      생성 → state.json(RunState: status=created, humanApproved=false) 기록 → request.md(주제+생성시각)
      기록 → wiki/templates/article.md를 렌더링({{articleId}}/{{title}}/{{slug}}/{{createdAt}} 치환)해
      article-template.md로 저장.
    outputs:
      - "temp/runs/<run_id>/state.json"
      - "temp/runs/<run_id>/request.md"
      - "temp/runs/<run_id>/article-template.md"
    checks: []
    next: draft

  - id: draft
    order: 3
    name: final.md 직접 작성
    trigger: 시스템이 만들지 않음 — 글쓰기 에이전트가 article-template.md를 뼈대로 직접 작성
    actor: agent
    enforced_by: "convention: wiki/Blog_Writing_Rules.md 전체, wiki/templates/article.md 인라인 주석"
    inputs: ["temp/runs/<run_id>/article-template.md"]
    action: >
      리서치·초안·팩트체크는 전부 이 단계의 내부 절차일 뿐 별도 파일로 강제되지 않는다
      (wiki/Agent_Guidelines.md §1). 9개 `##` 섹션을 채운다: 요약, 차별화 포인트, 본문,
      사실 검증 결과, 작성자의 견해, 한계와 반론, 참고문헌, 종합적 의견, 꼬리질문
      (+ 관례상 백링크). 최신 공식 문서 우선 확인(규칙 9), 참고문헌 신뢰도 등급(규칙 10),
      사실 검증은 원문 대조로(규칙 12, rubber-stamp 금지), 분량은 하한선일 뿐 질이 우선(규칙 13).
    outputs: ["temp/runs/<run_id>/final.md"]
    authoring_aids:  # 2026-08-22 신설 — validate 단계에서야 실패를 발견하는 왕복을 줄이기 위한 작성 보조 도구
      - {cmd: "src/tools/suggest_internal_links.py --tags <tags> [--topic \"...\"]", satisfies_check: internal_link_count, purpose: "content/posts/*.md frontmatter에서 태그/키워드 겹치는 기존 글을 점수순으로 추천, ## 백링크에 바로 붙여넣기 가능한 마크다운 링크로 출력"}
      - {cmd: "src/tools/check_reference_domains.py <url1> [url2] ...", satisfies_check: reference_credibility_tier, purpose: "후보 참고문헌 URL을 validate.py의 TRUSTED_REFERENCE_DOMAINS와 즉석 대조(같은 목록 재사용, 복제 아님)"}
      - {cmd: "python src/pipeline/seo_check.py --run <run_id>", satisfies_check: "(신규, validate_run() 8개 게이트와 분리된 독립 점검)", purpose: "라이브 배포 시 <meta name=\"description\">으로 쓰일 '## 요약' 첫 160자 미리보기 + 문장이 어색하게 안 잘리는지 경고"}
      - {cmd: "src/tools/check_backlink_relevance.py --run <run_id>", satisfies_check: "element_matrix.백링크.check (신규)", purpose: "이미 써놓은 '## 백링크' 각 링크가 이 글과 태그 기준으로 실제 관련 있는지 점수화, 관련성 낮은 링크 경고"}
      - {cmd: "src/tools/check_code_blocks.py --run <run_id>", satisfies_check: "element_matrix.코드.check (신규)", purpose: "코드펜스 구문 검사(python/bash/json) + 코드펜스 직전 문단이 언급한 식별자가 실제 코드에 있는지 교차 확인"}
      - {cmd: "src/tools/check_opinion_insight.py --run <run_id>", satisfies_check: "element_matrix.의견/차별화.check (신규)", purpose: "차별화 포인트/작성자의 견해/종합적 의견 3개 섹션에 대해 구체성/상투구 비율/타 글과의 유사도/주장-근거 정합성/어휘 다양성 5개 하위 지표 리포트"}
    checks:
      - id: required_sections
        rule: "9개 섹션 헤딩 모두 존재"
        enforced_by: "convention (validate 스텝에서 사후 검증)"
    next: validate

  - id: validate
    order: 4
    name: 게시 게이트 검증
    trigger: "python main.py validate --run <run_id> [--preflight] [--skip-link-check]"
    actor: agent
    enforced_by: "code: src/pipeline/validate.py::validate_run(), config: src/core/publish_gate.json"
    inputs: ["temp/runs/<run_id>/final.md", src/core/publish_gate.json]
    action: >
      --preflight면 사람 승인 체크를 건너뛴다(초안 사전 점검용). --skip-link-check면 참고문헌 URL
      생존 확인(네트워크 호출)을 생략한다. 아래 checks를 순서대로 실행하고 오류 1건이라도 있으면
      exit 1(경고는 통과, 출력만 됨).
    checks:
      - id: frontmatter
        rule: "ArticleFrontmatter 스키마 검증 (id/title/slug/status/tags/factCheckScore)"
        severity: error
        code_ref: "src/core/types.py::ArticleFrontmatter, slug는 ^[a-z0-9]+(?:-[a-z0-9]+)*$"
      - id: required_sections
        rule: "publish_gate.json.requiredSections 9개 전부 '## ' 헤딩으로 존재"
        severity: error
        value: [요약, 차별화 포인트, 본문, 사실 검증 결과, 작성자의 견해, 한계와 반론, 참고문헌, 종합적 의견, 꼬리질문]
      - id: min_references
        rule: "## 참고문헌 리스트 항목 개수 >= minimumReferences"
        severity: error
        value: 2
      - id: reference_link_liveness
        rule: "참고문헌 각 항목의 http(s) URL이 실제 접속 가능(HEAD, 실패 시 GET, UA 지정)"
        severity: "error (allowBrokenLinks=false면 error, true면 warning) — --skip-link-check로 생략 가능"
        value: {allowBrokenLinks: false}
      - id: reference_credibility_tier
        rule: "참고문헌 URL 중 TRUSTED_REFERENCE_DOMAINS와 하나도 안 겹치면 오류"
        severity: error
        note: "2026-08-22 승격 — warning으로 두면 무시되고 넘어가는 사례가 반복돼 사용자 요청으로 error화. draft 단계에서 src/tools/check_reference_domains.py로 미리 확인 가능(steps.draft.authoring_aids)"
        code_ref: "src/pipeline/validate.py::TRUSTED_REFERENCE_DOMAINS (arxiv.org, docs.oracle.com, spring.io, kubernetes.io, kafka.apache.org, redis.io, cncf.io, linuxfoundation.org, developer.mozilla.org, learn.microsoft.com, cloud.google.com, docs.aws.amazon.com, man7.org, kernel.org, openjdk.org, docs.python.org, modelcontextprotocol.io, rfc-editor.org, ietf.org, grpc.io, protobuf.dev, projectreactor.io, docs.confluent.io, cassandra.apache.org, go.dev, github.com, dev.mysql.com, postgresql.org 등 — 2026-08-22 error 승격과 함께 누락분 보강 완료. 새 주제가 이 목록에 없는 공식 도메인을 인용해야 하면 이 목록에 먼저 추가할 것)"
      - id: section_min_words
        rule: "섹션별 최소 단어수(한글 글자수 + 영숫자 단어수 합산) 미달 시 오류"
        severity: error
        value: {차별화 포인트: 40, 본문: 800, 작성자의 견해: 100, 한계와 반론: 80, 종합적 의견: 100}
      - id: code_or_image_presence
        rule: "코드펜스와 이미지가 둘 다 0개면 오류"
        severity: error
        note: "2026-08-22 승격 (warning -> error)"
      - id: opinion_disclaimer
        rule: "'작성자의 견해'·'종합적 의견' 각각에 '>' 인용구 + (의견|견해|해석|사견) 키워드 존재"
        severity: error
        note: "2026-08-22 완화 — 예전엔 리터럴 문장 1개를 정확히 요구해 47개 글이 동일 문구를 반복하던 문제 수정"
      - id: encoding_corruption
        rule: "본문에 U+FFFD(�) 포함 시 오류"
        severity: error
      - id: fact_check_verdicts
        rule: "'사실 검증 결과' 표에 unverified 또는 contradicted 판정이 하나라도 있으면 오류"
        severity: error
      - id: unsupported_claims
        rule: "판정은 있는데 근거 열이 빈 claim이 있으면 오류 (할루시네이션 신호)"
        severity: error
        note: "2026-08-22 승격 (warning -> error)"
      - id: vague_evidence
        rule: "근거 열이 모호한 표현(업계 리포트/일반적으로 알려진/교차 확인 단독 등)만 있고 구체적 출처 표지(URL/RFC 번호/공식 문서/도메인)가 전혀 없으면 오류"
        severity: error
        note: "2026-08-23 신설 — wiki/Incident_Log.md#factcheck-2026-08-19-1/-2 실제 사고(업계 리포트 교차 확인만으로 verified 처리했다가 사실관계 오류 발견) 재발 방지. element_matrix.사실검증.check 보완."
        code_ref: "src/pipeline/validate.py의 vague_pattern/specific_marker_pattern"
      - id: internal_link_count
        rule: "본문+백링크+종합적 의견 합산, beji-tech.blogspot.com 링크 개수 < minimumInternalLinks면 오류"
        severity: error
        value: {minimumInternalLinks: 2}
        note: "2026-08-22 신설 및 승격(warning -> error) — 배경: wiki/Incident_Log.md#backlink-bug-2026-08-22. draft 단계에서 src/tools/suggest_internal_links.py로 후보 추천 가능(steps.draft.authoring_aids)"
      - id: human_approval
        rule: "--preflight 없이 실행 시 state.json.humanApproved == true 여야 함"
        severity: error
    outputs: {ok: bool, errors: list, warnings: list}
    on_fail: "final.md 수정 후 재실행 — 컨펌된 본문은 절대 임의 축약/재작성 금지, 게이트 로직 쪽을 고치는 게 원칙"
    next: human_review

  - id: human_review
    order: 5
    name: "🛑 관리자 검토 및 명시적 승인"
    trigger: "에이전트가 final.md 또는 리뷰 artifact를 사용자에게 제시"
    actor: human
    enforced_by: "convention: wiki/rules/blogger_rules.md §1, AGENTS.md §2 (자동화 불가 지점)"
    inputs: ["temp/runs/<run_id>/final.md (validate 통과 상태)"]
    action: >
      관리자가 본문(코드/다이어그램/수치 포함)을 검토한다. 승인 전 컨펌 본문은 AI가 임의로 축약·수정·
      삭제·재작성 절대 금지 — 검증 오류는 본문이 아니라 src/ 소스나 게이트 스키마를 고쳐서 해결.
      **배치 단위 사전 승인("발행해")은 개별 초안 검토를 대체하지 않는다** — fork/서브에이전트에게
      "이미 승인됐다"는 근거로 approve+publish까지 위임 금지, `validate --preflight`까지만 시키고
      부모가 직접 검토·승인·발행할 것.
    outputs: {approved: bool}
    checks: []
    next: approve

  - id: approve
    order: 6
    name: 승인 기록
    trigger: "python main.py approve --run <run_id>"
    actor: agent
    enforced_by: "code: src/pipeline/approve.py::approve_run()"
    inputs: ["temp/runs/<run_id>/state.json"]
    action: >
      status가 이미 published면 ValueError로 거부. 아니면 state.status = approved,
      state.humanApproved = true 로 갱신.
    outputs: ["temp/runs/<run_id>/state.json (humanApproved=true)"]
    checks:
      - id: not_already_published
        rule: "state.status != published"
        severity: error
    next: platform_choice

  - id: platform_choice
    order: 7
    name: 배포 플랫폼 재질의
    trigger: "'승인/배포/post로 옮겨라' 지시를 받아도 반드시 재질의"
    actor: human
    enforced_by: "convention: wiki/rules/blogger_rules.md §1 (Human Approval Unalterable & Platform Choice)"
    inputs: []
    action: "Blogger(실서버 자동 퍼블리싱) / Naver / Manual(수동 이관만) 중 관리자에게 다시 확인 후 진행"
    outputs: {platform: "blogger|notion (기본 blogger)"}
    checks: []
    next: publish

  - id: publish
    order: 8
    name: 멀티 플랫폼 게시
    trigger: "python main.py publish --run <run_id> [--platform blogger,notion] [--dry-run]"
    actor: agent
    enforced_by: "code: src/publishers/__init__.py::publish_to_multi()"
    inputs: ["temp/runs/<run_id>/final.md", "temp/runs/<run_id>/state.json"]
    action: |
      1. validate_run() 재실행(게이트 우회 불가) — 실패 시 즉시 중단, 경고는 출력만.
      2. dry-run 아니면 ensure_images_pushed(): content/images/ 미반영 변경을 git add·commit·push
         (실패 시 예외로 발행 자체 차단, src/publishers/__init__.py::ensure_images_pushed).
      3. final.md 로드 → published_content = 본문에서 '## 꼬리질문' 제거 + raw URL 자동 링크화
         (코드블록 제외, linkify_markdown).
      4. convert_markdown_to_html() 호출 → src/pipeline/converter.py (다음 스텝에 상세).
      5. 플랫폼별(blogger 우선 정렬) BlogPublisher.publish() 호출 — 아래 publish_blogger 참고.
      6. dry-run이면 여기서 종료(상태 미변경). 아니면 tail_questions/references/toc 파싱,
         state.status=published, state.publishedPlatforms 갱신, publish-result.json 기록.
      7. content/posts/<Category>/<slug>.md로 최종 이관(archive_and_transfer 스텝 참고, Category는 tags 기준 Basics/Advanced/ETC).
    outputs:
      - "라이브 게시물(Blogger 등)"
      - "temp/runs/<run_id>/state.json (status=published)"
      - "temp/runs/<run_id>/publish-result.json"
    checks:
      - id: gate_revalidation
        rule: "publish도 validate_run()을 내부에서 다시 호출 — CLI에서 validate를 생략해도 우회 불가"
        severity: error
    next: convert_html

  - id: convert_html
    order: 8.1
    name: 마크다운 → 라이브 HTML 변환 (publish 내부 서브스텝)
    trigger: "publish_to_multi() 내부 호출"
    actor: system
    enforced_by: "code: src/pipeline/converter.py::convert_markdown_to_html()"
    inputs: [published_content: markdown]
    action: |
      - CLAIM-xxx/SOURCE-xxx 인용 태그를 [1][2] 형식 각괄호로 정리.
      - 로컬 이미지 경로(file:///...)를 content/images/로 복사 후 GitHub Raw CDN URL로 치환
        (push 안 돼 있으면 라이브에서 깨짐 — publish 스텝의 ensure_images_pushed가 이를 보장).
      - '## 참고문헌' 추출(구조화 렌더링용) + '## 백링크' 추출(2026-08-22부터 렌더링 대상,
        예전엔 그냥 삭제만 됨 — wiki/Incident_Log.md#backlink-bug-2026-08-22).
      - '## 사실 검증 결과', '## 차별화 포인트', '## 참고문헌', '## 백링크'를 본문에서 제거(내부 전용).
      - H1 제목을 <h2 class="post-body-title">로 치환, 나머지 ##/### 헤딩으로 TOC 생성(메타 섹션명 제외).
      - mistune 커스텀 렌더러: 헤딩 앵커, ```mermaid → <div class="mermaid">, 코드블록은 pygments
        monokai 하이라이팅.
      - 결과 조립: 본문 HTML + (있으면) 접이식 '📚 참고문헌' 블록 + (있으면) 노출형 '🔗 관련 글' 블록
        + 테마 CSS/pygments CSS를 인라인한 <div class="tech-blog-post"> 컨테이너.
    outputs: {html: string, references_html: string, toc: list}
    checks: []
    next: publish_blogger

  - id: publish_blogger
    order: 8.2
    name: Blogger API 게시 (publish 내부 서브스텝)
    trigger: "publish_to_multi() 내부 → BloggerPublisher.publish()"
    actor: system
    enforced_by: "code: src/publishers/blogger.py::BloggerPublisher"
    inputs: {title: string, html: string, tags: list, existingPostId: "string|null"}
    action: |
      1. .env의 BLOGGER_CLIENT_ID/SECRET/BLOG_ID/REFRESH_TOKEN 로드.
      2. refresh_token으로 우선 시도: posts().update()(existingPostId 있으면) 또는 posts().insert().
      3. 실패 시 대화형 브라우저 OAuth 폴백(localhost:8080/oauth2callback 로컬 서버, 브라우저 자동
         오픈, 토큰 교환 후 .env의 BLOGGER_REFRESH_TOKEN 자동 갱신).
      4. dry-run이면 실제 API 호출 없이 제목/태그/HTML 글자수만 로그.
    outputs: {postId: string, url: string, publishedAt: string}
    checks:
      - id: response_completeness
        rule: "postId/url 둘 다 없으면 예외 발생"
        severity: error
    next: archive_and_transfer

  - id: archive_and_transfer
    order: 9
    name: content/posts/<Category>/ 정식 자산 이관
    trigger: "publish_to_multi() 마지막 단계 (dry-run이 아닐 때만)"
    actor: system
    enforced_by: "code: src/publishers/__init__.py::publish_to_multi() 하단"
    inputs: ["temp/runs/<run_id>/final.md (원본, sanitize 전)", publish_results]
    action: >
      slug는 final.md frontmatter를 신뢰 소스로 사용(state.slug는 항상 비어있음). frontmatter의
      status=published, id=Blogger postId(내부 articleId 아님 — 이후 유지보수 도구들이 이 id를
      API postId로 그대로 씀), url, publishedAt을 실제 게시 결과로 덮어써서 content/posts/<Category>/<slug>.md에
      (Category는 src/core/paths.py::category_for_tags()가 tags 기준으로 결정, 2026-08-23 신설)
      **원본 그대로**(sanitize된 published_content가 아니라 final.md의 content) 저장.
    outputs: ["content/posts/<Category>/<slug>.md"]
    checks: []
    next: null  # 파이프라인 끝

post_publish_maintenance:  # 위 순차 파이프라인과 별도 — 발행 후 필요할 때만 개별 실행
  note: "새 일회성 스크립트를 만들지 말고 아래 --dry-run 지원 도구를 재사용/확장할 것 (convention)"
  tools:
    - {cmd: "src/tools/update_post_content.py --slug <slug> --body-file <path> [--title]", purpose: "발행 글 본문 부분 수정 후 라이브 반영"}
    - {cmd: "src/tools/apply_nav_labels.py", purpose: "상단 탭(Basics/Advanced/ETC) 라벨 백필"}
    - {cmd: "src/tools/patch_published_posts.py", purpose: "라이브 게시물 일괄 패치"}
    - {cmd: "src/tools/report_fact_check_stats.py", purpose: "factCheckScore/verdict 분포 점검 (읽기 전용)"}
    - {cmd: "src/tools/archive_session_log.py --dry-run|--keep N", purpose: "session-handoff.md Session log 정리"}
    - {cmd: "src/tools/build_session_backlink_index.py / apply_session_backlinks.py / lint_session_backlinks.py", purpose: "세션 backlink 줄 범위 인덱스/적용/검사"}
    - {cmd: "src/tools/build_moc.py", purpose: "content/posts/<Category>/_MOC.md(Obsidian MOC) 재생성 — 각 글의 실제 ## 백링크 관계를 tags 기준 그룹으로 정리. 새 글 발행/백링크 수정 후 재실행 권장(2026-08-23 신설)"}

related_but_separate_pipelines:  # 이 문서의 주 스코프(글 작성) 밖 — main.py의 다른 서브커맨드
  - {cmd: "python main.py sync", purpose: "Notion 페이지 → MDX 동기화", code_ref: "src/pipeline/sync_mdx.py"}
  - {cmd: "python main.py todo [--status]", purpose: "final.md '## 꼬리질문'에서 파싱된 TODO 조회", code_ref: "src/pipeline/knowledge_store.py"}
  - {cmd: "python main.py backlinks --run <run_id>", purpose: "지식 그래프 기반 백링크/참고문헌 조회", code_ref: "wiki/knowledge-graph.json"}
  - {cmd: "python main.py theme [--upload]", purpose: "Blogger 테마 관리 — 라이브 반영은 여전히 수동(Blogger HTML 편집기 직접 붙여넣기)", code_ref: "src/theme/theme.py"}

guardrails:  # 특정 스텝에 묶이지 않는 전역 제약 — 전부 convention(자동 검증 없음, 사람이 지킬 것)
  - id: no_one_off_scripts
    rule: "scratch/ 등에 일회성 API 푸시 스크립트 작성 전면 금지 — 오직 python main.py 정식 파이프라인만"
    source: "wiki/Blog_Writing_Rules.md #1, AGENTS.md §3"
  - id: confirmed_body_immutable
    rule: "관리자가 승인한 final.md 본문은 AI가 임의로 축약·수정·삭제·재작성 금지 — 오류는 src/나 게이트를 고쳐서 해결"
    source: "wiki/rules/blogger_rules.md §1"
  - id: batch_approval_not_transitive
    rule: "'발행해' 같은 배치 단위 사전 승인은 개별 초안에 대한 사전 검토를 대체하지 않는다 — fork에게 approve+publish까지 위임 금지"
    source: "session-handoff 2026-08-19 재발 사례, ~/.claude/.../memory/feedback_subagent_scope_discipline.md"
  - id: differentiation_required
    rule: "새 글은 '## 차별화 포인트'로 상위 검색결과 대비 부가가치를 먼저 명시 — 포화 101 주제는 이 각도 없이 지양"
    source: "wiki/Blog_Writing_Rules.md #14"
  - id: internal_links_must_be_real
    rule: "'## 백링크'에는 실제 라이브 URL만(https://beji-tech.blogspot.com/...) — 저장소 내부 상대경로 금지"
    source: "wiki/Blog_Writing_Rules.md #15"
  - id: utf8_only
    rule: "final.md는 항상 UTF-8로 쓰고 멀티바이트 문자를 자르는 부분 편집 금지"
    source: "wiki/Blog_Writing_Rules.md #8"
  - id: quality_over_word_count
    rule: "섹션 최소 분량은 하한선일 뿐 — 할루시네이션/불필요한 난해함/과도한 단순화(패딩) 금지, 자동 게이트가 못 잡는 부분"
    source: "wiki/Blog_Writing_Rules.md #13"

file_map:  # run 디렉토리 및 관련 파일 빠른 참조
  run_dir: "temp/runs/<runId>/"
  run_dir_files: [state.json, request.md, article-template.md, final.md, publish-result.json]
  gate_config: src/core/publish_gate.json
  gate_logic: src/pipeline/validate.py
  seo_check: "src/pipeline/seo_check.py (2026-08-22 신설, validate.py와 분리된 독립 모듈)"
  theme_meta_description: "content/theme/blogger_site_theme.xml <head> (data:post.body snippet() 기반, 수동 배포 필요)"
  converter: src/pipeline/converter.py
  publishers: [src/publishers/blogger.py, src/publishers/notion.py]
  article_template: wiki/templates/article.md
  writing_rules: wiki/Blog_Writing_Rules.md
  incident_log: wiki/Incident_Log.md
  topic_backlog: wiki/Post_Topic_Backlog.md
  final_archive: "content/posts/<Category>/<slug>.md  (Category: Basics|Advanced|ETC, src/core/paths.py::category_for_tags())"
```

## 관련 세션
- `../sessions/raw/2026-08-16.md:31178-31214` (pipeline, 2026-08-16)
- `../sessions/raw/2026-08-16.md:34838-34954` (pipeline, 2026-08-16)
- 전체 인덱스: [Session_Index.md](../Session_Index.md)
