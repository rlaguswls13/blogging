import os
import datetime
import re
from typing import Dict, Any, List
import requests
from src.publishers.base import BlogPublisher, ArticlePayload, PublishResult

def notion_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": os.environ.get("NOTION_VERSION", "2026-03-11")
    }

def notion_request(token: str, url: str, method: str = "GET", json_data: Any = None) -> Any:
    headers = notion_headers(token)
    full_url = f"https://api.notion.com{url}"
    
    if method == "GET":
        response = requests.get(full_url, headers=headers)
    elif method == "POST":
        response = requests.post(full_url, headers=headers, json=json_data)
    elif method == "PATCH":
        response = requests.patch(full_url, headers=headers, json=json_data)
    else:
        raise ValueError(f"지원하지 않는 HTTP Method: {method}")
        
    if not response.ok:
        raise Exception(f"Notion API {response.status_code}: {response.text}")
        
    return response.json()

class NotionPublisher(BlogPublisher):
    @property
    def name(self) -> str:
        return "notion"

    def get_credentials(self) -> Dict[str, str]:
        token = os.environ.get("NOTION_WRITE_TOKEN")
        parent_id = os.environ.get("NOTION_BLOG_PARENT_ID")
        if not token or not parent_id:
            raise ValueError("NOTION_WRITE_TOKEN과 NOTION_BLOG_PARENT_ID가 필요합니다.")
        return {"token": token, "parent_id": parent_id}

    def publish(self, article: ArticlePayload, dry_run: bool) -> PublishResult:
        creds = self.get_credentials()
        token = creds["token"]
        parent_id = creds["parent_id"]
        
        if dry_run:
            print(f"[Notion Dry-Run] {'업데이트' if article.existingPostId else '신규 게시'}")
            print(f"[Notion Dry-Run] 제목: {article.title}")
            print(f"[Notion Dry-Run] 마크다운 글자 수: {len(article.markdownContent)}자")
            post_id = article.existingPostId if article.existingPostId else "dry-run-notion-page-id"
            return PublishResult(
                platform=self.name,
                postId=post_id,
                url=f"https://notion.so/{post_id}",
                publishedAt=datetime.datetime.utcnow().isoformat() + "Z"
            )
            
        try:
            page_id = article.existingPostId
            if page_id:
                notion_request(token, f"/v1/pages/{page_id}/markdown", "PATCH", {
                    "type": "replace_content",
                    "replace_content": {"new_str": article.markdownContent}
                })
            else:
                parent_type = os.environ.get("NOTION_BLOG_PARENT_TYPE", "data_source")
                title_property = os.environ.get("NOTION_TITLE_PROPERTY", "Name")
                status_property = os.environ.get("NOTION_STATUS_PROPERTY", "Status")
                published_status = os.environ.get("NOTION_PUBLISHED_STATUS", "Published")
                
                parent = {"page_id": parent_id} if parent_type == "page" else {"data_source_id": parent_id}
                
                properties = None
                if parent_type != "page":
                    properties = {
                        title_property: {
                            "title": [{"text": {"content": str(article.title)}}]
                        },
                        status_property: {
                            "status": {"name": published_status}
                        }
                    }
                    
                body = {
                    "parent": parent,
                    "markdown": article.markdownContent
                }
                if properties:
                    body["properties"] = properties
                    
                page = notion_request(token, "/v1/pages", "POST", body)
                page_id = page.get("id")
                
            if not page_id:
                raise Exception("Notion API 응답에서 page_id를 생성하거나 찾지 못했습니다.")
                
            return PublishResult(
                platform=self.name,
                postId=page_id,
                url=f"https://notion.so/{page_id.replace('-', '')}",
                publishedAt=datetime.datetime.utcnow().isoformat() + "Z"
            )
        except Exception as error:
            raise Exception(f"Notion 게시 중 오류 발생: {str(error)}")

    def validate_auth(self) -> bool:
        try:
            creds = self.get_credentials()
            token = creds["token"]
            headers = notion_headers(token)
            res = requests.post("https://api.notion.com/v1/search", headers=headers, json={"page_size": 1})
            return res.ok
        except Exception:
            return False

# Read-only Notion client exports for sync_mdx.py
def query_published_pages() -> List[Dict[str, Any]]:
    token = os.environ.get("NOTION_READ_TOKEN")
    data_source_id = os.environ.get("NOTION_BLOG_DATA_SOURCE_ID")
    if not token or not data_source_id:
        raise ValueError("NOTION_READ_TOKEN과 NOTION_BLOG_DATA_SOURCE_ID가 필요합니다.")
        
    pages = []
    cursor = None
    
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
            
        result = notion_request(token, f"/v1/data_sources/{data_source_id}/query", "POST", body)
        results = result.get("results", [])
        
        for page in results:
            if is_published(page):
                pages.append(page)
                
        has_more = result.get("has_more", False)
        if not has_more:
            break
        cursor = result.get("next_cursor")
        if not cursor:
            break
            
    return pages

def is_published(page: Dict[str, Any]) -> bool:
    configured = os.environ.get("NOTION_PUBLISHED_STATUS", "Published").lower()
    properties = page.get("properties", {})
    
    for prop in properties.values():
        if not isinstance(prop, dict):
            continue
        status_info = prop.get("status") or prop.get("select") or {}
        name = status_info.get("name")
        if name and name.lower() in [configured, "published", "게시", "게시됨"]:
            return True
            
    return False

def retrieve_page_markdown(page_id: str) -> str:
    token = os.environ.get("NOTION_READ_TOKEN")
    if not token:
        raise ValueError("NOTION_READ_TOKEN이 필요합니다.")
        
    result = notion_request(token, f"/v1/pages/{page_id}/markdown", "GET")
    markdown = result.get("markdown", "")
    truncated = result.get("truncated", False)
    unknown_block_ids = result.get("unknown_block_ids", [])
    
    if truncated or unknown_block_ids:
        raise Exception(f"{page_id}: 잘리거나 읽을 수 없는 Notion 블록이 있습니다.")
        
    if re.search(r"<unknown\b", markdown, re.IGNORECASE):
        raise Exception(f"{page_id}: MDX로 변환할 수 없는 unknown 블록이 있습니다.")
        
    return markdown
