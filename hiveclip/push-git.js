const { execSync } = require('child_process');
try {
  console.log('Running git push...');
  execSync('git push', { cwd: 'C:/Users/PC/hiveclip', stdio: 'inherit' });
  console.log('Git push completed successfully');
} catch (e) {
  console.error('Error:', e.message);
  process.exit(1);
}
