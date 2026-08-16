"""
사실 검증(fact-check)이 형식적으로(rubber-stamp) 이루어지고 있지 않은지 가시화하는
읽기 전용 리포트 도구.

배경: 2026-08-17 파이프라인 완성도 점검 중 최근 temp/runs/*/final.md 표본을 확인한
결과 예외 없이 factCheckScore: 1.0, 모든 CLAIM이 verified였다. 이 도구는 게이트를
막지 않는다 — self-report 점수라 강제해도 다시 1.0으로 조작되기 쉽고, 실제로 꼼꼼히
검증했을 가능성도 있어 우선은 통계로 드러내는 것이 우선이다.
남아있는 temp/runs/의 원본 실행 폴더만 대상으로 한다(content/posts/*.md는 발행 시
사실 검증 결과 섹션이 제거되어 이 정보가 남아있지 않다).

사용법:
  python src/tools/report_fact_check_stats.py
"""

import re
import sys
from pathlib import Path

import frontmatter

RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "temp" / "runs"

VERDICT_PATTERN = re.compile(r"\|\s*(verified|unverified|contradicted)\s*\|", re.IGNORECASE)


def find_final_md_files():
    if not RUNS_DIR.exists():
        return []
    return sorted(RUNS_DIR.glob("*/final.md"))


def analyze(path: Path):
    text = path.read_text(encoding="utf-8")
    post = frontmatter.loads(text)
    score = post.metadata.get("factCheckScore")

    match = re.search(r"^##\s+사실\s*검증\s*결과\s*$(.*?)(?=^##(?!#)|\Z)", post.content, re.MULTILINE | re.DOTALL)
    section = match.group(1) if match else ""

    verdicts = [v.lower() for v in VERDICT_PATTERN.findall(section)]
    return {
        "run": path.parent.name,
        "score": score,
        "verified": verdicts.count("verified"),
        "unverified": verdicts.count("unverified"),
        "contradicted": verdicts.count("contradicted"),
        "total_claims": len(verdicts),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    files = find_final_md_files()
    if not files:
        print("temp/runs/ 아래에 남아있는 final.md가 없습니다.")
        return

    rows = [analyze(p) for p in files]

    print(f"{'run':<16}{'score':>7}{'verified':>10}{'unverified':>12}{'contradicted':>14}{'total':>8}")
    all_100_verified = 0
    for r in rows:
        print(
            f"{r['run']:<16}{str(r['score']):>7}{r['verified']:>10}{r['unverified']:>12}"
            f"{r['contradicted']:>14}{r['total_claims']:>8}"
        )
        if r["total_claims"] > 0 and r["unverified"] == 0 and r["contradicted"] == 0 and r["score"] == 1.0:
            all_100_verified += 1

    print()
    print(f"총 {len(rows)}개 run 중 {all_100_verified}개가 '모든 claim verified + score 1.0' 패턴입니다.")
    if len(rows) > 0 and all_100_verified == len(rows):
        print("경고: 표본 전체가 예외 없이 100% verified입니다. rubber-stamp 검증 여부를 점검해 보세요.")
        print("(wiki/Blog_Writing_Rules.md 12번 수칙: CLAIM 판정은 실제 원문 대조로 수행할 것)")


if __name__ == "__main__":
    main()
