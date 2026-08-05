import { Marked, Renderer } from 'marked';
import hljs from 'highlight.js';

function headingToSlug(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\p{L}\p{N}\s-]/gu, "") // Preserves Korean, English, and other Unicode letters/numbers
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-");
}

export interface ConvertedArticle {
  html: string;
  tocHtml: string;
}

export async function convertMarkdownToHtml(markdown: string): Promise<ConvertedArticle> {
  // 1. Parse headings to build TOC
  // We look for markdown headings of depth 2 and 3: e.g., "## Title" or "### Title"
  // But we exclude frontmatter or headings inside code blocks. A simple line-by-line check is usually safe.
  const lines = markdown.split('\n');
  const headings: { text: string; depth: number; slug: string }[] = [];
  let inCodeBlock = false;

  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) continue;

    const match = line.match(/^(#{2,3})\s+(.+)$/);
    if (match) {
      const depth = match[1].length;
      const text = match[2].trim();
      // Skip required sections that are metadata/system level if desired, or include them.
      // Let's include everything except maybe "요약" or "참고문헌" depending on preference,
      // but standard tech blogs include all main headings.
      headings.push({
        text,
        depth,
        slug: headingToSlug(text)
      });
    }
  }

  // 2. Generate TOC HTML
  let tocHtml = '';
  if (headings.length > 0) {
    tocHtml += '<nav class="toc">\n  <div class="toc-title">목차</div>\n  <ul>\n';
    let currentDepth = 2;

    for (const h of headings) {
      if (h.depth === 2) {
        if (currentDepth === 3) {
          tocHtml += '    </ul>\n  </li>\n';
          currentDepth = 2;
        }
        tocHtml += `    <li><a href="#${h.slug}">${h.text}</a>`;
      } else if (h.depth === 3) {
        if (currentDepth === 2) {
          tocHtml += '\n    <ul>\n';
          currentDepth = 3;
        }
        tocHtml += `      <li><a href="#${h.slug}">${h.text}</a></li>\n`;
      }
    }
    if (currentDepth === 3) {
      tocHtml += '    </ul>\n  </li>\n';
    } else {
      tocHtml += '</li>\n';
    }
    tocHtml += '  </ul>\n</nav>';
  }

  // 3. Setup custom marked renderer
  const renderer = new Renderer();

  // Custom code renderer with highlight.js syntax highlighting
  renderer.code = function({ text, lang }) {
    const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
    const highlighted = hljs.highlight(text, { language }).value;
    return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>\n`;
  };

  // Custom heading renderer to inject matching slugs as IDs
  renderer.heading = function({ text, depth }) {
    const slug = headingToSlug(text);
    return `<h${depth} id="${slug}">${text}</h${depth}>\n`;
  };

  // Create a clean instance of marked
  const markedInstance = new Marked({ renderer });

  // 4. Insert TOC into markdown
  // We insert the TOC right before the "## 본문" section if it exists, otherwise at the top of the body.
  let markdownWithToc = markdown;
  const tocInsertionPlaceholder = '## 본문';
  if (markdown.includes(tocInsertionPlaceholder) && tocHtml) {
    markdownWithToc = markdown.replace(
      tocInsertionPlaceholder,
      `## 목차\n\n${tocHtml}\n\n## 본문`
    );
  }

  const html = await markedInstance.parse(markdownWithToc);

  return {
    html,
    tocHtml
  };
}
