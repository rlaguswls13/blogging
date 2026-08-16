"""
Blogger 실서버 게시글의 'Trends' 라벨을 'ETC'로 일괄 치환하는 유지보수 도구.

배경: 상단 네브 탭 이름을 'Trends'에서 'ETC'로 바꾸기로 했다 (AI/Kubernetes/DevOps 등
특정 키워드 글만 모으는 소수 카테고리라 '트렌드'보다 'ETC(기타)'가 실제 성격에 더 맞음).
기존 'Trends' 라벨이 붙은 글들의 실제 Blogger 라벨을 'ETC'로 바꿔서 테마의 단순 라벨
조회 로직(postMatchesFilter)과 URL(/search/label/ETC)이 그대로 맞물리게 한다.

사용법:
  python src/tools/rename_trends_to_etc.py --dry-run
  python src/tools/rename_trends_to_etc.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()


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

        if "Trends" not in existing_labels:
            continue

        new_labels = ["ETC" if l == "Trends" else l for l in existing_labels]

        tag = "[DRY-RUN]" if dry_run else "[APPLY]"
        print(f"{tag} {title}\n       {existing_labels} -> {new_labels}")

        if not dry_run:
            posts_resource.patch(
                blogId=blog_id, postId=post_id, body={"labels": new_labels}
            ).execute()

        changed += 1

    verb = "시뮬레이션" if dry_run else "완료"
    print(f"\n총 {changed}개 게시물 라벨 치환 {verb}")


if __name__ == "__main__":
    main()
