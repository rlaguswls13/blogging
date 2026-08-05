import path from "node:path";
import { runDirectory } from "./paths.js";
import { readState, writeJson } from "./files.js";

export async function approveRun(runId: string): Promise<void> {
  const statePath = path.join(runDirectory(runId), "state.json");
  const state = await readState(statePath);
  if (state.status === "published") {
    throw new Error("이미 게시된 실행은 다시 승인할 수 없습니다.");
  }
  await writeJson(statePath, {
    ...state,
    status: "approved",
    humanApproved: true,
    updatedAt: new Date().toISOString()
  });
}

