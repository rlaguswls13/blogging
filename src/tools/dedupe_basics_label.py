"""
Blogger 실서버 게시글에서 '기초'와 'Basics' 라벨 중복을 정리하는 유지보수 도구.

배경: 모든 기초(Basics) 분류 글이 '기초'와 'Basics' 두 라벨을 동시에 달고 있었다
(같은 뜻의 한국어/영어 중복). Advanced/Trends는 영어 단일 라벨만 쓰므로, 태그 어휘를
전부 영어로 통일하기 위해 'Basics'만 남기고 '기초'는 제거한다. (만약 '기초'만 있고
'Basics'가 없는 글이 있다면 안전하게 '기초' -> 'Basics'로 치환한다.)

사용법:
  python src/tools/dedupe_basics_label.py --dry-run
  python src/tools/dedupe_basics_label.py
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

        if "기초" not in existing_labels:
            continue

        if "Basics" in existing_labels:
            new_labels = [l for l in existing_labels if l != "기초"]
        else:
            new_labels = ["Basics" if l == "기초" else l for l in existing_labels]

        tag = "[DRY-RUN]" if dry_run else "[APPLY]"
        print(f"{tag} {title}\n       {existing_labels} -> {new_labels}")

        if not dry_run:
            posts_resource.patch(
                blogId=blog_id, postId=post_id, body={"labels": new_labels}
            ).execute()

        changed += 1

    verb = "시뮬레이션" if dry_run else "완료"
    print(f"\n총 {changed}개 게시물 라벨 정리 {verb}")


if __name__ == "__main__":
    main()
