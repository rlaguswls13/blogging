import type { BlogPublisher, ArticlePayload, PublishResult } from './base.js';

export type NotionPage = {
  id: string;
  properties?: Record<string, unknown>;
};

function notionHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "Notion-Version": process.env.NOTION_VERSION ?? "2026-03-11"
  };
}

async function notionRequest<T>(
  token: string,
  url: string,
  init: RequestInit = {}
): Promise<T> {
  const response = await fetch(`https://api.notion.com${url}`, {
    ...init,
    headers: { ...notionHeaders(token), ...(init.headers ?? {}) }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Notion API ${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

export class NotionPublisher implements BlogPublisher {
  readonly name = 'notion';

  private getCredentials() {
    const token = process.env.NOTION_WRITE_TOKEN;
    const parentId = process.env.NOTION_BLOG_PARENT_ID;
    if (!token || !parentId) {
      throw new Error("NOTION_WRITE_TOKEN과 NOTION_BLOG_PARENT_ID가 필요합니다.");
    }
    return { token, parentId };
  }

  async publish(article: ArticlePayload, dryRun: boolean): Promise<PublishResult> {
    const { token, parentId } = this.getCredentials();

    if (dryRun) {
      console.log(`[Notion Dry-Run] ${article.existingPostId ? '업데이트' : '신규 게시'}`);
      console.log(`[Notion Dry-Run] 제목: ${article.title}`);
      console.log(`[Notion Dry-Run] 마크다운 글자 수: ${article.markdownContent.length}자`);
      return {
        platform: this.name,
        postId: article.existingPostId || 'dry-run-notion-page-id',
        url: `https://notion.so/${article.existingPostId || 'dry-run-notion-page-id'}`,
        publishedAt: new Date().toISOString(),
      };
    }

    try {
      let pageId = article.existingPostId;
      if (pageId) {
        await notionRequest(token, `/v1/pages/${pageId}/markdown`, {
          method: "PATCH",
          body: JSON.stringify({
            type: "replace_content",
            replace_content: { new_str: article.markdownContent }
          })
        });
      } else {
        const parentType = process.env.NOTION_BLOG_PARENT_TYPE ?? "data_source";
        const titleProperty = process.env.NOTION_TITLE_PROPERTY ?? "Name";
        const statusProperty = process.env.NOTION_STATUS_PROPERTY ?? "Status";
        const publishedStatus = process.env.NOTION_PUBLISHED_STATUS ?? "Published";
        const parent =
          parentType === "page"
            ? { page_id: parentId }
            : { data_source_id: parentId };
        const properties =
          parentType === "page"
            ? undefined
            : {
                [titleProperty]: {
                  title: [{ text: { content: String(article.title) } }]
                },
                [statusProperty]: {
                  status: { name: publishedStatus }
                }
              };
        const page = await notionRequest<NotionPage>(token, "/v1/pages", {
          method: "POST",
          body: JSON.stringify({
            parent,
            ...(properties ? { properties } : {}),
            markdown: article.markdownContent
          })
        });
        pageId = page.id;
      }

      return {
        platform: this.name,
        postId: pageId,
        url: `https://notion.so/${pageId.replaceAll("-", "")}`,
        publishedAt: new Date().toISOString(),
      };
    } catch (error: any) {
      throw new Error(`Notion 게시 중 오류 발생: ${error.message || error}`);
    }
  }

  async validateAuth(): Promise<boolean> {
    try {
      const { token } = this.getCredentials();
      // Test basic connection to Notion by fetching users or search (using search with empty query is simple)
      const res = await fetch(`https://api.notion.com/v1/search`, {
        method: 'POST',
        headers: notionHeaders(token),
        body: JSON.stringify({ page_size: 1 })
      });
      return res.ok;
    } catch {
      return false;
    }
  }
}

// Below are read-only Notion client exports for sync-mdx.ts
export async function queryPublishedPages(): Promise<NotionPage[]> {
  const token = process.env.NOTION_READ_TOKEN;
  const dataSourceId = process.env.NOTION_BLOG_DATA_SOURCE_ID;
  if (!token || !dataSourceId) {
    throw new Error("NOTION_READ_TOKEN과 NOTION_BLOG_DATA_SOURCE_ID가 필요합니다.");
  }

  const pages: NotionPage[] = [];
  let cursor: string | undefined;
  do {
    const result = await notionRequest<{
      results: NotionPage[];
      has_more: boolean;
      next_cursor: string | null;
    }>(token, `/v1/data_sources/${dataSourceId}/query`, {
      method: "POST",
      body: JSON.stringify({
        page_size: 100,
        ...(cursor ? { start_cursor: cursor } : {})
      })
    });
    pages.push(...result.results.filter(isPublished));
    cursor = result.has_more ? result.next_cursor ?? undefined : undefined;
  } while (cursor);
  return pages;
}

function isPublished(page: NotionPage): boolean {
  const configured = (process.env.NOTION_PUBLISHED_STATUS ?? "Published").toLowerCase();
  for (const property of Object.values(page.properties ?? {})) {
    if (!property || typeof property !== "object") continue;
    const value = property as {
      status?: { name?: string };
      select?: { name?: string };
    };
    const name = value.status?.name ?? value.select?.name;
    if (name && [configured, "published", "게시", "게시됨"].includes(name.toLowerCase())) {
      return true;
    }
  }
  return false;
}

export async function retrievePageMarkdown(pageId: string): Promise<string> {
  const token = process.env.NOTION_READ_TOKEN;
  if (!token) throw new Error("NOTION_READ_TOKEN이 필요합니다.");
  const result = await notionRequest<{
    markdown: string;
    truncated: boolean;
    unknown_block_ids: string[];
  }>(token, `/v1/pages/${pageId}/markdown`);
  if (result.truncated || result.unknown_block_ids.length > 0) {
    throw new Error(`${pageId}: 잘리거나 읽을 수 없는 Notion 블록이 있습니다.`);
  }
  if (/<unknown\b/i.test(result.markdown)) {
    throw new Error(`${pageId}: MDX로 변환할 수 없는 unknown 블록이 있습니다.`);
  }
  return result.markdown;
}
