import re
import unicodedata
from typing import Dict
import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

def heading_to_slug(text: str) -> str:
    clean_text = re.sub(r"<[^>]+>", "", text)
    normalized = unicodedata.normalize("NFKD", clean_text)
    # Alphanumeric character matching (including Unicode letters like Korean)
    cleaned = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[\s_]+", "-", cleaned)
    slug = re.sub(r"-+", "-", slug)
    return slug

class CustomHTMLRenderer(mistune.HTMLRenderer):
    def heading(self, text, level, **attrs):
        slug = heading_to_slug(text)
        return f'<h{level} id="{slug}">{text}</h{level}>\n'

    def block_code(self, code, info=None, **attrs):
        language = info.strip() if info else "text"
        if language == "mermaid":
            # Wrap in a clean div with class 'mermaid' for client-side rendering
            return f'<div class="mermaid">\n{code}\n</div>\n'
            
        try:
            lexer = get_lexer_by_name(language, stripall=True)
        except ClassNotFound:
            lexer = get_lexer_by_name("text", stripall=True)

        formatter = HtmlFormatter(nowrap=True)
        highlighted = highlight(code, lexer, formatter)

        return f'<pre><code class="hljs language-{language}">{highlighted}</code></pre>\n'

def restyle_references(text: str) -> str:
    """Reshape "## 참고문헌" list items for readability: hyperlink the quoted title itself
    (instead of also printing the raw URL as separate visible text) and shrink the trailing
    "(확인일: YYYY-MM-DD)" access-date note into a small subscript.

    Processes line-by-line (each reference is one line) in two passes so it's safe across the
    inconsistent formats already written by past sessions (bare URL, `[url](url)`, or — for 3
    TLS-post entries — date-before-URL order): pass 1 always wraps the access-date (present
    verbatim in every entry, so this alone is a safe universal improvement); pass 2 then looks
    for a URL sitting right before/after that now-wrapped date note and, only when the line has
    exactly one quoted span (so "the title" is unambiguous) and the shape matches cleanly, moves
    the URL onto the title as the link target and drops the bare URL text. Lines with zero or
    multiple quoted spans (e.g. a citation with a nested quoted sub-title) simply fall through
    pass 2 unchanged — still date-restyled, just not title-linked, rather than risk linking the
    wrong quoted span (2026-08-23, requested after several inconsistent generations here).

    Must run on text that has already gone through linkify_markdown() (as it does inside
    convert_markdown_to_html), which turns a bare URL into a `<url>` autolink — so the URL
    alternation below matches that form too, not just `[url](url)` or a raw bare URL.
    """
    date_tag = r'<sub class="ref-date">\(확인일:\s*[\d\-]+\)</sub>'
    # One URL, in any of the three shapes it may already be in by this point: markdown link
    # `[url](url)`, autolink `<url>` (what linkify_markdown produces from a bare URL), or bare.
    url_alt = (
        r'(?:\[(?P<url_b>https?://[^\]]+)\]\(https?://[^\)]+\)'
        r'|<(?P<url_c>https?://[^>\s]+)>'
        r'|(?P<url_a>https?://[^\s\)\]>]+))'
    )

    def _url_from(m):
        return m.group("url_a") or m.group("url_b") or m.group("url_c")

    def _restyle_line(line):
        # Count quotes before pass 1 injects its own (class="ref-date" would otherwise miscount).
        has_single_quoted_title = line.count('"') == 2

        # Pass 1: universally shrink the access-date note, regardless of URL position/format.
        line = re.sub(
            r"\(확인일:\s*([\d\-]+)\)",
            r'<sub class="ref-date">(확인일: \1)</sub>',
            line,
        )

        if not has_single_quoted_title:
            return line  # ambiguous or no quoted title on this line — leave URL placement as-is

        # Pass 2a: normal order — "Title"<short trailing text>URL <date-tag>
        def _repl_normal(m):
            title, between = m.group("title"), m.group("between").rstrip()
            return f'"[{title}]({_url_from(m)})"{between} {m.group("date")}'

        new_line = re.sub(
            r'"(?P<title>[^"]+)"(?P<between>[^<>\n]{0,80}?)\s*' + url_alt
            + r'\s*(?P<date><sub class="ref-date">\(확인일:\s*[\d\-]+\)</sub>)',
            _repl_normal,
            line,
        )
        if new_line != line:
            return new_line

        # Pass 2b: reversed order (a few TLS-post entries) — "Title" <date-tag> — URL
        def _repl_reversed(m):
            return f'"[{m.group("title")}]({_url_from(m)})" {m.group("date")}'

        return re.sub(
            r'"(?P<title>[^"]+)"\s*(?P<date>' + date_tag + r')\s*[—-]\s*' + url_alt,
            _repl_reversed,
            line,
        )

    return "\n".join(_restyle_line(line) for line in text.split("\n"))

