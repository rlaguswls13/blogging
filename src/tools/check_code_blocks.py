"""
코드 품질 검증 — element_matrix의 '코드' check(automated: false)를 채우는 작성 보조 도구.
지금까지 code_or_image_presence 게이트는 코드펜스가 "있는지"만 봤고, 실제로 구문이 맞는지나
설명과 일치하는지는 전혀 보지 않았다.

이 도구는 두 가지를 확인한다(둘 다 정적 분석, 실제로 코드를 실행하지는 않음 — 부작용 위험 없음):

1. **구문 검사(syntax check)**: python/bash/json은 실제 파서로 구문 오류를 잡는다
   (python: compile(), bash: `bash -n`, json: json.loads()). 그 외 언어(SQL/Go/protobuf 등)는
   파서가 없어 건너뛴다 — "돌아가는지"까지는 여전히 human_verify 몫이다.
2. **설명-코드 일치(logic-matches-description, 2026-08-23 신설)**: 코드펜스 바로 앞 문단에서
   백틱으로 인용된 식별자(`` `함수명()` ``, `` `변수명` `` 등)를 뽑아, 그 식별자가 실제로 코드
   블록 안에 등장하는지 확인한다. "다음은 chansend() 함수의 락 획득 부분입니다"라고 써놓고
   코드에 chansend가 없으면 설명과 코드가 어긋난다는 신호로 잡는다. 완벽하지 않다(식별자가
   맞아도 로직 자체가 설명과 다를 수 있음) — 그래도 복붙 실수나 설명만 고치고 코드는 안 고친
   경우처럼 흔한 실수는 잡는다.

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


def extract_code_blocks(body):
    """(lang, code, preceding_context) 튜플 리스트. preceding_context는 코드펜스 직전 문단."""
    blocks = []
    for m in re.finditer(r"```(\w*)\n(.*?)```", body, re.DOTALL):
        lang = m.group(1).lower()
        code = m.group(2)
        context_start = max(0, m.start() - CONTEXT_CHARS)
        context = body[context_start:m.start()]
        blocks.append((lang, code, context))
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
    try:
        json.loads(code)
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


def extract_claimed_identifiers(context_text):
    """직전 문단의 백틱 인용에서 식별자로 보이는 것만 추린다(순수 한글 단어/일반 용어 제외)."""
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
        identifiers.append(token)
    return identifiers


def check_logic_match(code, context):
    claimed = extract_claimed_identifiers(context)
    missing = [ident for ident in claimed if ident.rstrip("()") not in code and ident not in code]
    return claimed, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()

    final_path = run_directory(args.run) / "final.md"
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
