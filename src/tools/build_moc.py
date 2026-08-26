"""
content/posts/<Category>/_MOC.md(Obsidian Map of Content) 재생성 유지보수 도구.

배경: 2026-08-23 content/posts/를 Basics/Advanced/ETC 카테고리 하위폴더로 재편(Obsidian
볼트 겸용)하면서, 각 카테고리 안에서 글들이 실제로 어떻게 서로 백링크돼 있는지 한눈에 보는
MOC을 요청받았다. 순수 그래프 연결성(connected components)으로 클러스터링을 시도했으나
실패했다 — 이 블로그는 이미 상당히 촘촘하게 상호 연결돼 있어(내부링크 품질 작업의 자연스러운
결과) 소수의 다리 노드만 거치면 전체가 하나의 거대 컴포넌트로 뭉개진다. 그래서 그래프 병합
대신 각 글의 실제 frontmatter tags 중 그 카테고리 안에서 가장 많은 글과 공유되는 태그를 그룹
키로 쓴다(표제를 새로 짓지 않고 이미 있는 tags 그대로 사용). 화살표는 그룹 경계와 무관하게
각 글의 실제 '## 백링크' 섹션(라이브 URL)을 파싱한 결과이며, 관계 자체를 그룹 안으로 제한하지
않는다. gof-14처럼 지나치게 많이 인용되는(in-degree>=10) 인덱스성 허브 글은 일반 그룹 형성용
엣지에서 제외하고 별도 "허브" 섹션으로 분리한다(안 그러면 gof-14 하나가 무관한 클러스터끼리
다리를 놓아버림).

사용법:
  python src/tools/build_moc.py

새 글을 발행하거나 기존 글의 '## 백링크'를 수정한 뒤 재실행하면 3개 _MOC.md 파일을 덮어쓴다
(수동 편집하지 말 것 — 다음 재생성에서 사라진다). all_post_paths()가 파일명이 '_'로 시작하는
파일(_MOC.md 자신 등)을 이미 제외하므로 반복 실행해도 자기참조 버그가 생기지 않는다.
"""

import os
import re
import sys
from collections import defaultdict, Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import frontmatter

from src.core.paths import posts_root, POST_CATEGORIES, all_post_paths

CATEGORY_TAGS = {"Basics", "Advanced", "ETC"}
HUB_THRESHOLD = 10


def extract_section(body, heading):
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##(?!#)|\Z)", re.MULTILINE | re.DOTALL)
    m = pattern.search(body)
    return m.group(1) if m else ""


