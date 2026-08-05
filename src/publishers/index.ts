import fs from 'node:fs/promises';
import path from 'node:path';
import matter from 'gray-matter';
import { runDirectory } from '../paths.js';
import { readState, writeJson } from '../files.js';
import { validateRun } from '../validate.js';
import { convertMarkdownToHtml } from '../converter.js';
import { BloggerPublisher } from './blogger.js';
import { NotionPublisher } from './notion.js';
import { addKnowledgeNode, calculateBacklinks } from '../knowledge-store.js';
import type { BlogPublisher, ArticlePayload, PublishResult } from './base.js';
import type { Platform, TailQuestion, Reference, TocItem } from '../types.js';

export function getPublisher(platform: Platform): BlogPublisher {
  switch (platform) {
    case 'blogger':
      return new BloggerPublisher();
    case 'notion':
      return new NotionPublisher();
    default:
      throw new Error(`지원하지 않는 플랫폼입니다: ${platform}`);
  }
}

function parseTailQuestions(markdownContent: string, articleId: string): TailQuestion[] {
  const match = markdownContent.match(/## 꼬리질문\s*$([\s\S]*?)(##|$)/m);
  if (!match) return [];

  const sectionContent = match[1];
  const lines = sectionContent.split('\n');
  const questions: TailQuestion[] = [];
  let index = 1;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Matches list item prefixes like "1. ", "- ", "- [ ] "
    const cleanLine = trimmed
      .replace(/^(?:\d+\.|[-*])\s*(?:\[\s*\])?\s*/, '')
      .trim();

    if (!cleanLine) continue;

    // Find all URLs in the line
    const urlMatches = cleanLine.match(/https?:\/\/[^\s\)]+/g) ?? [];
    
    // Clean question text by removing URL mentions
    const questionText = cleanLine
      .replace(/\(?(?:추천\s*)?URL:\s*https?:\/\/[^\s\)]+\)?/gi, '')
      .replace(/https?:\/\/[^\s\)]+/g, '')
      .replace(/\(\s*\)/g, '')
      .trim();

    questions.push({
      id: `q-${articleId}-${index++}`,
      question: questionText || cleanLine,
      relatedTocIds: [],
      suggestedUrls: urlMatches,
      status: 'todo'
    });
  }

  return questions;
}

function parseReferences(markdownContent: string): Reference[] {
  const match = markdownContent.match(/## 참고문헌\s*$([\s\S]*?)(##|$)/m);
  if (!match) return [];

  const sectionContent = match[1];
  const lines = sectionContent.split('\n');
  const refs: Reference[] = [];
  let index = 1;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const cleanLine = trimmed.replace(/^(?:\d+\.|[-*])\s*/, '').trim();
    if (!cleanLine) continue;

    // Extract title and URL from Markdown link: [Title](URL)
    const linkMatch = cleanLine.match(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/);
    if (linkMatch) {
      refs.push({
        id: `ref-${index++}`,
        title: linkMatch[1],
        url: linkMatch[2],
        tocItemId: ''
      });
    } else {
      // Fallback: extract plain URL
      const urlMatch = cleanLine.match(/(https?:\/\/\S+)/);
      if (urlMatch) {
        refs.push({
          id: `ref-${index++}`,
          title: cleanLine.replace(urlMatch[0], '').trim() || '참고 자료',
          url: urlMatch[0],
          tocItemId: ''
        });
      }
    }
  }

  return refs;
}

function parseTocItems(markdownContent: string): TocItem[] {
  const lines = markdownContent.split('\n');
  const items: TocItem[] = [];
  let index = 1;
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
      const title = match[2].trim();
      
      // Exclude main metadata/system sections from the formal TOC data if desired,
      // but let's register all depth 2-3 headings.
      items.push({
        id: `toc-${index++}`,
        title,
        level: depth as any
      });
    }
  }

  return items;
}

export async function publishToMulti(
  runId: string,
  platforms: Platform[],
  dryRun: boolean
): Promise<void> {
  // 1. Run gate validation
  const validation = await validateRun(runId, !dryRun);
  if (!validation.ok) {
    throw new Error(`게시 게이트 통과 실패:\n- ${validation.errors.join('\n- ')}`);
  }

  const dir = runDirectory(runId);
  const statePath = path.join(dir, 'state.json');
  const state = await readState(statePath);
  const raw = await fs.readFile(path.join(dir, 'final.md'), 'utf8');
  const { content, data } = matter(raw);

  // Convert markdown to HTML
  const conversion = await convertMarkdownToHtml(content);

  // Extract tags from frontmatter
  const tags: string[] = Array.isArray(data.tags) ? data.tags : [];

  const results: PublishResult[] = [];
  const publishedPlatforms = state.publishedPlatforms || {};

  for (const p of platforms) {
    const publisher = getPublisher(p);
    
    // Retrieve existing post ID for update
    const existingPostId = p === 'notion' 
      ? (state.notionPageId || publishedPlatforms[p]?.postId)
      : publishedPlatforms[p]?.postId;

    const payload: ArticlePayload = {
      title: data.title || state.topic,
      markdownContent: content,
      htmlContent: conversion.html,
      tags,
      existingPostId
    };

    console.log(`[게시 시작] 플랫폼: ${p}`);
    const result = await publisher.publish(payload, dryRun);
    results.push(result);
    console.log(`[게시 완료] 플랫폼: ${p}, ID: ${result.postId}`);
  }

  if (dryRun) {
    console.log('Dry-run 완료. 실제 상태를 업데이트하지 않습니다.');
    return;
  }

  // Parse sections to populate knowledge graph
  const tailQuestions = parseTailQuestions(content, state.articleId);
  const references = parseReferences(content);
  const tocItems = parseTocItems(content);

  // Update state.json
  const updatedPlatforms = { ...publishedPlatforms };
  for (const r of results) {
    updatedPlatforms[r.platform as Platform] = {
      postId: r.postId,
      url: r.url,
      publishedAt: r.publishedAt
    };
    if (r.platform === 'notion') {
      state.notionPageId = r.postId;
    }
  }

  state.status = 'published';
  state.tailQuestions = tailQuestions;
  state.publishedPlatforms = updatedPlatforms;
  state.updatedAt = new Date().toISOString();

  await writeJson(statePath, state);

  // Save session publish result file
  await writeJson(path.join(dir, 'publish-result.json'), {
    runId,
    results,
    publishedAt: state.updatedAt
  });

  // Calculate backlinks and add to knowledge graph
  const backlinks = await calculateBacklinks(state.articleId, state.topic);
  
  await addKnowledgeNode({
    articleId: state.articleId,
    topic: state.topic,
    createdAt: state.updatedAt,
    tocItems,
    references,
    tailQuestions,
    backlinks
  });

  console.log(`모든 플랫폼 게시 완료 및 지식 그래프에 등록되었습니다.`);
}
