"""
SEO meta description 사전 점검 — 기존 8개 발행 게이트(validate.py::validate_run())와는
완전히 분리된 독립 모듈이다. validate_run()을 건드리지 않고 main.py에서 별도로 호출한다.

배경: Blogger API v3의 Posts 리소스는 글별 검색 설명(search description) 필드를 제공하지
않는다(2026-08-22 확인, https://developers.google.com/blogger/docs/3.0/reference/posts,
Blogger 공식 커뮤니티 답변으로 재확인: support.google.com/blogger/thread/343506660).
그래서 <meta name="description">는 API/테마 어느 쪽으로도 프로그래밍적으로 채울 수 없고,
Blogger 글 편집기의 "검색 설명" 칸에 사람이 직접 입력하는 것만 유효하다(2026-08-23 확인 —
data:post.body를 <head>에서 snippet()으로 자르는 시도는 data:post.*가 Blog 위젯 루프 밖에서
항상 비어있어 실패함, content/theme/blogger_site_theme.xml 주석 참고).

그럼에도 이 모듈이 여전히 유효한 이유: 우리가 <meta name="description">를 못 채우더라도,
구글은 크롤링한 페이지의 실제 노출 텍스트(주로 본문 맨 앞부분, 즉 "## 요약" 섹션)를 자체적으로
분석해 검색 결과 스니펫을 자동 생성하는 경우가 많다. 즉 이 점검은 "메타 태그를 채운다"가 아니라
"구글이 자동으로 뽑아갈 가능성이 높은 문장이 검색 노출용으로 자연스러운지"를 사전에 보여주는
용도로 재해석해서 쓴다.

사용법:
  python src/pipeline/seo_check.py --run <run_id>
  또는: python main.py validate --run <run_id> --seo (main.py에서 이 모듈을 별도 호출)
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.core.paths import run_directory

SNIPPET_LENGTH = 160
MIN_SUMMARY_CHARS = 160  # 요약 섹션이 이보다 짧으면 스니펫이 조기 종료되거나 본문 앞부분이 섞여 들어감
GENERIC_OPENERS = ["이 글은", "이 글에서는", "본 글은", "본 포스트는", "오늘은"]


@dataclass
class SeoCheckResult:
    ok: bool
    snippet_preview: str
    summary_char_count: int
    warnings: List[str] = field(default_factory=list)


def _extract_section(body: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##(?!#)|\Z)", re.MULTILINE | re.DOTALL)
    m = pattern.search(body)
    return m.group(1).strip() if m else ""


def markdown_to_plain(text: str) -> str:
    """Blogger snippet(data:post.body, {links:false, linebreaks:false})가 하는 일을
    마크다운 단계에서 근사한다: 마크다운 문법 제거, 링크는 텍스트만 남기고, 줄바꿈은 공백으로."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # 코드펜스 제거
    text = re.sub(r"`([^`]*)`", r"\1", text)  # 인라인 코드
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # 이미지
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # 링크 -> 텍스트만
    text = re.sub(r"[*_>#-]", "", text)  # 마크다운 강조/인용/헤딩/목록 기호
    text = re.sub(r"\s+", " ", text).strip()  # 줄바꿈 -> 공백(linebreaks:false)
    return text


def check_meta_description(run_id: str) -> SeoCheckResult:
    run_dir = run_directory(run_id)
    final_path = run_dir / "final.md"
    if not final_path.exists():
        raise FileNotFoundError(f"{final_path} 없음 — draft 단계를 먼저 완료할 것")

    text = final_path.read_text(encoding="utf-8")
    body_start = text.index("\n# ")
    body = text[body_start:]

    summary = _extract_section(body, "요약")
    plain = markdown_to_plain(summary)

    warnings: List[str] = []
    if len(plain) < MIN_SUMMARY_CHARS:
        warnings.append(
            f"'## 요약' 섹션이 평문 기준 {len(plain)}자로 {MIN_SUMMARY_CHARS}자 미만입니다 — "
            f"라이브 스니펫이 요약만으로 안 채워지고 본문 시작부까지 섞여 들어갈 수 있습니다."
        )
    if any(plain.startswith(opener) for opener in GENERIC_OPENERS):
        warnings.append(
            "요약이 \"이 글은/오늘은\" 같은 상투적 도입부로 시작합니다 — "
            "검색 스니펫 앞부분은 클릭률에 영향을 주므로 핵심 내용부터 시작하는 것을 권장합니다."
        )
    if not plain:
        warnings.append("'## 요약' 섹션이 비어 있습니다 — 스니펫이 본문 시작부로 대체됩니다.")

    snippet_preview = plain[:SNIPPET_LENGTH]
    if len(plain) > SNIPPET_LENGTH and not snippet_preview.endswith((".", "다", "요", "?", "!")):
        # 문장 중간에서 잘리면 어색하므로 마지막 완결 지점까지만 보여주는 별도 참고용 프리뷰도 덧붙임
        cut = max(snippet_preview.rfind(". "), snippet_preview.rfind("다 "), snippet_preview.rfind("요 "))
        if cut > SNIPPET_LENGTH * 0.5:
            warnings.append(
                f"{SNIPPET_LENGTH}자 지점이 문장 중간입니다 — 실제로는 '...{snippet_preview[max(0, cut-20):cut+1]}' "
                f"처럼 어색하게 잘릴 수 있습니다(문장 끝을 스니펫 길이 안쪽으로 조정하면 개선됨)."
            )

    return SeoCheckResult(
        ok=len(warnings) == 0,
        snippet_preview=snippet_preview,
        summary_char_count=len(plain),
        warnings=warnings,
    )


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if "--run" not in sys.argv:
        print("사용법: python src/pipeline/seo_check.py --run <run_id>", file=sys.stderr)
        sys.exit(1)
    run_id = sys.argv[sys.argv.index("--run") + 1]

    result = check_meta_description(run_id)
    print(f"라이브 메타 description 예상 미리보기 ({len(result.snippet_preview)}/{SNIPPET_LENGTH}자):")
    print(f"  \"{result.snippet_preview}\"")
    print(f"요약 섹션 평문 길이: {result.summary_char_count}자")
    if result.warnings:
        for w in result.warnings:
            print(f"경고: {w}")
    else:
        print("SEO 메타 description 점검 통과 — 경고 없음")


if __name__ == "__main__":
    main()