def build_moc():
    posts = {}  # slug -> {title, url, category, tags, content}
    url_to_slug = {}

    for path in all_post_paths():
        post = frontmatter.load(path)
        meta = post.metadata
        slug = meta.get("slug") or path.stem
        category = path.parent.name
        posts[slug] = {
            "title": meta.get("title", slug),
            "url": meta.get("url", ""),
            "category": category,
            "tags": [t for t in meta.get("tags", []) if isinstance(t, str)],
            "content": post.content,
        }
        if meta.get("url"):
            url_to_slug[meta["url"].rstrip("/")] = slug

    edges = defaultdict(set)  # slug -> set of linked slugs (## 백링크 파싱 결과)
    for slug, data in posts.items():
        backlink_section = extract_section(data["content"], "백링크")
        # 비탐욕 .*? — 링크 텍스트(글 제목)에 GoF 시리즈처럼 대괄호가 포함된 경우도 매칭.
        urls = re.findall(r"\[.*?\]\((https?://[^)]+)\)", backlink_section)
        for u in urls:
            target_slug = url_to_slug.get(u.rstrip("/"))
            if target_slug and target_slug != slug:
                edges[slug].add(target_slug)

    indeg = Counter()
    for _src, targets in edges.items():
        for t in targets:
            indeg[t] += 1
    hubs = {slug for slug, n in indeg.items() if n >= HUB_THRESHOLD}

    hub_citers = {h: set() for h in hubs}
    for src, targets in edges.items():
        for t in targets:
            if t in hubs:
                hub_citers[t].add(src)

    isolated = [
        slug for slug in posts
        if slug not in hubs and not edges.get(slug) and not any(slug in hub_citers[h] for h in hubs)
        and not any(slug in targets for targets in edges.values())
    ]

    by_category_posts = defaultdict(list)
    for slug, data in posts.items():
        if slug not in hubs:
            by_category_posts[data["category"]].append(slug)

    for category in POST_CATEGORIES:
        lines = [
            f"# {category} — Backlink MOC\n",
            "글 본문 `## 백링크` 섹션(실제 라이브 URL)을 파싱해 자동 생성했습니다. 그룹 표제는 각 글의 "
            "실제 `tags`에서 가져온 것이며, 화살표는 백링크 방향(A → B: A의 본문이 B를 인용)입니다. "
            "다시 생성하려면 `python src/tools/build_moc.py`를 재실행하세요"
            "(수동 편집 시 다음 재생성에서 덮어써집니다).\n",
        ]

        cat_slugs = [s for s in by_category_posts.get(category, []) if s not in isolated]
        tag_freq = Counter()
        for slug in cat_slugs:
            for t in posts[slug]["tags"]:
                if t not in CATEGORY_TAGS:
                    tag_freq[t] += 1

        def primary_tag(slug, _tag_freq=tag_freq):
            cand = [t for t in posts[slug]["tags"] if t not in CATEGORY_TAGS]
            if not cand:
                return None
            return max(cand, key=lambda t: (_tag_freq[t], t))

        groups = defaultdict(list)
        for slug in cat_slugs:
            key = primary_tag(slug) or "기타"
            groups[key].append(slug)

        sorted_groups = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        for label, members in sorted_groups:
            lines.append(f"## {label}\n")
            for slug in sorted(members, key=lambda s: -len(edges.get(s, set()))):
                data = posts[slug]
                lines.append(f"- [[{slug}|{data['title']}]]")
                for t in sorted(edges.get(slug, set())):
                    tdata = posts[t]
                    tcat_note = "" if tdata["category"] == category else f" *({tdata['category']})*"
                    hub_note = " *(허브)*" if t in hubs else ""
                    lines.append(f"  - → [[{t}|{tdata['title']}]]{tcat_note}{hub_note}")
            lines.append("")

        cat_hubs = [h for h in hubs if posts[h]["category"] == category]
        for h in sorted(cat_hubs, key=lambda h: -len(hub_citers[h])):
            citers = sorted(hub_citers[h], key=lambda s: posts[s]["title"])
            lines.append(f"## 🔗 허브: {posts[h]['title']} ({len(citers)}개 글이 참조)\n")
            lines.append(f"- [[{h}|{posts[h]['title']}]]")
            for c in citers:
                cdata = posts[c]
                ccat_note = "" if cdata["category"] == category else f" *({cdata['category']})*"
                lines.append(f"  - ← [[{c}|{cdata['title']}]]{ccat_note}")
            lines.append("")

        iso = sorted(
            [s for s in isolated if posts[s]["category"] == category],
            key=lambda s: posts[s]["title"],
        )
        if iso:
            lines.append("## 미연결 (백링크 없음 또는 아직 대상 없음)\n")
            for slug in iso:
                lines.append(f"- [[{slug}|{posts[slug]['title']}]]")
            lines.append("")

        out_path = posts_root / category / "_MOC.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"{category}: 태그 그룹 {len(sorted_groups)}개, 허브 {len(cat_hubs)}개, 미연결 {len(iso)}개 -> {out_path}")

    print(f"\n총 엣지 {sum(len(v) for v in edges.values())}개, 허브 {len(hubs)}개({', '.join(sorted(hubs))}), 미연결 {len(isolated)}개")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    build_moc()
