import path from "node:path";

export const projectRoot = process.env.BLOGGING_ROOT
  ? path.resolve(process.env.BLOGGING_ROOT)
  : process.cwd();
export const runsRoot = path.join(projectRoot, "temp", "runs");
export const generatedRoot = path.join(projectRoot, "content", "generated");
export const gatePath = path.join(projectRoot, "config", "publish-gate.json");
export const articleTemplatePath = path.join(projectRoot, "templates", "article.md");
export const knowledgeGraphPath = path.join(projectRoot, "content", "knowledge-graph.json");

export function runDirectory(runId: string): string {
  if (!/^[a-zA-Z0-9_-]+$/.test(runId)) {
    throw new Error("run-id에는 영문, 숫자, 밑줄, 하이픈만 사용할 수 있습니다.");
  }
  return path.join(runsRoot, runId);
}