def linkify_markdown(content: str) -> str:
    """Wrap bare http(s) URLs in `<...>` (markdown autolink syntax) so they render as clickable <a> tags.

    Skips code blocks, and skips URLs already inside markdown link/image syntax — both the target
    position `](URL)` and the link-text position `[URL]` (e.g. `[https://x](https://x)`, which several
    already-published posts use for bare-URL references). Without the `[URL]` exclusion, that second
    case gets double-wrapped into `[<https://x>](https://x)`, which mistune fails to parse as a link
    and instead leaks literal `%5D(` / bracket text into the live HTML (found 2026-08-23 auditing
    already-published posts for stale link rendering).
    """
    parts = content.split("```")
    for i in range(len(parts)):
        if i % 2 == 0:  # Non-code block
            pattern = r'(?<!\]\()(?<!\[)(?<!href=")(?<!src=")(?<!<)https?://[^\s\)\>\]]+'
            parts[i] = re.sub(pattern, lambda m: f"<{m.group(0)}>", parts[i])
    return "```".join(parts)

def convert_markdown_to_html(markdown_content: str) -> Dict[str, str]:
    # 0a. Clean up CLAIM and SOURCE citation tags into scientific brackets format [1], [2]
    markdown_content = re.sub(r'\[CLAIM-\d+\]:\s*', '', markdown_content)
    markdown_content = re.sub(r'\[CLAIM-\d+\]', '', markdown_content)

    # 0a-2. Auto-linkify bare URLs so they render as <a> tags — must run for every caller of this
    # function (publish, republish/maintenance tools, previews), not just the main publish path, so
    # this lives here instead of in src/publishers (2026-08-23: found several already-published posts
    # where maintenance tools that called this function directly skipped linkification entirely).
    markdown_content = linkify_markdown(markdown_content)
    
    # 0b. Detect local images, copy them to content/images, and convert paths to GitHub CDN URL
    from src.core.paths import project_root
    from pathlib import Path
    import os
    import shutil
    import urllib.parse
    
    images_dest_dir = project_root / "content" / "images"
    os.makedirs(images_dest_dir, exist_ok=True)
    
    def replace_image_path(match):
        alt_text = match.group(1)
        original_path = match.group(2).strip()
        
        clean_path = original_path
        if clean_path.startswith("file:///"):
            clean_path = clean_path[8:]
        elif clean_path.startswith("file://"):
            clean_path = clean_path[7:]
            
        # Decode url-encoded paths
        clean_path = urllib.parse.unquote(clean_path)
        clean_path = clean_path.replace("/", os.sep)
        path_obj = Path(clean_path)
        
        if path_obj.exists() and path_obj.is_file():
            filename = path_obj.name
            target_dest = images_dest_dir / filename
            
            try:
                # Copy file only if modified or not exists
                if not target_dest.exists() or target_dest.stat().st_mtime < path_obj.stat().st_mtime:
                    shutil.copy2(path_obj, target_dest)
                    print(f"[Image Copier] 복사 완료: {path_obj.name} -> content/images/")
            except Exception as e:
                print(f"[Image Copier] 복사 실패: {e}")
                
            github_cdn_url = f"https://raw.githubusercontent.com/rlaguswls13/blogging/main/content/images/{filename}"
            return f"![{alt_text}]({github_cdn_url})"
            
        return match.group(0)

    markdown_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image_path, markdown_content)
    
    def replace_citation(match):
        content = match.group(1)
        sources = re.findall(r'SOURCE-(\d+)', content)
        if not sources:
            return match.group(0)
        return ", ".join(f"[{int(s)}]" for s in sources)

    markdown_content = re.sub(r'\((?:인용|근거):\s*(SOURCE-\d+(?:\s*,\s*SOURCE-\d+)*)\)', replace_citation, markdown_content)
    markdown_content = re.sub(r'SOURCE-(\d+)', lambda m: f"[{int(m.group(1))}]", markdown_content)

    # 0b. Extract References and Backlinks sections, remove internal-only sections before parsing
    references_match = re.search(r"## 참고문헌\s*(.*?)(?=##|\Z)", markdown_content, flags=re.MULTILINE | re.DOTALL)
    references_content = restyle_references(references_match.group(1).strip()) if references_match else ""

    # 백링크는 삭제하지 않고 별도 렌더링한다(아래 "관련 글" 블록) — 과거엔 그냥 삭제되어 내부링크가
    # 라이브 페이지에 한 번도 실제로 렌더링된 적이 없었다(SEO 내부링크 신호 손실 버그, 2026-08-22 수정).
    backlinks_match = re.search(r"## 백링크\s*(.*?)(?=##|\Z)", markdown_content, flags=re.MULTILINE | re.DOTALL)
    backlinks_content = backlinks_match.group(1).strip() if backlinks_match else ""

    # Remove these internal-only sections from the main body content so they don't render normally
    markdown_content = re.sub(r"## 사실 검증 결과\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)
    markdown_content = re.sub(r"## 차별화 포인트\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)
    markdown_content = re.sub(r"## 참고문헌\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)
    markdown_content = re.sub(r"## 백링크\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)
    markdown_content = re.sub(r"## 관련 세션\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)
    # 꼬리질문(내부 검토용 후속 질문 체크리스트)도 내부 전용 섹션 — 과거엔 publish_to_multi()에서만
    # 임시로 strip해서, 이 함수를 직접 호출하는 유지보수 도구(update_post_content.py 등)로 재게시하면
    # 라이브 페이지에 그대로 노출되는 버그가 있었다(2026-08-23 발견).
    markdown_content = re.sub(r"## 꼬리질문\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)

    # 0b. Replace duplicate main title heading # [Title] with <h2 class="post-body-title">[Summary Title]</h2>
    main_title_match = re.search(r"^#\s+(.+)$", markdown_content, flags=re.MULTILINE)
    if main_title_match:
        full_title = main_title_match.group(1).strip()
        summary_title = full_title
        for delimiter in [":", " - ", " – ", " — "]:
            if delimiter in summary_title:
                summary_title = summary_title.split(delimiter)[0].strip()
                break
        
        # We replace the first '# Title' line with raw HTML <h2> so it's not matched in markdown TOC list
        title_html = f'<h2 class="post-body-title">{summary_title}</h2>\n'
        markdown_content = re.sub(r"^#\s+.+$", title_html, markdown_content, count=1, flags=re.MULTILINE)

    # 1. Parse headings to build TOC
    lines = markdown_content.split('\n')
    headings = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        match = re.match(r"^(#{2,3})\s+(.+)$", line)
        if match:
            depth = len(match.group(1))
            text = match.group(2).strip()
            # Skip metadata headings to prevent duplicate TOC links
            if text in ['요약', '목차', '본문', '참고문헌', '백링크', '작성자의 견해', '한계와 반론', '종합적 의견', '사실 검증 결과']:
                continue
            headings.append({
                "text": text,
                "depth": depth,
                "slug": heading_to_slug(text)
            })

    # 2. Generate TOC HTML
    toc_html = ""
    if headings:
        toc_html += '<details class="toc-details" open="open">\n<summary class="toc-summary">목차</summary>\n<nav class="toc">\n<ul>\n'
        current_depth = 2

        for h in headings:
            if h["depth"] == 2:
                if current_depth == 3:
                    toc_html += '</ul>\n</li>\n'
                    current_depth = 2
                toc_html += f'<li><a href="#{h["slug"]}">{h["text"]}</a>'
            elif h["depth"] == 3:
                if current_depth == 2:
                    toc_html += '\n<ul>\n'
                    current_depth = 3
                toc_html += f'<li><a href="#{h["slug"]}">{h["text"]}</a></li>\n'

        if current_depth == 3:
            toc_html += '</ul>\n</li>\n'
        else:
            toc_html += '</li>\n'

        toc_html += '</ul>\n</nav>\n</details>'

    # 3. Setup Custom Renderer
    renderer = CustomHTMLRenderer(escape=False)
    markdown_parser = mistune.create_markdown(renderer=renderer, plugins=['strikethrough', 'table'])

    # 4. Insert TOC into markdown
    markdown_with_toc = markdown_content
    toc_insertion_placeholder = '## 본문'
    if toc_insertion_placeholder in markdown_content and toc_html:
        markdown_with_toc = markdown_content.replace(
            toc_insertion_placeholder,
            f"{toc_html}\n\n## 본문"
        )

    html = markdown_parser(markdown_with_toc)

    # Convert references markdown to HTML
    references_html = markdown_parser(references_content) if references_content else ""

    # Wrap references in collapsible details block
    collapsible_html = ""
    if references_html:
        collapsible_html += f"""
<details class="collapsible-section">
  <summary>📚 참고문헌 (클릭하여 열기)</summary>
  <div class="collapsible-content">
    {references_html}
  </div>
</details>
"""

    # Convert backlinks markdown to HTML and render as a visible "관련 글" block
    # (접힌 콘텐츠가 아니라 본문 흐름에 노출시켜 실제 내부링크 신호로 작동하게 한다)
    backlinks_html = markdown_parser(backlinks_content) if backlinks_content else ""
    if backlinks_html:
        collapsible_html += f"""
<div class="related-posts-section">
  <h3>🔗 관련 글</h3>
  {backlinks_html}
</div>
"""

    # Load custom IT tech blog CSS style
    from src.core.paths import project_root, theme_css_path
    css_path = theme_css_path
    custom_css = ""
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            custom_css = f.read()

    # Load Pygments monokai styles for code blocks
    pygments_css = HtmlFormatter(style='monokai').get_style_defs('.hljs')

    # Wrap in scoped container and inject styles
    wrapped_html = f"""<div class="tech-blog-post">
<style>
{custom_css}
{pygments_css}
</style>
{html}
{collapsible_html}
</div>"""

    return {
        "html": wrapped_html,
        "tocHtml": toc_html
    }
