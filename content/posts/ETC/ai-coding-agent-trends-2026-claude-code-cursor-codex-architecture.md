---
author: ''
createdAt: '2026-08-26T00:25:46.648150Z'
factCheckScore: 0
id: '5941025659260864025'
notionPageId: null
publishedAt: '2026-08-25T22:45:33-07:00'
slug: ai-coding-agent-trends-2026-claude-code-cursor-codex-architecture
status: published
tags:
- ETC
- AI
- LLM
- Agentic Coding
title: AI 코딩 에이전트 트렌드 2026 — Claude Code, Cursor, Codex의 아키텍처적 차이
updatedAt: '2026-08-26T00:25:46.648150Z'
url: https://beji-tech.blogspot.com/2026/08/ai-2026-claude-code-cursor-codex.html
---

# AI 코딩 에이전트 트렌드 2026 — Claude Code, Cursor, Codex의 아키텍처적 차이

## 요약

Claude Code, Cursor, OpenAI Codex CLI는 모두 "도구를 반복 호출해 코드를 직접 수정하는 에이전틱 루프" 위에서 동작하지만, 그 루프를 안전하게 굴리는 방식은 세 제품이 서로 다른 길을 택했습니다. 이 글은 마케팅 페이지의 기능 나열이 아니라 세 제품의 2026년 8월 기준 공식 문서를 직접 대조해, (1) 도구 실행을 언제·어떻게 승인할지 결정하는 권한/샌드박스 모델과 (2) 장시간 작업에서 컨텍스트 윈도우를 관리하는 방식이라는 두 아키텍처 축에서 실제 차이를 정리합니다. Claude Code는 권한 모드와 선언적 allow/deny/ask 규칙에 OS 수준 샌드박스를 얹은 3중 구조를, Cursor는 허용목록·샌드박스·LLM 분류기를 순차 적용하는 Auto-review 삼단 필터를, Codex CLI는 sandbox_mode와 approval_policy라는 두 개의 독립 축을 config.toml로 명시하는 방식을 씁니다.

## 차별화 포인트

<!--
내부 전용 섹션(라이브 배포 시 자동 제거됨, 사실 검증 결과/참고문헌 처리와 동일).
게시 게이트 최소 40단어. 이 글이 같은 주제 상위 검색결과 대비 무엇을 더하는지 최소 1가지를 구체적으로
쓸 것 (wiki/Blog_Writing_Rules.md 14번 수칙) — 예: 직접 돌려본 벤치마크 수치, 실제 겪은 프로덕션
이슈/장애, 흔치 않은 조합/트레이드오프, 다른 곳에서 보기 힘든 비교표, 실제 실행해보고 확인한 예상 밖
동작. "정의 + 교과서적 예시"만 있는 포화 101 주제(GoF 패턴류 등)는 이 각도 없이는 신규 작성을 지양한다.
-->

이 주제로 검색되는 대다수 글은 "Claude Code는 터미널형이고 Cursor는 IDE형"이라는 표면적 UX 비교나 가격/구독 모델 나열에 그친다. 이 글은 대신 세 제품의 2026-08-26 시점 공식 문서(code.claude.com, cursor.com, learn.chatgpt.com/OpenAI Codex 문서, github.com/openai/codex)를 직접 열어 대조한 뒤, 다른 글에서 한 표로 보기 어려운 권한 모델 비교표(권한 모드/승인 정책/샌드박스 OS 프리미티브/설정 파일 형식)를 구성했다. 특히 Claude Code의 permission mode와 OS 샌드박스가 별개 레이어라는 점, Cursor의 Auto-review가 허용목록→샌드박스→LLM 분류기 3단계로 동작한다는 점, Codex의 sandbox_mode와 approval_policy가 서로 독립적인 두 축이라는 점은 공식 문서를 원문 대조해야만 정확히 파악되는 세부사항으로, 표면적 기능 비교 글에서는 거의 다뤄지지 않는다. 컨텍스트 관리 축에서도 Claude Code의 격리된 서브에이전트 위임과 Codex의 AGENTS.md 계층적 병합을 나란히 놓고 비교한다.

## 본문

<!--
게시 게이트(src/core/publish_gate.json::sectionMinWords) 기준 최소 800단어.
코드펜스(예: ```java ... ```) 또는 이미지 중 최소 1개는 반드시 포함할 것 — 둘 다 없으면
발행 게이트에서 오류로 차단된다(2026-08-22부터 경고 아님).
-->

