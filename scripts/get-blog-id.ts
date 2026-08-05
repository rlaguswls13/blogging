import 'dotenv/config';
import { google } from 'googleapis';

async function main() {
  const clientId = process.env.BLOGGER_CLIENT_ID;
  const clientSecret = process.env.BLOGGER_CLIENT_SECRET;
  const refreshToken = process.env.BLOGGER_REFRESH_TOKEN;

  if (!clientId || !clientSecret || !refreshToken) {
    console.error('Error: Blogger API 설정을 .env 파일에 먼저 입력해 주세요.');
    console.error('필수 환경변수:');
    console.error('  - BLOGGER_CLIENT_ID');
    console.error('  - BLOGGER_CLIENT_SECRET');
    console.error('  - BLOGGER_REFRESH_TOKEN');
    process.exit(1);
  }

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
  oauth2Client.setCredentials({ refresh_token: refreshToken });

  const blogger = google.blogger('v3');
  
  // Accept custom URL or default to http://beji-tech.blogspot.com
  const blogUrl = process.argv[2] || 'http://beji-tech.blogspot.com';

  try {
    console.log(`Blogger API로 URL 조회 중: ${blogUrl}`);
    const res = await blogger.blogs.getByUrl({
      auth: oauth2Client,
      url: blogUrl
    });

    console.log('\n======================================');
    console.log('✅ 블로그 정보 조회 성공!');
    console.log(`- 블로그 이름: ${res.data.name}`);
    console.log(`- 블로그 ID (BLOGGER_BLOG_ID): ${res.data.id}`);
    console.log(`- 블로그 URL: ${res.data.url}`);
    console.log('======================================');
    console.log('\n위 BLOGGER_BLOG_ID를 .env 파일의 BLOGGER_BLOG_ID 항목에 입력하시면 됩니다.');
  } catch (error: any) {
    console.error('\n❌ 블로그 정보 조회 실패!');
    console.error('에러 메세지:', error.message || error);
    console.log('\n참고: Blogger 기본 도메인은 .blogspot.com 입니다. 커스텀 도메인을 사용하시는 경우 정확한 URL을 전달해 주세요.');
    console.log('예: npm run blogger:get-id -- https://your-custom-domain.com');
  }
}

main();
