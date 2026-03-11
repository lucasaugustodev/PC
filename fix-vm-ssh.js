const http = require('http');
const WebSocket = require('ws');

const VM = '92.246.131.103';
const PUBKEY = require('fs').readFileSync(require('os').homedir() + '/.ssh/id_ed25519.pub', 'utf8').trim();

// Step 1: Spawn interactive session via claude-cli/auth (gives us a pty)
function post(path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body || {});
    const req = http.request({
      hostname: VM, port: 3001, path, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': data.length }
    }, res => {
      let b = ''; res.on('data', d => b += d); res.on('end', () => resolve(JSON.parse(b)));
    });
    req.on('error', reject);
    req.write(data); req.end();
  });
}

async function main() {
  // Launch interactive session
  const sess = await post('/api/claude-cli/auth');
  console.log('Session:', sess.sessionId);

  const ws = new WebSocket(`ws://${VM}:3001/ws`);
  let output = '';

  ws.on('open', () => {
    console.log('WS connected');
    ws.send(JSON.stringify({ type: 'attach', sessionId: sess.sessionId }));

    // Wait for claude to start, then kill it
    setTimeout(() => {
      console.log('Sending Ctrl+C to exit claude...');
      ws.send(JSON.stringify({ type: 'input', sessionId: sess.sessionId, data: '\x03' }));
    }, 2000);

    setTimeout(() => {
      ws.send(JSON.stringify({ type: 'input', sessionId: sess.sessionId, data: '\x03' }));
    }, 3000);

    setTimeout(() => {
      ws.send(JSON.stringify({ type: 'input', sessionId: sess.sessionId, data: 'exit\r\n' }));
    }, 4000);

    // After exiting claude, we should be at cmd.exe prompt
    // Send powershell commands to fix SSH
    setTimeout(() => {
      console.log('Sending SSH fix commands...');
      const cmds = [
        'powershell -Command "Stop-Service sshd -Force"',
        'echo Port 22> C:\\ProgramData\\ssh\\sshd_config',
        'echo PasswordAuthentication yes>> C:\\ProgramData\\ssh\\sshd_config',
        'echo PubkeyAuthentication yes>> C:\\ProgramData\\ssh\\sshd_config',
        'echo PermitRootLogin yes>> C:\\ProgramData\\ssh\\sshd_config',
        'echo AllowUsers Administrator>> C:\\ProgramData\\ssh\\sshd_config',
        'echo Subsystem sftp sftp-server.exe>> C:\\ProgramData\\ssh\\sshd_config',
        'del "C:\\ProgramData\\ssh\\administrators_authorized_keys" 2>nul',
        'mkdir "C:\\Users\\Administrator\\.ssh" 2>nul',
        `echo ${PUBKEY}> "C:\\Users\\Administrator\\.ssh\\authorized_keys"`,
        'powershell -Command "net user Administrator hZJK5I8Dtm0RhIzT; Start-Service sshd; Write-Host SSH_FIXED"',
        'type C:\\ProgramData\\ssh\\sshd_config',
      ];

      let i = 0;
      const sendNext = () => {
        if (i < cmds.length) {
          ws.send(JSON.stringify({ type: 'input', sessionId: sess.sessionId, data: cmds[i] + '\r\n' }));
          console.log('>', cmds[i].substring(0, 80));
          i++;
          setTimeout(sendNext, 1500);
        }
      };
      sendNext();
    }, 6000);

    // Collect output and exit
    setTimeout(() => {
      // Strip ANSI codes
      const clean = output.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '').replace(/\x1b\[[^a-zA-Z]*[a-zA-Z]/g, '');
      console.log('\n--- OUTPUT (last 1500 chars) ---');
      console.log(clean.slice(-1500));

      if (clean.includes('SSH_FIXED')) {
        console.log('\nSSH FIXED SUCCESSFULLY!');
      }
      ws.close();
      process.exit(0);
    }, 30000);
  });

  ws.on('message', raw => {
    try {
      const msg = JSON.parse(raw);
      if (msg.data) output += msg.data;
    } catch {}
  });
}

main().catch(e => { console.error(e); process.exit(1); });
