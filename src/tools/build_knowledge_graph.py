"""
content/posts/ 내 38개 포스팅 파일들의 태그, 연관 관계, 메타데이터를 파싱하여
content/knowledge-graph.json 지식 그래프 DB를 자동으로 생성/갱신하는 도구
"""

import json
import os
import re
from datetime import datetime

POSTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "content", "posts"))
KNOWLEDGE_GRAPH_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "wiki", "knowledge-graph.json"))

def parse_frontmatter(content):
    match = re.search(r'^---\r?\n([\s\S]*?)\r?\n---', content)
    if not match:
        return {}
    
    yaml_text = match.group(1)
    metadata = {}
    for line in yaml_text.split('\n'):
        if ':' not in line:
            continue
        key, val = line.split(':', 1)
        key = key.strip()
        val = val.strip()
        if val.startswith('"') and val.endsWith('"'):
            val = val[1:-1]
        if val.startswith('[') and val.endsWith(']'):
            try:
                val = json.loads(val)
            except Exception:
                pass
        metadata[key] = val
    return metadata

def build_knowledge_graph():
    if not os.path.exists(POSTS_DIR):
        print(f"오류: {POSTS_DIR} 디렉토리가 존재하지 않습니다.")
        return

    files = [f for f in os.listdir(POSTS_DIR) if f.endswith('.md')]
    print(f"총 {len(files)}개 마크다운 게시글로부터 지식 그래프 구축 시작...")

    nodes = []
    tag_map = {}

    for file in files:
        filepath = os.path.join(POSTS_DIR, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        meta = parse_frontmatter(content)
        post_node = {
            "id": meta.get("id", file.replace(".md", "")),
            "title": meta.get("title", file),
            "slug": meta.get("slug", file.replace(".md", "")),
            "url": meta.get("url", ""),
            "publishedAt": meta.get("publishedAt", ""),
            "updatedAt": meta.get("updatedAt", ""),
            "tags": meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
            "file": file
        }
        nodes.append(post_node)

        for tag in post_node["tags"]:
            lower_tag = tag.lower()
            if lower_tag not in tag_map:
                tag_map[lower_tag] = []
            tag_map[lower_tag].append(post_node["id"])

    edges = []
    edge_set = set()

    for i, n1 in enumerate(nodes):
        n1["relatedPostIds"] = []
        for j, n2 in enumerate(nodes):
            if i == j:
                continue
            
            n1_tags_lower = [t.lower() for t in n1["tags"]]
            n2_tags_lower = [t.lower() for t in n2["tags"]]
            shared_tags = [t for t in n1["tags"] if t.lower() in n2_tags_lower]

            if shared_tags:
                if n2["id"] not in n1["relatedPostIds"]:
                    n1["relatedPostIds"].append(n2["id"])
                
                edge_key = tuple(sorted([n1["id"], n2["id"]]))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": n1["id"],
                        "target": n2["id"],
                        "weight": len(shared_tags),
                        "sharedTags": shared_tags
                    })

    graph_data = {
        "version": "1.0.0",
        "updatedAt": datetime.utcnow().isoformat() + "Z",
        "stats": {
            "totalPosts": len(nodes),
            "totalTags": len(tag_map),
            "totalConnections": len(edges)
        },
        "tagMap": tag_map,
        "posts": nodes,
        "edges": edges
    }

    os.makedirs(os.path.dirname(KNOWLEDGE_GRAPH_PATH), exist_ok=True)
    with open(KNOWLEDGE_GRAPH_PATH, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, ensure_ascii=False, indent=2)

    print(f"=== 지식 그래프 구축 완료: {KNOWLEDGE_GRAPH_PATH} ({len(nodes)}개 노드, {len(edges)}개 엣지) ===")

if __name__ == "__main__":
    build_knowledge_graph()