### 1. 세 제품이 공유하는 공통 골격: 에이전틱 툴-유즈 루프

Claude Code, Cursor, Codex CLI는 모두 "모델이 도구 호출을 제안 → 실행 여부 판단 → 실행 결과를 모델에게 다시 넣음 → 반복"이라는 동일한 루프 구조 위에서 동작합니다. 의사코드로 단순화하면 다음과 같습니다.

```python
# 세 제품 공통의 단순화된 에이전틱 툴-유즈 루프 (개념적 pseudocode)
def agent_loop(user_task, context):
    while not task_done:
        model_output = llm.generate(context)           # 다음 행동 제안
        if model_output.tool_call is None:
            break                                       # 텍스트 응답만 반환, 종료

        tool_call = model_output.tool_call
        decision = permission_layer.evaluate(tool_call)  # 여기서 3사 아키텍처가 갈린다

        if decision == "ask":
            approved = prompt_user(tool_call)
            if not approved:
                context.append(denial_result(tool_call))
                continue

        if decision in ("allow", "ask_and_approved"):
            result = sandbox.run(tool_call)               # OS 수준 격리 여부도 갈린다
        else:  # "deny"
            result = denial_result(tool_call)

        context = context_manager.update(context, result)  # 여기서도 3사가 갈린다
    return final_summary
```

세 제품이 갈라지는 지점은 정확히 이 의사코드의 두 곳입니다 — `permission_layer.evaluate()`(그리고 `sandbox.run()`)와 `context_manager.update()`. 아래에서 공식 문서를 근거로 각각을 비교합니다.

### 2. 권한/샌드박스 모델: 세 가지 서로 다른 철학

**Claude Code**는 권한 결정을 두 개의 독립 레이어로 나눕니다. 첫째는 세션 전체의 기본 태도를 정하는 permission mode로, 공식 문서는 `default`(수동 승인), `acceptEdits`(파일 편집 자동 승인), `plan`(읽기 전용 탐색), `auto`(별도 분류기 모델이 매 행동을 검토), `dontAsk`(사전 승인된 도구만 허용, CI용), `bypassPermissions`(전부 자동 승인, 격리 컨테이너 전용) 6가지를 정의합니다. 둘째는 `settings.json`의 선언적 allow/deny/ask 규칙으로, 도구별·명령별로 세밀하게 제어합니다.

```json
// Claude Code settings.json — 도구별 allow/deny/ask 규칙 예시 (공식 문서 기준)
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "allowWrite": ["~/.kube", "/tmp/build"]
    },
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org"]
    }
  }
}
```

여기에 세 번째 레이어로 OS 수준 샌드박스가 얹힙니다. macOS에서는 Apple의 Seatbelt(`sandbox-exec`) 프레임워크를, Linux·WSL2에서는 `bubblewrap`을 이용해 Bash 명령과 그 자식 프로세스의 파일시스템·네트워크 접근을 커널 수준에서 강제합니다. 중요한 점은 permission mode가 "이 명령을 실행해도 되는지" 모델 판단 이전 단계에서 승인 여부를 정하는 반면, 샌드박스는 "이미 승인되어 실행 중인 프로세스가 실제로 무엇을 건드릴 수 있는지"를 운영체제가 강제한다는 것 — 둘은 공식 문서에서 명시적으로 "상호 보완적인 레이어(complementary layers)"로 설명됩니다.

**Cursor**는 2026년 5월 출시된 Cursor 3.6부터 "Run Mode"라는 개념으로 이를 통합했습니다. 기본값인 **Auto-review**는 3단계 필터를 순차 적용합니다 — (1) 사용자가 정의한 허용목록에 있는 명령은 즉시 실행, (2) 그 외 셸 명령은 가능하면 샌드박스 안에서 실행, (3) 전체 시스템 접근이 필요한 호출만 LLM 분류기(Claude Haiku 4.5 또는 GPT-5.4 Mini 계열)로 넘겨 자동 승인·대안 제안·사용자 승인 요청 중 하나를 결정합니다. **Allowlist** 모드는 분류기 없이 결정론적으로 허용목록만 신뢰하고, **Run Everything**은 샌드박스와 분류기를 모두 끄고 전부 자동 실행합니다. 샌드박스 자체의 OS 프리미티브는 macOS Seatbelt, Linux는 Landlock(파일시스템 제한)과 seccomp(위험 시스템콜 차단) 조합으로, 커널 6.2 이상과 unprivileged user namespace를 요구합니다. 분류기의 판단 기준은 자연어 지시문(`permissions.json`)으로 커스터마이즈할 수 있습니다.

