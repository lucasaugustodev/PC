const { execSync } = require('child_process');
try {
  execSync('git add server/', { cwd: 'C:/Users/PC/hiveclip', stdio: 'inherit' });
  console.log('Git add completed');
} catch (e) {
  console.error('Error:', e.message);
}
