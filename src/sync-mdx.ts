import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { generatedRoot } from "./paths.js";
import { queryPublishedPages, retrievePageMarkdown } from "./publishers/notion.js";

function safeSlug(markdown: string, pageId: string): string {
  const title = markdown.match(/^#\s+(.+)$/m)?.[1] ?? pageId;
  const slug = title
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, "-");
  return slug || pageId.replaceAll("-", "");
}

function quoteYaml(value: string): string {
  return JSON.stringify(value);
}

export async function syncMdx(): Promise<number> {
  await mkdir(generatedRoot, { recursive: true });
  const pages = await queryPublishedPages();

  for (const page of pages) {
    const markdown = await retrievePageMarkdown(page.id);
    const title = markdown.match(/^#\s+(.+)$/m)?.[1] ?? page.id;
    const slug = safeSlug(markdown, page.id);
    const output = [
      "---",
      `title: ${quoteYaml(title)}`,
      `slug: ${quoteYaml(slug)}`,
      `notionPageId: ${quoteYaml(page.id)}`,
      `syncedAt: ${quoteYaml(new Date().toISOString())}`,
      "---",
      "",
      markdown,
      ""
    ].join("\n");
    await writeFile(path.join(generatedRoot, `${slug}.mdx`), output, "utf8");
  }
  return pages.length;
}