**Codex CLI**는 두 축을 완전히 분리했습니다. `sandbox_mode`는 프로세스가 물리적으로 무엇에 접근 가능한지(`read-only` / `workspace-write` / `danger-full-access`)를, `approval_policy`는 언제 사용자에게 승인을 물을지(`untrusted` / `on-request` / `on-failure` / `never`)를 각각 독립적으로 결정합니다. 즉 "샌드박스 안에서 실행되더라도 매번 물어보게" 하거나 반대로 "위험한 접근 범위를 열어두되 실패했을 때만 물어보게" 하는 조합이 모두 가능합니다. OS 수준 강제는 macOS Seatbelt, Linux·WSL2는 `bubblewrap` 기반 Landlock/user namespace 제한을 사용합니다.

```toml
# Codex CLI config.toml — 두 축을 독립적으로 지정하는 예시 (공식 문서 기준)
# sandbox_mode 선택지: "read-only" | "workspace-write" | "danger-full-access"
# approval_policy 선택지: "untrusted" | "on-request" | "on-failure" | "never"
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false        # 기본값: 워크스페이스 밖 네트워크는 차단
writable_roots = ["/tmp"]     # .git, .codex 디렉터리는 이 모드에서도 읽기 전용 유지
```

| 비교 항목 | Claude Code | Cursor | Codex CLI |
|---|---|---|---|
| 승인 결정 축 | permission mode(6종) + allow/deny/ask 규칙 | Run Mode(Auto-review/Allowlist/Run Everything) 단일 축 | sandbox_mode × approval_policy 독립 2축 |
| 자동 승인 보조 수단 | `auto` 모드의 별도 분류기 모델 | Auto-review의 LLM 분류기(허용목록·샌드박스 실패 시에만 호출) | 없음(정책값 자체가 결정, 분류기 미사용) |
| macOS 샌드박스 | Seatbelt | Seatbelt(`sandbox-exec`) | Seatbelt |
| Linux/WSL2 샌드박스 | bubblewrap | Landlock + seccomp(커널 6.2+ 요구) | bubblewrap 기반 Landlock |
| 설정 파일 | `settings.json`(JSON) | `permissions.json` + `sandbox.json` | `config.toml` |
| 완전 무제한 모드 | `bypassPermissions` | Run Everything(샌드박스·분류기 모두 비활성) | `danger-full-access` |

세 설계 모두 "완전 자동 실행" 옵션을 제공하지만 공통적으로 격리된 컨테이너·VM 안에서만 쓰라고 경고합니다 — Claude Code 문서는 `bypassPermissions`를 "격리된 컨테이너와 VM 전용"으로, Codex 문서는 `danger-full-access`를 파일시스템·네트워크 경계를 모두 제거하는 모드로 명시합니다.

### 3. 컨텍스트 관리: 서브에이전트 위임 vs. 단일 루프

권한 모델만큼이나 실무 체감이 큰 차이는 컨텍스트 윈도우 관리 방식입니다. Claude Code는 **서브에이전트(Task/Agent 도구)**로 위임하는 구조를 씁니다. 메인 대화가 탐색·테스트 실행처럼 장황한 출력을 만드는 작업을 서브에이전트에 맡기면, 서브에이전트는 완전히 격리된 별도 컨텍스트 윈도우에서 파일을 읽고 로그를 쌓다가 요약본만 메인 대화로 반환합니다. 공식 문서는 이를 "탐색용 서브에이전트가 15만 토큰을 소모해도 메인 대화에는 요약 몇 줄만 남는다"는 식으로 설명하며, 서브에이전트별로 도구 접근 권한과 모델(예: 저비용 모델로 탐색만 전담)을 다르게 제한할 수 있다고 명시합니다. 최대 3단계까지 중첩 위임이 가능하고 동시 실행 개수는 기본 20개로 제한됩니다.

Cursor는 이와 달리 코드베이스 전체를 사전에 인덱싱해 두는 방식에 가깝습니다. 워크스페이스 인덱스가 프로젝트 구조에 대한 의미론적 이해를 미리 구축해 두고, 에이전트는 `@codebase` 같은 참조로 필요한 부분만 끌어오는 검색 기반 접근을 취합니다 — 서브에이전트로 작업을 물리적으로 격리하기보다는, 단일 세션 컨텍스트 윈도우 안에서 인덱스 검색으로 필요한 정보만 선별해 넣는 접근입니다.

