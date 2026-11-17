// Local HTTPS proxy for the existing Next.js app. No external tunnel or CA install.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const { X509Certificate } = require('node:crypto');

const directory = path.resolve(__dirname, '../.runtime/https');
const config = JSON.parse(fs.readFileSync(path.join(directory, 'config.json'), 'utf8'));
const target = new URL(config.upstream);
if (target.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname)) {
  throw new Error('The development proxy target must be local HTTP');
}
const certificate = fs.readFileSync(path.join(directory, 'server.crt'));
const ca = fs.readFileSync(path.join(directory, 'root-ca.crt'));
if (!new X509Certificate(certificate).checkIP(config.host)) throw new Error('Certificate does not match the LAN address');
const appUrl = `https://${config.host}:${config.httpsPort}`;
const setupUrl = `http://${config.host}:${config.setupPort}`;

function forwardHeaders(request) {
  return {
    ...request.headers,
    'x-forwarded-host': request.headers.host || config.host,
    'x-forwarded-proto': 'https',
  };
}

const secure = https.createServer({
  key: fs.readFileSync(path.join(directory, 'server.key')),
  cert: Buffer.concat([certificate, Buffer.from('\n'), ca]),
  minVersion: 'TLSv1.2',
}, (request, response) => {
  if (!request.url?.startsWith('/') || request.url.startsWith('//')) {
    response.writeHead(400); response.end(); return;
  }
  const upstream = http.request({
    hostname: target.hostname, port: target.port || 80, path: request.url,
    method: request.method, headers: forwardHeaders(request), timeout: 120_000,
  }, incoming => {
    response.writeHead(incoming.statusCode, incoming.headers);
    incoming.pipe(response);
  });
  upstream.on('error', () => {
    if (!response.headersSent) response.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Web server unavailable. Start Next.js on port 3000.');
  });
  upstream.on('timeout', () => upstream.destroy());
  response.on('close', () => { if (!response.writableFinished) upstream.destroy(); });
  request.pipe(upstream);
});

secure.on('upgrade', (request, client, head) => {
  if (!request.url?.startsWith('/') || request.url.startsWith('//')) { client.destroy(); return; }
  const upstream = net.connect(Number(target.port || 80), target.hostname, () => {
    const headers = Object.entries(forwardHeaders(request))
      .filter(([, value]) => value !== undefined)
      .map(([name, value]) => `${name}: ${Array.isArray(value) ? value.join(', ') : value}`);
    upstream.write([`${request.method} ${request.url} HTTP/${request.httpVersion}`, ...headers, '', ''].join(String.fromCharCode(13, 10)));
    if (head.length) upstream.write(head);
    client.pipe(upstream).pipe(client);
  });
  upstream.on('error', () => client.destroy());
  client.on('error', () => upstream.destroy());
  client.on('close', () => upstream.destroy());
});

const setupPage = `<!doctype html><html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>เตรียมมือถือสำหรับ G1 Thai</title><style>body{margin:0;padding:28px 22px;background:#071221;color:#edf4ff;font:16px/1.8 system-ui,sans-serif}main{max-width:620px;margin:20px auto}h1{font-size:26px}a{color:#9bc4ff}button{font:inherit}code{overflow-wrap:anywhere;font-size:12px}li{margin-bottom:16px}.action{display:inline-block;padding:10px 18px;border:1px solid #477ed0;border-radius:12px;text-decoration:none;background:#152c4b}</style>
<main><h1>เตรียมมือถือสำหรับ G1 Thai</h1><p>เชื่อมมือถือกับ Wi-Fi เดียวกับคอม แล้วทำตามขั้นตอนนี้</p><ol>
<li><a class="action" href="/g1-local-ca.cer">ดาวน์โหลดใบรับรองทดสอบ</a><p>ชื่อ: <strong>G1 Thai Local Test CA</strong> ใบรับรองนี้มีอายุ 7 วัน และทำให้เครื่องเชื่อถือใบรับรองที่สร้างจาก CA นี้ ใช้กับเครื่องทดสอบที่คุณไว้ใจ และลบออกหลังทดสอบ</p></li>
<li><strong>Android:</strong> เปิดการตั้งค่า ค้นหา “ติดตั้งใบรับรอง” เลือกใบรับรอง CA แล้วเลือกไฟล์ที่ดาวน์โหลด ชื่อเมนูขึ้นกับรุ่นมือถือ<br><strong>iPhone:</strong> ติดตั้งโปรไฟล์ใบรับรองจากการตั้งค่า จากนั้นไป ทั่วไป → เกี่ยวกับ → การตั้งค่าความเชื่อถือใบรับรอง แล้วเปิดความเชื่อถือให้ G1 Thai Local Test CA</li>
<li><a class="action" href="${appUrl}">เปิดเว็บ G1 ผ่าน HTTPS</a><p>หากยังมีคำเตือนใบรับรอง ให้ตรวจชื่อและการติดตั้งใบรับรองก่อนใช้ไมค์</p></li>
</ol><p><a href="https://support.apple.com/en-us/102390">วิธีของ Apple</a> · <a href="https://support.google.com/pixelphone/answer/2844832?hl=en">วิธีของ Android</a></p>
<p>SHA-256 ของใบรับรอง:<br><code>${config.caFingerprint}</code></p></main></html>`;

// This HTTP listener serves only setup instructions and the public CA certificate.
const setup = http.createServer((request, response) => {
  response.setHeader('Cache-Control', 'no-store');
  response.setHeader('X-Content-Type-Options', 'nosniff');
  if (request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405); response.end(); return; }
  if (request.url === '/g1-local-ca.cer') {
    const certificate = fs.readFileSync(path.join(directory, 'g1-local-ca.cer'));
    response.writeHead(200, { 'Content-Type': 'application/x-x509-ca-cert', 'Content-Disposition': 'attachment; filename="g1-local-ca.cer"', 'Content-Length': certificate.length });
    response.end(request.method === 'HEAD' ? undefined : certificate);
  } else if (request.url === '/') {
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end(request.method === 'HEAD' ? undefined : setupPage);
  } else { response.writeHead(404); response.end(); }
});

for (const server of [secure, setup]) {
  server.on('error', error => { console.error(error.message); process.exitCode = 1; secure.close(); setup.close(); });
}
// Connection metadata only: do not log microphone data, questions, or responses.
setup.on('connection', socket => console.log(`Setup connection: ${socket.remoteAddress}`));
secure.on('connection', socket => console.log(`HTTPS connection: ${socket.remoteAddress}`));
secure.on('tlsClientError', error => console.error(`TLS handshake: ${error.code || 'failed'}`));
secure.listen(config.httpsPort, config.host, () => console.log(`HTTPS: ${appUrl}`));
setup.listen(config.setupPort, config.host, () => console.log(`Phone setup: ${setupUrl}`));
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  secure.close(); setup.close(); setTimeout(() => process.exit(0), 1000).unref();
});
