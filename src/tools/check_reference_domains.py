"""
참고문헌 URL을 validate.py의 TRUSTED_REFERENCE_DOMAINS와 즉석에서 대조하는 작성 보조 도구.

배경: validate.py의 reference_credibility_tier 체크가 2026-08-22부터 warning에서 error로
승격됐다(wiki/Blog_Writing_Rules.md 10번 수칙) — 참고문헌 전체가 신뢰 도메인과 하나도 안 겹치면
발행이 막힌다. 리서치 중에 후보 URL들을 이 도구로 먼저 확인하면, `## 참고문헌`을 다 채운 뒤
`validate` 단계에서야 발견해 다시 리서치하러 돌아가는 왕복을 줄일 수 있다.

이 스크립트는 src/pipeline/validate.py의 TRUSTED_REFERENCE_DOMAINS를 그대로 import해서 쓴다 —
목록을 여기 따로 복제하지 않는다(단일 소스 유지).

사용법:
  python src/tools/check_reference_domains.py <url1> [url2] ...
  python src/tools/check_reference_domains.py --file <참고문헌 URL 목록 텍스트 파일, 줄당 1개>
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
from src.pipeline.validate import TRUSTED_REFERENCE_DOMAINS  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--file", help="줄당 URL 1개인 텍스트 파일")
    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        urls += [line.strip() for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip()]

    if not urls:
        print("오류: URL을 하나 이상 인자로 주거나 --file을 지정하세요.", file=sys.stderr)
        sys.exit(1)

    any_trusted = False
    for url in urls:
        domain = urlparse(url).netloc
        trusted = domain in TRUSTED_REFERENCE_DOMAINS
        any_trusted = any_trusted or trusted
        print(f"{'PASS' if trusted else 'MISS'}: {domain or '(도메인 파싱 실패)'} — {url}")

    print()
    if any_trusted:
        print("결과: 신뢰 도메인 1개 이상 포함 — reference_credibility_tier 게이트 통과 예상.")
    else:
        print("결과: 전부 비신뢰 도메인 — 게이트 차단됨. Tier1/2 공식 문서를 최소 1개 추가하거나,")
        print("정말 공식 도메인인데 목록 누락이면 src/pipeline/validate.py의")
        print("TRUSTED_REFERENCE_DOMAINS에 추가할 것.")
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