Codex CLI는 `AGENTS.md` 계층 구조로 프로젝트 규칙을 컨텍스트에 주입합니다. 공식 문서에 따르면 Codex 홈 디렉터리(`~/.codex`)의 전역 `AGENTS.md`부터 시작해 Git 저장소 루트에서 현재 작업 디렉터리까지 각 단계의 `AGENTS.md`(및 `AGENTS.override.md`)를 순서대로 찾아 병합하며, 기본 32KiB 바이트 한도에 도달하면 누적을 멈춥니다. 이는 "여러 전문화된 서브에이전트로 나누는" Claude Code 방식이 아니라 "단일 대화 컨텍스트에 계층적으로 지시문을 쌓는" 방식이라는 점에서 근본적으로 다른 설계입니다. Codex 문서 목록에는 별도의 서브에이전트 설정 페이지가 존재함이 확인되나(경로: `agent-configuration/subagents`), 이번 조사 시점에는 해당 페이지 본문에 접근하지 못해 Codex의 서브에이전트 기능 세부 동작은 이 글에서 검증하지 못했습니다 — 이 부분은 `## 한계와 반론`에 명시합니다.

### 4. 실무 시사점

세 아키텍처는 "얼마나 자율적으로 돌릴 것인가"에 대한 서로 다른 기본 가정을 반영합니다. Claude Code는 권한 모드와 샌드박스를 분리해 "무엇을 승인할지"와 "승인된 프로세스가 실제로 무엇에 닿을 수 있는지"를 별도로 통제하려는 방어적 이중화 설계에 가깝고, Cursor는 분류기를 앞세워 승인 피로(approval fatigue) 자체를 줄이는 데 무게를 뒀으며, Codex CLI는 두 축을 명시적으로 분리해 세밀한 조합을 코드로 관리하려는 설정 지향적 설계입니다. 어느 쪽이 "더 안전한가"보다는, 팀의 CI 파이프라인·컨테이너 격리 여부·감사(audit) 요구사항에 어떤 축이 더 잘 들어맞는지를 기준으로 선택하는 것이 실무적으로 타당합니다.

## 사실 검증 결과

| Claim | 판정 | 근거 |
|---|---|---|
| CLAIM-001: Claude Code는 permission mode(default/acceptEdits/plan/auto/dontAsk/bypassPermissions) 6종을 제공하며, `auto` 모드는 별도 분류기 모델이 각 행동을 검토한다 | verified | code.claude.com/docs/en/permission-modes 공식 문서(2026-08-26 접속, "Available modes" 표) |
| CLAIM-002: Claude Code의 Bash 샌드박스는 macOS에서 Seatbelt, Linux·WSL2에서 bubblewrap을 사용해 파일시스템·네트워크를 OS 수준에서 격리하며, permission mode와는 상호 보완적인 별도 레이어다 | verified | code.claude.com/docs/en/sandboxing 공식 문서(2026-08-26 접속, "OS-level enforcement", "How sandboxing relates to permissions and permission modes" 절) |
| CLAIM-003: Claude Code 서브에이전트는 메인 대화와 분리된 격리 컨텍스트 윈도우에서 실행되며 Agent(Task) 도구로 위임되고, 최대 3단계 중첩·기본 동시 20개 제한이 있다 | verified | code.claude.com/docs/en/sub-agents 공식 문서(2026-08-26 접속, "Depth & Concurrency Limits" 절) |
| CLAIM-004: Cursor 3.6(2026-05-29 출시)의 Auto-review 모드는 허용목록→샌드박스→LLM 분류기 순으로 도구 호출을 처리하며, 샌드박스는 macOS Seatbelt, Linux는 Landlock+seccomp(커널 6.2+)를 사용한다 | verified | cursor.com/docs/agent/security/run-modes 공식 문서(2026-08-26 접속, "Sandbox Implementation" 절) |
| CLAIM-005: Codex CLI는 config.toml의 sandbox_mode(read-only/workspace-write/danger-full-access)와 approval_policy(untrusted/on-request/on-failure/never)를 독립된 두 축으로 지정하며, workspace-write 모드에서도 .git/.codex 디렉터리는 읽기 전용으로 남는다 | verified | learn.chatgpt.com/docs/config-file/config-basic (OpenAI Codex 공식 문서, 2026-08-26 접속) |
| CLAIM-006: Codex CLI는 macOS에서 Seatbelt, Linux·WSL2에서 bubblewrap 기반 Landlock 제한을 OS 수준 샌드박스 강제 메커니즘으로 사용한다 | verified | learn.chatgpt.com/docs/sandboxing (OpenAI Codex 공식 문서, 2026-08-26 접속, "Enforcement Mechanisms" 절) |
| CLAIM-007: Codex CLI의 AGENTS.md는 `~/.codex`의 전역 파일부터 Git 저장소 루트~현재 디렉터리까지 계층적으로 탐색·병합되며 기본 32KiB 바이트 한도가 있다 | verified | learn.chatgpt.com/docs/agent-configuration/agents-md (OpenAI Codex 공식 문서, 2026-08-26 접속, "Hierarchical Discovery Process" 절) |

