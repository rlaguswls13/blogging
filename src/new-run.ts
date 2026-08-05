import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { articleTemplatePath, runDirectory } from "./paths.js";
import { writeJson } from "./files.js";
import type { RunState } from "./types.js";

function makeRunId(now: Date): string {
  return now.toISOString().replace(/\D/g, "").slice(0, 14);
}

function slugify(value: string): string {
  const ascii = value
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-");
  return ascii || `article-${Date.now()}`;
}

export async function createRun(topic: string): Promise<string> {
  const now = new Date();
  const runId = makeRunId(now);
  const dir = runDirectory(runId);
  await mkdir(dir, { recursive: false });

  const articleId = `article-${runId}`;
  const iso = now.toISOString();
  const state: RunState = {
    runId,
    articleId,
    topic,
    status: "created",
    humanApproved: false,
    notionPageId: null,
    createdAt: iso,
    updatedAt: iso
  };

  await writeJson(path.join(dir, "state.json"), state);
  await writeFile(
    path.join(dir, "request.md"),
    `# 블로그 작성 요청\n\n## 요청 주제\n\n${topic}\n\n## 생성 시각\n\n${iso}\n`,
    "utf8"
  );

  const template = await readFile(articleTemplatePath, "utf8");
  await writeFile(
    path.join(dir, "article-template.md"),
    template
      .replaceAll("{{articleId}}", articleId)
      .replaceAll("{{title}}", topic)
      .replaceAll("{{slug}}", slugify(topic))
      .replaceAll("{{createdAt}}", iso),
    "utf8"
  );

  return runId;
}

