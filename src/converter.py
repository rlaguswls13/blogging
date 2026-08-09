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
        language = info.strip() if info else "plaintext"
        try:
            lexer = get_lexer_by_name(language, stripall=True)
        except ClassNotFound:
            lexer = get_lexer_by_name("plaintext", stripall=True)

        formatter = HtmlFormatter(nowrap=True)
        highlighted = highlight(code, lexer, formatter)

        return f'<pre><code class="hljs language-{language}">{highlighted}</code></pre>\n'

def convert_markdown_to_html(markdown_content: str) -> Dict[str, str]:
    # 0. Extract Fact Check and References sections before parsing
    fact_check_match = re.search(r"## 사실 검증 결과\s*(.*?)(?=##|\Z)", markdown_content, flags=re.MULTILINE | re.DOTALL)
    fact_check_content = fact_check_match.group(1).strip() if fact_check_match else ""

    references_match = re.search(r"## 참고문헌\s*(.*?)(?=##|\Z)", markdown_content, flags=re.MULTILINE | re.DOTALL)
    references_content = references_match.group(1).strip() if references_match else ""

    # Remove these sections from the main body content so they don't render normally
    markdown_content = re.sub(r"## 사실 검증 결과\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)
    markdown_content = re.sub(r"## 참고문헌\s*(.*?)(?=##|\Z)", "", markdown_content, flags=re.MULTILINE | re.DOTALL)

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
            headings.append({
                "text": text,
                "depth": depth,
                "slug": heading_to_slug(text)
            })

    # 2. Generate TOC HTML
    toc_html = ""
    if headings:
        toc_html += '<nav class="toc">\n  <div class="toc-title">목차</div>\n  <ul>\n'
        current_depth = 2

        for h in headings:
            if h["depth"] == 2:
                if current_depth == 3:
                    toc_html += '    </ul>\n  </li>\n'
                    current_depth = 2
                toc_html += f'    <li><a href="#{h["slug"]}">{h["text"]}</a>'
            elif h["depth"] == 3:
                if current_depth == 2:
                    toc_html += '\n    <ul>\n'
                    current_depth = 3
                toc_html += f'      <li><a href="#{h["slug"]}">{h["text"]}</a></li>\n'

        if current_depth == 3:
            toc_html += '    </ul>\n  </li>\n'
        else:
            toc_html += '</li>\n'

        toc_html += '  </ul>\n</nav>'

    # 3. Setup Custom Renderer
    renderer = CustomHTMLRenderer(escape=False)
    markdown_parser = mistune.create_markdown(renderer=renderer, plugins=['strikethrough', 'table'])

    # 4. Insert TOC into markdown
    markdown_with_toc = markdown_content
    toc_insertion_placeholder = '## 본문'
    if toc_insertion_placeholder in markdown_content and toc_html:
        markdown_with_toc = markdown_content.replace(
            toc_insertion_placeholder,
            f"## 목차\n\n{toc_html}\n\n## 본문"
        )

    html = markdown_parser(markdown_with_toc)

    # Convert fact check and references markdown to HTML separately
    fact_check_html = markdown_parser(fact_check_content) if fact_check_content else ""
    references_html = markdown_parser(references_content) if references_content else ""

    # Wrap collapsible blocks
    collapsible_html = ""
    if fact_check_html:
        collapsible_html += f"""
<details class="collapsible-section">
  <summary>🔍 사실 검증 결과 (클릭하여 열기)</summary>
  <div class="collapsible-content">
    {fact_check_html}
  </div>
</details>
"""
    if references_html:
        collapsible_html += f"""
<details class="collapsible-section">
  <summary>📚 참고문헌 (클릭하여 열기)</summary>
  <div class="collapsible-content">
    {references_html}
  </div>
</details>
"""

    # Load custom IT tech blog CSS style
    from src.paths import project_root
    css_path = project_root / "templates" / "blogger_post_style.css"
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