## 작성자의 견해

> 이 부분은 확정된 사실이 아니라 필자 개인의 해석과 견해임을 밝힙니다.

세 제품의 권한 모델을 나란히 놓고 보면, "자율성과 안전성은 트레이드오프"라는 통념이 실제로는 "어느 축을 분리하느냐"의 설계 문제로 환원된다는 인상을 받았습니다. Claude Code는 승인 여부(permission mode)와 실행 범위(샌드박스)를 물리적으로 분리해서, 설령 모델이 뭔가를 승인해버려도 OS가 한 번 더 막아주는 이중 방어선을 만든 것처럼 보입니다. 반대로 Cursor의 Auto-review는 그 판단 자체를 또 다른 LLM(분류기)에게 맡겨서 승인 피로를 줄이는 쪽에 베팅했는데, 이는 사용자 경험은 좋아지지만 "분류기가 실수로 승인해버릴 가능성"이라는 새로운 실패 지점을 만든다는 점에서 개인적으로는 다소 불안한 선택이라고 봅니다. Cursor 공식 문서 스스로도 "분류기는 실수할 수 있다"고 명시한 것이 인상적이었습니다. Codex CLI가 sandbox_mode와 approval_policy를 완전히 독립된 두 축으로 쪼갠 것은 세 제품 중 가장 "인프라 엔지니어스러운" 설계로 느껴지는데, 유연성은 가장 크지만 그만큼 잘못 조합했을 때(예: workspace-write + never) 위험한 조합을 사용자가 스스로 만들 수 있다는 부담도 큽니다. 결국 어떤 도구를 쓰든 "기본값을 얼마나 신뢰하고 얼마나 커스터마이즈할 것인가"가 실무에서 가장 중요한 판단 기준이 될 것이라는 게 제 사견입니다.

## 한계와 반론

이 글은 2026년 8월 26일 시점에 접속 가능했던 세 벤더의 공식 문서 스냅샷을 기준으로 작성되었습니다. AI 코딩 에이전트 시장은 두세 달 단위로 기능이 개편되는 극도로 빠른 속도의 영역이라, 여기 서술한 구체적인 설정 키 이름(예: `sandbox_workspace_write`)이나 기본값, 모드 이름(예: Cursor의 "Auto-review"는 과거 "YOLO 모드"에서 개명된 것으로 확인됨)은 몇 달 안에 다시 바뀔 가능성이 실제로 높습니다. 또한 Codex CLI의 서브에이전트 기능은 공식 문서 목록에 페이지 경로만 확인되고 본문 접근에 실패해 이 글에서 다루지 못했으며, Codex CLI의 컨텍스트 자동 압축 임계값(예: 컨텍스트 창의 몇 %에서 발동하는지)에 대한 구체적 수치는 조사 과정에서 비공식 기술 블로그에는 언급되어 있었으나 이번에 접근한 OpenAI 공식 문서 페이지에서는 확인하지 못해, 근거가 불충분하다고 판단해 사실 검증 표에 아예 올리지 않고 이 절에서 한계로만 명시합니다. 마지막으로 이 비교는 문서 기반 아키텍처 분석이며, 세 제품을 동일 작업으로 직접 벤치마크해 실제 승인 프롬프트 빈도나 컨텍스트 손실률을 정량 비교한 것은 아니라는 한계가 있습니다 — 이는 별도의 실측 후속 글이 필요한 영역입니다.

## 참고문헌

