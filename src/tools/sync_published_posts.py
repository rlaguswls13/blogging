"""
Blogger 실서버(beji-tech.blogspot.com)의 전체 게시글을 로컬 content/posts/에 동기화 축적하는 스크립트
"""

import json
import os
import re
import sys
import urllib.request

BLOG_FEED_BASE = "https://beji-tech.blogspot.com/feeds/posts/default?alt=json"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "content", "posts"))

def clean_html_to_markdown(html_content: str) -> str:
    """HTML 본문을 깔끔한 마크다운 스타일 텍스트로 축약 및 변환"""
    if not html_content:
        return ""
    
    # 1. <style> 태그 제거
    text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html_content)
    
    # 2. 헤더 변환
    text = re.sub(r'<h1[^>]*>([\s\S]*?)</h1>', r'\n# \1\n', text)
    text = re.sub(r'<h2[^>]*>([\s\S]*?)</h2>', r'\n## \1\n', text)
    text = re.sub(r'<h3[^>]*>([\s\S]*?)</h3>', r'\n### \1\n', text)
    text = re.sub(r'<h4[^>]*>([\s\S]*?)</h4>', r'\n#### \1\n', text)
    
    # 3. 블록 요소 및 태그 정리
    text = re.sub(r'<p[^>]*>([\s\S]*?)</p>', r'\n\1\n', text)
    text = re.sub(r'<blockquote[^>]*>([\s\S]*?)</blockquote>', r'\n> \1\n', text)
    text = re.sub(r'<code[^>]*>([\s\S]*?)</code>', r'`\1`', text)
    text = re.sub(r'<pre[^>]*>([\s\S]*?)</pre>', r'\n```\n\1\n```\n', text)
    text = re.sub(r'<strong[^>]*>([\s\S]*?)</strong>', r'**\1**', text)
    text = re.sub(r'<b[^>]*>([\s\S]*?)</b>', r'**\1**', text)
    text = re.sub(r'<em[^>]*>([\s\S]*?)</em>', r'*\1*', text)
    text = re.sub(r'<li[^>]*>([\s\S]*?)</li>', r'\n- \1', text)
    text = re.sub(r'<hr\s*/?>', r'\n---\n', text)
    
    # 4. 링크 및 이미지
    text = re.sub(r'<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', r'[\2](\1)', text)
    text = re.sub(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"[^>]*>', r'![\2](\1)', text)
    text = re.sub(r'<img[^>]+src="([^"]+)"[^>]*>', r'![](\1)', text)
    
    # 5. 기타 HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 6. HTML 엔티티 디코딩
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    
    # 7. 연속 줄바꿈 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def fetch_all_posts():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_entries = []
    start_index = 1
    max_results = 50

    print("=== Blogger 게시글 동기화 시작 ===")
    while True:
        url = f"{BLOG_FEED_BASE}&start-index={start_index}&max-results={max_results}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                entries = data.get('feed', {}).get('entry', [])
                if not entries:
                    break
                all_entries.extend(entries)
                total_results = int(data.get('feed', {}).get('openSearch$totalResults', {}).get('$t', 0))
                print(f"가져온 포스트 수: {len(all_entries)} / {total_results}")
                if len(all_entries) >= total_results:
                    break
                start_index += max_results
        except Exception as e:
            print(f"오류 발생 ({url}): {e}")
            break

    print(f"총 {len(all_entries)}개의 포스트 동기화 진행 중...")
    
    saved_count = 0
    for entry in all_entries:
        title = entry.get('title', {}).get('$t', 'Untitled')
        published = entry.get('published', {}).get('$t', '')
        updated = entry.get('updated', {}).get('$t', '')
        
        categories = [cat.get('term') for cat in entry.get('category', []) if cat.get('term')]
        
        alt_link = None
        for link in entry.get('link', []):
            if link.get('rel') == 'alternate':
                alt_link = link.get('href')
                break
        
        if not alt_link:
            continue
            
        slug = alt_link.split('/')[-1].replace('.html', '')
        raw_html = entry.get('content', {}).get('$t', '') or entry.get('summary', {}).get('$t', '')
        markdown_body = clean_html_to_markdown(raw_html)
        
        post_id = entry.get('id', {}).get('$t', '').split('post-')[-1]
        
        tags_str = json.dumps(categories, ensure_ascii=False)
        frontmatter = f"""---
id: "{post_id}"
title: "{title}"
slug: "{slug}"
status: "published"
url: "{alt_link}"
publishedAt: "{published}"
updatedAt: "{updated}"
tags: {tags_str}
---

# {title}

{markdown_body}
"""
        filepath = os.path.join(OUTPUT_DIR, f"{slug}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
        saved_count += 1

    print(f"=== 완료: 총 {saved_count}개 포스트가 {OUTPUT_DIR} 에 동기화 저장되었습니다 ===")

if __name__ == "__main__":
    fetch_all_posts()
