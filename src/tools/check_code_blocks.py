"""
코드 품질 검증 — element_matrix의 '코드' check(automated: false)를 채우는 작성 보조 도구.
지금까지 code_or_image_presence 게이트는 코드펜스가 "있는지"만 봤고, 실제로 구문이 맞는지나
설명과 일치하는지는 전혀 보지 않았다.

이 도구는 두 가지를 확인한다(둘 다 정적 분석, 실제로 코드를 실행하지는 않음 — 부작용 위험 없음):

1. **구문 검사(syntax check)**: python/bash/json은 실제 파서로 구문 오류를 잡는다
   (python: compile(), bash: `bash -n`, json: json.loads() — json은 `//` 줄 주석을 먼저
   벗겨내고 검사한다, 문서용 JSON 예시에 주석을 다는 건 흔한 관행이라 엄격한 JSON 파서가
   이를 오탐하는 걸 막기 위함, 2026-08-23 조정).
2. **설명-코드 일치(logic-matches-description, 2026-08-23 신설, 2026-08-23 정밀화)**:
   코드펜스 바로 앞 문단에서 백틱으로 인용된 식별자(`` `함수명()` ``, `` `변수명` `` 등)를
   뽑아, 그 식별자가 실제로 코드 블록 안에 등장하는지 확인한다. "다음은 chansend() 함수의
   락 획득 부분입니다"라고 써놓고 코드에 chansend가 없으면 설명과 코드가 어긋난다는 신호로
   잡는다. 완벽하지 않다(식별자가 맞아도 로직 자체가 설명과 다를 수 있음) — 그래도 복붙
   실수나 설명만 고치고 코드는 안 고친 경우처럼 흔한 실수는 잡는다.

   발행된 글 55개 전수 소급 감사(audit_published_posts.py) 결과 26건이 잡혔는데, 실제로
   전부 대조해보니 전부 오탐이었다(2026-08-23) — 원인은 두 가지로 수렴했다:
   (a) 문맥 추출이 400자 내에 있는 `##`/`###` 소제목 경계를 넘어가, 다른 절의 설명이 이
       코드블록과 무관한데도 식별자로 뽑힘 — 가장 흔한 원인. → 문맥을 가장 가까운 앞쪽
       헤딩에서 끊도록 수정.
   (b) 프로세가 실제 사례 인용이나 정의상 구성요소로 언급한 고유명사(`Logger`,
       `WindowsUIFactory`, `@ResponseBody` 등)를 식별자로 오인 — 이런 "구조 마커(`.`/`_`/
       `()`/`-` 등) 없는 민짜 단어"는 코드에 문자 그대로 나올 필요가 없는 배경 지식/비유
       인용인 경우가 대부분이었다. → 그런 토큰은 식별자 후보에서 제외.
   두 조정 모두 인용된 식별자에 함수 호출(`()`), 점 표기(`.`), snake_case(`_`), CLI
   플래그(`-`) 등 실제 코드 구조 마커가 있으면 여전히 검사 대상으로 남긴다 — 실제로 코드에
   있어야 할 것으로 보이는 식별자에 대한 민감도는 유지한 채, 배경 인용을 걸러내는 것이 목적.

사용법:
  python src/tools/check_code_blocks.py --run <run_id>
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.core.paths import run_directory

CONTEXT_CHARS = 400  # 코드펜스 앞에서 설명-일치 검사에 쓸 문맥 범위
MIN_IDENTIFIER_LEN = 2


HEADING_RE = re.compile(r"^#{2,6}\s+.+$", re.MULTILINE)


def extract_code_blocks(body):
    """(lang, code, preceding_context) 튜플 리스트. preceding_context는 코드펜스 직전 문단
    (단, 가장 가까운 앞쪽 ##/### 헤딩을 넘어가지 않는다 — 다른 절의 설명이 이 코드블록과
    무관하게 문맥으로 딸려오는 걸 막기 위함, 2026-08-23)."""
    blocks = []
    for m in re.finditer(r"```(\w*)\n(.*?)```", body, re.DOTALL):
        lang = m.group(1).lower()
        code = m.group(2)
        context_start = max(0, m.start() - CONTEXT_CHARS)
        window = body[context_start:m.start()]
        last_heading = None
        for hm in HEADING_RE.finditer(window):
            last_heading = hm
        if last_heading is not None:
            window = window[last_heading.end():]
        blocks.append((lang, code, window))
    return blocks


def check_python_syntax(code):
    try:
        compile(code, "<article-code-block>", "exec")
        return None
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (line {e.lineno})"


def check_bash_syntax(code):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return result.stderr.strip()
        return None
    except FileNotFoundError:
        return None  # bash 자체가 없는 환경 — 건너뜀
    finally:
        Path(path).unlink(missing_ok=True)


def check_json_syntax(code):
    # 문서용 JSON 예시에 `//` 줄 주석을 다는 건 흔한 관행(JSONC 스타일) — 표준 JSON엔 없는
    # 문법이지만 그 자체가 "코드 결함"은 아니므로, 검사 전에 주석 줄만 제거한다(2026-08-23).
    stripped = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)
    try:
        json.loads(stripped)
        return None
    except json.JSONDecodeError as e:
        return f"JSONDecodeError: {e.msg} (line {e.lineno})"


SYNTAX_CHECKERS = {
    "python": check_python_syntax,
    "py": check_python_syntax,
    "bash": check_bash_syntax,
    "sh": check_bash_syntax,
    "shell": check_bash_syntax,
    "json": check_json_syntax,
}


BARE_WORD_RE = re.compile(r"^@?[A-Za-z][A-Za-z0-9]*$")
FILE_EXTENSION_RE = re.compile(r"^\.[A-Za-z0-9]+$")


def extract_claimed_identifiers(context_text):
    """직전 문단의 백틱 인용에서 식별자로 보이는 것만 추린다(순수 한글 단어/일반 용어 제외).

    구조 마커(`.`/`_`/`()`/`-` 등)가 전혀 없는 민짜 단어(bare word, 대소문자 무관)와 파일
    확장자만 있는 토큰(`.proto` 등)은 제외한다 — 실제 감사에서 이런 토큰은 거의 항상 실제
    사례 인용/정의상 구성요소(예: `Logger`, `HikariCP`, `@ResponseBody`)이지, 코드에 문자
    그대로 나와야 하는 요구가 아니었다(2026-08-23, audit_published_posts.py 26건 전수 검토).
    """
    backticked = re.findall(r"`([^`]+)`", context_text)
    identifiers = []
    for token in backticked:
        token = token.strip()
        if len(token) < MIN_IDENTIFIER_LEN:
            continue
        # 식별자스러운 것만: 영문/숫자/./_/()가 포함되고 공백이 없는 짧은 토큰
        if " " in token or "\n" in token:
            continue
        if not re.search(r"[A-Za-z0-9_]", token):
            continue
        if FILE_EXTENSION_RE.match(token):
            continue
        if BARE_WORD_RE.match(token):
            continue
        identifiers.append(token)
    return identifiers


def _normalize(text):
    return re.sub(r"\s+", "", text)


def check_logic_match(code, context):
    claimed = extract_claimed_identifiers(context)
    normalized_code = _normalize(code)
    missing = []
    for ident in claimed:
        bare = ident.rstrip("()")
        if _normalize(ident) in normalized_code or _normalize(bare) in normalized_code:
            continue
        missing.append(ident)
    return claimed, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", help="run_id (temp/runs/<run_id>/final.md) — draft 단계용")
    group.add_argument("--file", help="이미 발행된 content/posts/<Category>/<slug>.md 등 임의 경로 — 소급 감사용(2026-08-23 신설)")
    args = parser.parse_args()

    final_path = Path(args.file) if args.file else (run_directory(args.run) / "final.md")
    if not final_path.exists():
        print(f"오류: {final_path} 없음", file=sys.stderr)
        sys.exit(1)

    body = final_path.read_text(encoding="utf-8")
    blocks = extract_code_blocks(body)
    if not blocks:
        print("코드펜스가 없습니다 — 이미지로 code_or_image_presence를 충족하는 경우일 수 있음.")
        return

    print(f"코드펜스 {len(blocks)}개 발견:\n")
    any_issue = False
    for i, (lang, code, context) in enumerate(blocks, 1):
        print(f"[{i}] 언어: {lang or '(미지정)'}, {len(code.splitlines())}줄")

        checker = SYNTAX_CHECKERS.get(lang)
        if checker:
            err = checker(code)
            if err:
                print(f"    ❌ 구문 오류: {err}")
                any_issue = True
            else:
                print(f"    ✅ 구문 검사 통과")
        else:
            print(f"    — 구문 검사기 없음(지원: {', '.join(sorted(set(SYNTAX_CHECKERS)))})")

        claimed, missing = check_logic_match(code, context)
        if claimed:
            if missing:
                print(f"    ⚠️ 설명-코드 불일치: 직전 문단이 언급한 {missing}가 코드에 안 보입니다")
                any_issue = True
            else:
                print(f"    ✅ 설명-코드 일치 확인({len(claimed)}개 식별자 전부 코드에 존재)")
        print()

    if any_issue:
        print("⚠️ 위 항목을 확인하세요 — 발행 게이트를 막지는 않지만 human_review 전에 고치는 걸 권장합니다.")
    else:
        print("✅ 전체 코드펜스 이상 없음.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
