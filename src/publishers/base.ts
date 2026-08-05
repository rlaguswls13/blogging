export interface ArticlePayload {
  title: string;
  markdownContent: string;
  htmlContent: string;
  tags: string[];
  isDraft?: boolean;
  existingPostId?: string;
}

export interface PublishResult {
  platform: string;
  postId: string;
  url: string;
  publishedAt: string;
}

export interface BlogPublisher {
  readonly name: string;
  publish(article: ArticlePayload, dryRun: boolean): Promise<PublishResult>;
  validateAuth(): Promise<boolean>;
}
