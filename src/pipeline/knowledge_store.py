import re
from typing import List, Dict, Any, Optional
from src.core.paths import project_root
from src.core.files import read_json, write_json
from src.core.types import KnowledgeNode, TailQuestion

knowledge_graph_path = project_root / "content" / "knowledge-graph.json"

def load_knowledge_graph() -> Dict[str, Any]:
    try:
        return read_json(knowledge_graph_path)
    except Exception:
        return {"nodes": [], "version": 1}

def save_knowledge_graph(graph: Dict[str, Any]) -> None:
    write_json(knowledge_graph_path, graph)

def add_knowledge_node(node: KnowledgeNode) -> None:
    graph = load_knowledge_graph()
    node_data = node.model_dump(exclude_none=True)
    
    # Filter out node with same articleId to prevent duplication
    graph["nodes"] = [n for n in graph.get("nodes", []) if n.get("articleId") != node.articleId]
    graph["nodes"].append(node_data)
    
    save_knowledge_graph(graph)

def get_todos(status: Optional[str] = None) -> List[Dict[str, Any]]:
    graph = load_knowledge_graph()
    todos = []
    
    for node in graph.get("nodes", []):
        article_id = node.get("articleId", "")
        topic = node.get("topic", "")
        for q in node.get("tailQuestions", []):
            if not status or q.get("status") == status:
                todos.append({
                    "articleId": article_id,
                    "topic": topic,
                    "todo": TailQuestion.model_validate(q)
                })
    return todos

def update_todo_status(
    question_id: str,
    status: str,
    linked_article_id: Optional[str] = None
) -> bool:
    graph = load_knowledge_graph()
    updated = False
    
    for node in graph.get("nodes", []):
        for q in node.get("tailQuestions", []):
            if q.get("id") == question_id:
                q["status"] = status
                if linked_article_id:
                    q["linkedArticleId"] = linked_article_id
                updated = True
                
    if updated:
        save_knowledge_graph(graph)
    return updated

def calculate_backlinks(
    new_article_id: str,
    new_topic: str
) -> List[Dict[str, str]]:
    graph = load_knowledge_graph()
    backlinks = []
    
    new_topic_normalized = re.sub(r"\s+", "", new_topic.lower())
    
    for node in graph.get("nodes", []):
        if node.get("articleId") == new_article_id:
            continue
            
        for q in node.get("tailQuestions", []):
            q_normalized = re.sub(r"\s+", "", q.get("question", "").lower())
            
            # Simple keyword overlap match
            is_match = (new_topic_normalized in q_normalized) or (q_normalized in new_topic_normalized)
            if is_match:
                backlinks.append({
                    "fromArticleId": node.get("articleId"),
                    "toArticleId": new_article_id,
                    "anchor": q.get("question")
                })
                
                # Auto-update status to done and link the new article
                q["status"] = "done"
                q["linkedArticleId"] = new_article_id
                
    if backlinks:
        save_knowledge_graph(graph)
        
    return backlinks
