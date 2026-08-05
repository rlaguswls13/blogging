import { z } from "zod";

export const WorkflowStatus = z.enum([
  "created",
  "researched",
  "drafted",
  "fact_checked",
  "approved",
  "published"
]);

// 목차 항목
export const TocItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  level: z.number().int().min(1).max(3),
});
export type TocItem = z.infer<typeof TocItemSchema>;

// 참고문헌
export const ReferenceSchema = z.object({
  id: z.string(),
  url: z.string().url(),
  title: z.string(),
  author: z.string().optional(),
  publishedDate: z.string().optional(),
  tocItemId: z.string(),
});
export type Reference = z.infer<typeof ReferenceSchema>;

// 꼬리질문
export const TailQuestionSchema = z.object({
  id: z.string(),
  question: z.string(),
  relatedTocIds: z.array(z.string()),
  suggestedUrls: z.array(z.string().url()),
  status: z.enum(['todo', 'in_progress', 'done']),
  linkedArticleId: z.string().optional(),
});
export type TailQuestion = z.infer<typeof TailQuestionSchema>;

// 지식 그래프 노드
export const KnowledgeNodeSchema = z.object({
  articleId: z.string(),
  topic: z.string(),
  createdAt: z.string().datetime(),
  tocItems: z.array(TocItemSchema),
  references: z.array(ReferenceSchema),
  tailQuestions: z.array(TailQuestionSchema),
  backlinks: z.array(z.object({
    fromArticleId: z.string(),
    toArticleId: z.string(),
    anchor: z.string(),
  })),
});
export type KnowledgeNode = z.infer<typeof KnowledgeNodeSchema>;

// 게시 플랫폼
export const PlatformSchema = z.enum(['notion', 'blogger']);
export type Platform = z.infer<typeof PlatformSchema>;

export const RunStateSchema = z.object({
  runId: z.string().min(1),
  articleId: z.string().min(1),
  topic: z.string().min(1),
  status: WorkflowStatus,
  humanApproved: z.boolean(),
  notionPageId: z.string().nullable(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  tailQuestions: z.array(TailQuestionSchema).optional(),
  publishedPlatforms: z.record(
    PlatformSchema,
    z.object({
      postId: z.string(),
      url: z.string().url(),
      publishedAt: z.string().datetime(),
    })
  ).optional()
});

export type RunState = z.infer<typeof RunStateSchema>;

export const ArticleFrontmatterSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  slug: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
  status: z.enum(["draft", "verified", "approved", "published"]),
  createdAt: z.string().min(1),
  updatedAt: z.string().min(1),
  tags: z.array(z.string()).default([]),
  notionPageId: z.string().nullable().optional(),
  factCheckScore: z.number().min(0).max(1)
});

export const PublishGateSchema = z.object({
  requiredSections: z.array(z.string()).min(1),
  minimumReferences: z.number().int().nonnegative(),
  unresolvedHighRiskClaims: z.number().int().nonnegative(),
  contradictedClaims: z.number().int().nonnegative(),
  requireOpinionDisclaimer: z.boolean(),
  requireHumanApproval: z.boolean(),
  allowBrokenLinks: z.boolean()
});
