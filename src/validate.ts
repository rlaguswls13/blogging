import { readFile } from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import { ArticleFrontmatterSchema, PublishGateSchema } from "./types.js";
import { gatePath, runDirectory } from "./paths.js";
import { readJson, readState } from "./files.js";

export type ValidationResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

function sectionExists(body: string, heading: string): boolean {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`^##\\s+${escaped}\\s*$`, "m").test(body);
}

function referenceCount(body: string): number {
  const match = body.match(/^##\s+참고문헌\s*$([\s\S]*)$/m);
  if (!match) return 0;
  return (match[1].match(/^[ \t]*(?:\d+\.|-)[ \t]+\S+/gm) ?? []).length;
}

export async function validateRun(
  runId: string,
  requireHumanApproval = true
): Promise<ValidationResult> {
  const dir = runDirectory(runId);
  const state = await readState(path.join(dir, "state.json"));
  const gate = PublishGateSchema.parse(await readJson(gatePath));
  const raw = await readFile(path.join(dir, "final.md"), "utf8");
  const parsed = matter(raw);
  const errors: string[] = [];
  const warnings: string[] = [];

  const frontmatter = ArticleFrontmatterSchema.safeParse(parsed.data);
  if (!frontmatter.success) {
    errors.push(
      ...frontmatter.error.issues.map(
        (issue) => `frontmatter.${issue.path.join(".")}: ${issue.message}`
      )
    );
  }

  for (const section of gate.requiredSections) {
    if (!sectionExists(parsed.content, section)) {
      errors.push(`필수 섹션이 없습니다: ${section}`);
    }
  }

  const refs = referenceCount(parsed.content);
  if (refs < gate.minimumReferences) {
    errors.push(`참고문헌은 최소 ${gate.minimumReferences}개가 필요합니다. 현재 ${refs}개입니다.`);
  }

  if (
    gate.requireOpinionDisclaimer &&
    !parsed.content.includes("사실 전달이 아니라 작성자의 해석과 견해")
  ) {
    errors.push("작성자의 견해 안내문이 없습니다.");
  }

  if (/\bRisk:\s*high[\s\S]{0,250}\bVerdict:\s*unverified\b/i.test(parsed.content)) {
    errors.push("고위험 미검증 주장이 남아 있습니다.");
  }
  if (/\bVerdict:\s*contradicted\b/i.test(parsed.content)) {
    errors.push("반박된 주장이 남아 있습니다.");
  }

  if (requireHumanApproval && gate.requireHumanApproval && !state.humanApproved) {
    errors.push("state.json의 humanApproved가 true가 아닙니다.");
  }

  const urls = parsed.content.match(/https?:\/\/[^\s)>]+/g) ?? [];
  if (urls.length < refs) {
    warnings.push("일부 참고문헌에 URL이 없을 수 있습니다.");
  }

  return { ok: errors.length === 0, errors, warnings };
}
