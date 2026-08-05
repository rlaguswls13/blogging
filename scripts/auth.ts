import 'dotenv/config';
import http from 'node:http';
import url from 'node:url';
import fs from 'node:fs/promises';
import path from 'node:path';
import { exec } from 'node:child_process';
import { google } from 'googleapis';

const PORT = 8080;
const REDIRECT_URI = `http://localhost:${PORT}/oauth2callback`;

async function main() {
  const clientId = process.env.BLOGGER_CLIENT_ID;
  const clientSecret = process.env.BLOGGER_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    console.error('Error: .env 파일에 BLOGGER_CLIENT_ID와 BLOGGER_CLIENT_SECRET을 먼저 입력해 주세요.');
    process.exit(1);
  }

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret, REDIRECT_URI);

  // Generate auth URL
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline', // Required to get a refresh token
    scope: ['https://www.googleapis.com/auth/blogger'],
    prompt: 'consent',       // Force consent screen to always get a refresh token
  });

  // Start local server to listen for redirect
  const server = http.createServer(async (req, res) => {
    const reqUrl = url.parse(req.url || '', true);

    if (reqUrl.pathname === '/oauth2callback') {
      const code = reqUrl.query.code as string;
      const error = reqUrl.query.error as string;

      if (error) {
        res.writeHead(400, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`<h1>인증 실패</h1><p>에러 발생: ${error}</p>`);
        console.error(`인증 에러: ${error}`);
        server.close();
        process.exit(1);
      }

      if (code) {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end('<h1>인증 성공!</h1><p>터미널로 돌아가 인증 완료 결과를 확인하고 이 창을 닫으셔도 됩니다.</p>');
        
        try {
          console.log('Authorization code 수신 완료. Token 교환 중...');
          const { tokens } = await oauth2Client.getToken(code);
          const refreshToken = tokens.refresh_token;

          if (!refreshToken) {
            console.warn('\n⚠️ 경고: Refresh Token이 발급되지 않았습니다.');
            console.warn('이미 권한 동의를 마친 계정일 수 있습니다. 구글 계정 보안 설정에서 해당 앱의 접근 권한을 삭제하고 다시 시도하시거나, prompt: consent 설정을 확인하세요.');
          } else {
            console.log('\n✅ Refresh Token 획득 성공!');
            await updateEnvFile(refreshToken);
          }
        } catch (err: any) {
          console.error('토큰 교환 실패:', err.message || err);
        } finally {
          server.close();
          console.log('\n로컬 인증 서버가 종료되었습니다.');
          process.exit(0);
        }
      }
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  server.listen(PORT, () => {
    console.log(`\n======================================================`);
    console.log(`🔑 구글 Blogger OAuth 인증 프로세스 시작`);
    console.log(`- 대기 포트: ${PORT}`);
    console.log(`- 리디렉션 URI: ${REDIRECT_URI}`);
    console.log(`⚠️ Google Cloud Console 사용자 인증 정보에서 아래 주소를 '승인된 리디렉션 URI'에 추가해 주어야 합니다:`);
    console.log(`  => ${REDIRECT_URI}`);
    console.log(`======================================================\n`);
    console.log('브라우저를 열어 구글 로그인창으로 이동합니다...');
    
    // Open system browser (using powershell for Windows stability)
    exec(`powershell -Command "Start-Process '${authUrl}'"`);
  });
}

async function updateEnvFile(refreshToken: string) {
  const envPath = path.resolve(process.cwd(), '.env');
  let content = '';
  
  try {
    content = await fs.readFile(envPath, 'utf8');
  } catch {
    // If .env doesn't exist, create it
    content = '';
  }

  const tokenPattern = /^BLOGGER_REFRESH_TOKEN=.*$/m;
  const newTokenLine = `BLOGGER_REFRESH_TOKEN=${refreshToken}`;

  if (tokenPattern.test(content)) {
    // Replace existing token line
    content = content.replace(tokenPattern, newTokenLine);
  } else {
    // Append to file
    content += `\n${newTokenLine}\n`;
  }

  await fs.writeFile(envPath, content, 'utf8');
  console.log('✅ .env 파일에 BLOGGER_REFRESH_TOKEN이 자동으로 업데이트되었습니다!');
}

main();
