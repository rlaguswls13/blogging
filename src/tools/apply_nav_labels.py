"""
Blogger 실서버(beji-tech.blogspot.com) 게시글에 상단 탭(Basics/Advanced/Trends) 분류
라벨을 직접 부여하는 유지보수 도구.

배경: content/theme/blogger_site_theme.xml의 postMatchesFilter()는 원래 각 탭마다
범용 키워드 목록(database, sql, concurrency 등)을 나열해 매칭했는데, 글이 늘어날수록
목록을 계속 손봐야 하고 중복/누락 분류가 발생했다. 이 스크립트는 그 반대로, 글 자체에
정확히 하나의 분류 라벨을 실제로 붙여서 테마 JS가 단순 라벨 조회만으로 동작하도록 만든다.

분류 규칙 (postMatchesFilter()와 동일한 기준):
  - Basics : 이미 '기초' 또는 'Basics' 라벨이 있는 글 (작성 시점부터 저자가 일관되게 부여해옴)
  - Trends : AI Agent/GraphRAG/AI Framework/LLM/LLM Agent/Kubernetes/Cloud-Native/
             DevOps/HTTP3/QUIC/AutoGen 라벨 중 하나라도 있는 글
  - Advanced : 위 두 조건에 해당하지 않는 나머지 전부 (기본값)

기존 라벨은 절대 제거하지 않고, 분류 결과에 해당하는 라벨 하나만 추가한다(멱등적 재실행 가능).

사용법:
  python src/tools/apply_nav_labels.py --dry-run   # 무엇이 바뀔지만 출력, 실제 반영 없음
  python src/tools/apply_nav_labels.py              # 실제 Blogger 라이브 게시물에 반영
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

TRENDS_LABELS = {
    "ai agent", "graphrag", "ai framework", "llm", "llm agent",
    "kubernetes", "cloud-native", "devops", "http3", "quic", "autogen",
}
BASICS_LABELS = {"basics", "기초"}


def classify(labels):
    """None이면 이미 Basics라 변경 불필요, 아니면 추가할 라벨명을 반환."""
    lower = {label.lower() for label in labels}
    if lower & BASICS_LABELS:
        return None
    if lower & TRENDS_LABELS:
        return "Trends"
    return "Advanced"


def get_service():
    client_id = os.environ["BLOGGER_CLIENT_ID"]
    client_secret = os.environ["BLOGGER_CLIENT_SECRET"]
    refresh_token = os.environ["BLOGGER_REFRESH_TOKEN"]
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    return build("blogger", "v3", credentials=credentials)


def fetch_all_posts(posts_resource, blog_id):
    all_posts = []
    request = posts_resource.list(blogId=blog_id, maxResults=150, fetchBodies=False)
    while request is not None:
        response = request.execute()
        all_posts.extend(response.get("items", []))
        request = posts_resource.list_next(request, response)
    return all_posts


def main():
    dry_run = "--dry-run" in sys.argv
    blog_id = os.environ["BLOGGER_BLOG_ID"]

    service = get_service()
    posts_resource = service.posts()

    all_posts = fetch_all_posts(posts_resource, blog_id)
    print(f"총 {len(all_posts)}개 게시물 조회됨\n")

    changed = 0
    for post in all_posts:
        post_id = post["id"]
        title = post["title"]
        existing_labels = post.get("labels", [])

        target = classify(existing_labels)
        if target is None or target in existing_labels:
            continue

        new_labels = existing_labels + [target]
        tag = "[DRY-RUN]" if dry_run else "[APPLY]"
        print(f"{tag} {title}\n       +{target}  (기존: {existing_labels})")

        if not dry_run:
            posts_resource.patch(
                blogId=blog_id, postId=post_id, body={"labels": new_labels}
            ).execute()

        changed += 1

    verb = "시뮬레이션" if dry_run else "완료"
    print(f"\n총 {changed}개 게시물에 라벨 추가 {verb}")


if __name__ == "__main__":
    main()
