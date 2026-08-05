import os
import datetime
from typing import Dict
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from src.publishers.base import BlogPublisher, ArticlePayload, PublishResult

class BloggerPublisher(BlogPublisher):
    @property
    def name(self) -> str:
        return "blogger"

    def get_credentials(self) -> Dict[str, str]:
        client_id = os.environ.get("BLOGGER_CLIENT_ID")
        client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
        refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")
        blog_id = os.environ.get("BLOGGER_BLOG_ID")

        if not client_id or not client_secret or not refresh_token or not blog_id:
            raise ValueError(
                "Google Blogger API 설정이 누락되었습니다.\n"
                "필수 환경변수: BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN, BLOGGER_BLOG_ID"
            )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "blog_id": blog_id
        }

    def get_blogger_service(self, creds_dict: Dict[str, str]):
        credentials = Credentials(
            token=None,
            refresh_token=creds_dict["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=creds_dict["client_id"],
            client_secret=creds_dict["client_secret"]
        )
        return build("blogger", "v3", credentials=credentials)

    def publish(self, article: ArticlePayload, dry_run: bool) -> PublishResult:
        creds_dict = self.get_credentials()
        blog_id = creds_dict["blog_id"]
        
        if dry_run:
            print(f"[Blogger Dry-Run] {'업데이트' if article.existingPostId else '신규 게시'}")
            print(f"[Blogger Dry-Run] 제목: {article.title}")
            print(f"[Blogger Dry-Run] 태그: {', '.join(article.tags)}")
            print(f"[Blogger Dry-Run] HTML 글자 수: {len(article.htmlContent)}자")
            post_id = article.existingPostId if article.existingPostId else "dry-run-blogger-post-id"
            return PublishResult(
                platform=self.name,
                postId=post_id,
                url=f"https://draft.blogger.com/blog/post/edit/{blog_id}/{post_id}",
                publishedAt=datetime.datetime.utcnow().isoformat() + "Z"
            )

        try:
            service = self.get_blogger_service(creds_dict)
            posts = service.posts()
            
            body = {
                "title": article.title,
                "content": article.htmlContent,
                "labels": article.tags
            }
            
            if article.existingPostId:
                request = posts.update(
                    blogId=blog_id,
                    postId=article.existingPostId,
                    body=body
                )
            else:
                request = posts.insert(
                    blogId=blog_id,
                    isDraft=article.isDraft if article.isDraft is not None else False,
                    body=body
                )
                
            response = request.execute()
            
            post_id = response.get("id")
            url = response.get("url")
            
            if not post_id or not url:
                raise Exception("Blogger API 응답에서 postId 또는 url을 찾을 수 없습니다.")
                
            published_at = response.get("published", datetime.datetime.utcnow().isoformat() + "Z")
            
            return PublishResult(
                platform=self.name,
                postId=post_id,
                url=url,
                publishedAt=published_at
            )
        except Exception as error:
            raise Exception(f"Blogger 게시 중 오류 발생: {str(error)}")

    def validate_auth(self) -> bool:
        try:
            creds_dict = self.get_credentials()
            service = self.get_blogger_service(creds_dict)
            service.blogs().get(blogId=creds_dict["blog_id"]).execute()
            return True
        except Exception:
            return False