1. Anthropic, "Choose a permission mode" (Claude Code 공식 문서), https://code.claude.com/docs/en/permission-modes (확인일: 2026-08-26)
2. Anthropic, "Configure the sandboxed Bash tool" (Claude Code 공식 문서), https://code.claude.com/docs/en/sandboxing (확인일: 2026-08-26)
3. Anthropic, "Subagent Architecture in Claude Code" (Claude Code 공식 문서), https://code.claude.com/docs/en/sub-agents (확인일: 2026-08-26)
4. Cursor, "Run Modes" (Cursor 공식 문서), https://cursor.com/docs/agent/security/run-modes (확인일: 2026-08-26)
5. OpenAI, "Config file basics" (Codex CLI 공식 문서), https://learn.chatgpt.com/docs/config-file/config-basic (확인일: 2026-08-26)
6. OpenAI, "Sandboxing" (Codex CLI 공식 문서), https://learn.chatgpt.com/docs/sandboxing (확인일: 2026-08-26)
7. OpenAI, "AGENTS.md" (Codex CLI 공식 문서), https://learn.chatgpt.com/docs/agent-configuration/agents-md (확인일: 2026-08-26)
8. OpenAI, "openai/codex" GitHub 저장소(공식 소스 및 문서 인덱스), https://github.com/openai/codex (확인일: 2026-08-26)

## 종합적 의견

> 이 섹션은 개별 벤더 문서 대조를 넘어선 전체 주제에 대한 필자의 종합적 견해와 해석을 담고 있습니다.

2026년 시점 AI 코딩 에이전트 3사의 아키텍처를 종합하면, 업계가 "에이전트를 얼마나 자율적으로 풀어놓을 것인가"라는 단일 축의 문제에서 벗어나 "자율성을 구성하는 여러 통제 지점(승인 시점, 실행 범위, 컨텍스트 격리)을 각각 어떻게 설계할 것인가"라는 다차원 문제로 넘어가고 있다는 인상을 받습니다. Claude Code의 이중 레이어(권한 모드 + OS 샌드박스), Cursor의 삼단 필터(허용목록 + 샌드박스 + 분류기), Codex CLI의 이축 분리(sandbox_mode × approval_policy)는 표면적으로는 다른 이름을 쓰지만, 공통적으로 "결정을 내리는 계층"과 "결정을 강제하는 계층"을 분리하려는 수렴적 진화로 읽힙니다. 특히 세 제품 모두 macOS에서는 Seatbelt를, Linux 계열에서는 Landlock/bubblewrap 계열 커널 프리미티브를 공유한다는 점은, 개별 벤더가 자체 격리 기술을 새로 발명하기보다 OS가 이미 제공하는 검증된 프리미티브 위에서 정책 레이어만 차별화하는 쪽으로 업계 전체가 수렴하고 있음을 보여줍니다. 실무에서 도구를 고를 때는 "어느 제품이 더 똑똑한가"보다 "우리 조직의 감사·컴플라이언스 요구사항이 이 세 가지 통제 축 중 어디에 가장 민감한가"를 먼저 물어보는 편이 더 생산적인 질문이라고 생각합니다. 컨텍스트 관리 방식의 차이(서브에이전트 위임 vs. 인덱스 검색 vs. 계층적 지시문 병합) 역시 단순한 기술적 우열이 아니라, "긴 작업을 어떻게 잘게 쪼갤 것인가"에 대한 각 팀의 제품 철학 차이로 이해하는 것이 더 정확한 해석이라고 봅니다.

## 꼬리질문

1. Cursor의 Auto-review 분류기가 실제로 오탐(허용해서는 안 될 명령을 승인)하는 비율은 어느 정도이며, 이를 벤치마크한 공개 자료가 있는가?
   - 추천 참고 URL: https://cursor.com/docs/agent/security/run-modes
2. Codex CLI의 서브에이전트 기능(`agent-configuration/subagents`)은 Claude Code의 격리된 컨텍스트 윈도우 위임과 실제로 얼마나 유사하거나 다른가?
   - 추천 참고 URL: https://learn.chatgpt.com/docs/codex/cli

## 백링크

- [MCP(Model Context Protocol) 2026-07-28 스펙 갱신: Stateless 아키텍처 전환과 멀티 에이전트 시대의 표준화](https://beji-tech.blogspot.com/2026/08/mcpmodel-context-protocol-2026-07-28.html)
- [LLM Agent 오케스트레이션 프레임워크 비교 분석: AutoGen vs LangGraph](https://beji-tech.blogspot.com/2026/08/llm-agent-autogen-vs-langgraph.html)
- [RAG(검색 증강 생성) 시스템의 한계 극복을 위한 GraphRAG 아키텍처와 엔티티 추출 원리](https://beji-tech.blogspot.com/2026/08/rag-graphrag.html)