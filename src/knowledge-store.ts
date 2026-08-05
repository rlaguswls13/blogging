import { knowledgeGraphPath } from "./paths.js";
import { readJson, writeJson } from "./files.js";
import type { KnowledgeNode, TailQuestion } from "./types.js";

interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  version: number;
}

export async function loadKnowledgeGraph(): Promise<KnowledgeGraph> {
  try {
    return await readJson<KnowledgeGraph>(knowledgeGraphPath);
  } catch (error) {
    // If it doesn't exist, return empty graph structure
    return { nodes: [], version: 1 };
  }
}

export async function saveKnowledgeGraph(graph: KnowledgeGraph): Promise<void> {
  await writeJson(knowledgeGraphPath, graph);
}

export async function addKnowledgeNode(node: KnowledgeNode): Promise<void> {
  const graph = await loadKnowledgeGraph();
  
  // Filter out existing node if any to avoid duplication
  graph.nodes = graph.nodes.filter(n => n.articleId !== node.articleId);
  graph.nodes.push(node);
  
  await saveKnowledgeGraph(graph);
}

export async function getTodos(status?: 'todo' | 'in_progress' | 'done'): Promise<{ articleId: string; topic: string; todo: TailQuestion }[]> {
  const graph = await loadKnowledgeGraph();
  const todos: { articleId: string; topic: string; todo: TailQuestion }[] = [];
  
  for (const node of graph.nodes) {
    for (const q of node.tailQuestions) {
      if (!status || q.status === status) {
        todos.push({
          articleId: node.articleId,
          topic: node.topic,
          todo: q
        });
      }
    }
  }
  return todos;
}

export async function updateTodoStatus(
  questionId: string,
  status: 'todo' | 'in_progress' | 'done',
  linkedArticleId?: string
): Promise<boolean> {
  const graph = await loadKnowledgeGraph();
  let updated = false;
  
  for (const node of graph.nodes) {
    for (const q of node.tailQuestions) {
      if (q.id === questionId) {
        q.status = status;
        if (linkedArticleId) {
          q.linkedArticleId = linkedArticleId;
        }
        updated = true;
      }
    }
  }
  
  if (updated) {
    await saveKnowledgeGraph(graph);
  }
  return updated;
}

/**
 * Calculates backlinks between a new article and existing nodes in the knowledge graph.
 * For example, if the new article's topic or keyword matches a tail question in an existing article,
 * we can create a backlink from the existing article to the new one.
 */
export async function calculateBacklinks(
  newArticleId: string,
  newTopic: string
): Promise<{ fromArticleId: string; toArticleId: string; anchor: string }[]> {
  const graph = await loadKnowledgeGraph();
  const backlinks: { fromArticleId: string; toArticleId: string; anchor: string }[] = [];
  
  // A simple keywords/topic matching rule:
  // If an existing article has a tail question (TODO) whose words or concepts overlap with the newTopic,
  // we link them.
  const newTopicNormalized = newTopic.toLowerCase().replace(/\s+/g, "");
  
  for (const node of graph.nodes) {
    if (node.articleId === newArticleId) continue;
    
    for (const q of node.tailQuestions) {
      const qNormalized = q.question.toLowerCase().replace(/\s+/g, "");
      
      // If the question contains key parts of the new topic, suggest a backlink
      // (For a production system this could be semantic search or LLM based, but let's do keyword matching for now)
      const isMatch = qNormalized.includes(newTopicNormalized) || newTopicNormalized.includes(qNormalized);
      if (isMatch) {
        backlinks.push({
          fromArticleId: node.articleId,
          toArticleId: newArticleId,
          anchor: q.question
        });
        
        // Auto-update the tail question to point to this new article
        q.status = 'done';
        q.linkedArticleId = newArticleId;
      }
    }
  }
  
  return backlinks;
}
