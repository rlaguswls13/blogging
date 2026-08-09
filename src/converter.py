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
    # escape=False is used because we want raw HTML preservation if markdown has HTML elements.
    renderer = CustomHTMLRenderer(escape=False)
    # Enable common extensions like table and strikethrough
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
</div>"""

    return {
        "html": wrapped_html,
        "tocHtml": toc_html
    }
