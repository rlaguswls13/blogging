import "dotenv/config";
import { createRun } from "./new-run.js";
import { requiredFlag, hasFlag, readFlag } from "./args.js";
import { validateRun } from "./validate.js";
import { publishToMulti } from "./publishers/index.js";
import { syncMdx } from "./sync-mdx.js";
import { approveRun } from "./approve.js";
import { getTodos, loadKnowledgeGraph } from "./knowledge-store.js";

async function main(): Promise<void> {
  const [, , command, ...args] = process.argv;

  if (command === "new") {
    const runId = await createRun(requiredFlag(args, "topic"));
    console.log(`새 실행 생성: ${runId}`);
    console.log(`경로: temp/runs/${runId}`);
    return;
  }

  if (command === "validate") {
    const result = await validateRun(
      requiredFlag(args, "run"),
      !hasFlag(args, "preflight")
    );
    for (const warning of result.warnings) console.warn(`경고: ${warning}`);
    if (!result.ok) {
      for (const error of result.errors) console.error(`오류: ${error}`);
      process.exitCode = 1;
      return;
    }
    console.log("게시 게이트 통과");
    return;
  }

  if (command === "approve") {
    const runId = requiredFlag(args, "run");
    await approveRun(runId);
    console.log(`사람 승인 기록 완료: ${runId}`);
    return;
  }

  if (command === "publish") {
    const runId = requiredFlag(args, "run");
    const platformStr = readFlag(args, "platform") ?? "notion";
    const platforms = platformStr.split(",") as any[];
    await publishToMulti(runId, platforms, hasFlag(args, "dry-run"));
    console.log(hasFlag(args, "dry-run") ? "dry-run 완료" : "멀티 플랫폼 게시 완료");
    return;
  }

  if (command === "sync") {
    const count = await syncMdx();
    console.log(`${count}개의 Notion 페이지를 MDX로 생성했습니다.`);
    return;
  }

  if (command === "todo") {
    const status = readFlag(args, "status") as any;
    const todos = await getTodos(status);
    console.log(`--- 꼬리질문 TODO 목록 (${status || '전체'}) ---`);
    if (todos.length === 0) {
      console.log("미완료된 꼬리질문이 없습니다.");
    } else {
      for (const item of todos) {
        console.log(`[${item.todo.status.toUpperCase()}] ID: ${item.todo.id}`);
        console.log(`  질문: ${item.todo.question}`);
        console.log(`  출처 글: ${item.topic} (ID: ${item.articleId})`);
        if (item.todo.suggestedUrls.length > 0) {
          console.log(`  추천 URL: ${item.todo.suggestedUrls.join(', ')}`);
        }
        if (item.todo.linkedArticleId) {
          console.log(`  연결된 글 ID: ${item.todo.linkedArticleId}`);
        }
        console.log('');
      }
    }
    return;
  }

  if (command === "backlinks") {
    const graph = await loadKnowledgeGraph();
    const runId = requiredFlag(args, "run");
    const targetArticleId = `article-${runId}`;
    const node = graph.nodes.find(n => n.articleId === targetArticleId);
    
    if (!node) {
      console.error(`지식 그래프에서 글을 찾을 수 없습니다: ${targetArticleId}`);
      process.exitCode = 1;
      return;
    }
    
    console.log(`--- [${node.topic}] 백링크 정보 ---`);
    console.log(`등록 시각: ${node.createdAt}`);
    console.log(`\n[인용된 참고문헌]`);
    for (const r of node.references) {
      console.log(`- ${r.title} (${r.url})`);
    }
    
    console.log(`\n[설정된 백링크]`);
    if (node.backlinks.length === 0) {
      console.log("설정된 백링크가 없습니다.");
    } else {
      for (const b of node.backlinks) {
        console.log(`- From: ${b.fromArticleId} -> To: ${b.toArticleId} (앵커: "${b.anchor}")`);
      }
    }
    return;
  }

  throw new Error("사용법: new | validate | approve | publish | sync | todo | backlinks");
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
