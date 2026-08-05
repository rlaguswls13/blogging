import { google } from 'googleapis';
import type { BlogPublisher, ArticlePayload, PublishResult } from './base.js';

export class BloggerPublisher implements BlogPublisher {
  readonly name = 'blogger';

  private getCredentials() {
    const clientId = process.env.BLOGGER_CLIENT_ID;
    const clientSecret = process.env.BLOGGER_CLIENT_SECRET;
    const refreshToken = process.env.BLOGGER_REFRESH_TOKEN;
    const blogId = process.env.BLOGGER_BLOG_ID;

    if (!clientId || !clientSecret || !refreshToken || !blogId) {
      throw new Error(
        'Google Blogger API 설정이 누락되었습니다.\n' +
        '필수 환경변수: BLOGGER_CLIENT_ID, BLOGGER_CLIENT_SECRET, BLOGGER_REFRESH_TOKEN, BLOGGER_BLOG_ID'
      );
    }

    return { clientId, clientSecret, refreshToken, blogId };
  }

  private getAuthClient(clientId: string, clientSecret: string, refreshToken: string) {
    const oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
    oauth2Client.setCredentials({ refresh_token: refreshToken });
    return oauth2Client;
  }

  async publish(article: ArticlePayload, dryRun: boolean): Promise<PublishResult> {
    const { clientId, clientSecret, refreshToken, blogId } = this.getCredentials();
    const auth = this.getAuthClient(clientId, clientSecret, refreshToken);
    const blogger = google.blogger('v3');

    if (dryRun) {
      console.log(`[Blogger Dry-Run] ${article.existingPostId ? '업데이트' : '신규 게시'}`);
      console.log(`[Blogger Dry-Run] 제목: ${article.title}`);
      console.log(`[Blogger Dry-Run] 태그: ${article.tags.join(', ')}`);
      console.log(`[Blogger Dry-Run] HTML 글자 수: ${article.htmlContent.length}자`);
      return {
        platform: this.name,
        postId: article.existingPostId || 'dry-run-blogger-post-id',
        url: `https://draft.blogger.com/blog/post/edit/${blogId}/${article.existingPostId || 'dry-run-blogger-post-id'}`,
        publishedAt: new Date().toISOString(),
      };
    }

    try {
      let res: any;
      if (article.existingPostId) {
        res = await blogger.posts.update({
          auth,
          blogId,
          postId: article.existingPostId,
          requestBody: {
            title: article.title,
            content: article.htmlContent,
            labels: article.tags,
          },
        });
      } else {
        res = await blogger.posts.insert({
          auth,
          blogId,
          isDraft: article.isDraft ?? false,
          requestBody: {
            title: article.title,
            content: article.htmlContent,
            labels: article.tags,
          },
        });
      }

      const postId = res.data.id;
      const url = res.data.url;

      if (!postId || !url) {
        throw new Error('Blogger API 응답에서 postId 또는 url을 찾을 수 없습니다.');
      }

      return {
        platform: this.name,
        postId,
        url,
        publishedAt: res.data.published || new Date().toISOString(),
      };
    } catch (error: any) {
      throw new Error(`Blogger 게시 중 오류 발생: ${error.message || error}`);
    }
  }

  async validateAuth(): Promise<boolean> {
    try {
      const { clientId, clientSecret, refreshToken, blogId } = this.getCredentials();
      const auth = this.getAuthClient(clientId, clientSecret, refreshToken);
      
      // Try to get token to verify credentials work
      const accessToken = await auth.getAccessToken();
      if (!accessToken.token) {
        return false;
      }

      // Check if the blog is accessible
      const blogger = google.blogger('v3');
      await blogger.blogs.get({ auth, blogId });
      
      return true;
    } catch {
      return false;
    }
  }
}
