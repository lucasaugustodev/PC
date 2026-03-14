const { execSync } = require('child_process');
const path = require('path');

const cwd = 'C:/Users/PC/hiveclip';

try {
  console.log('=== Git Status ===');
  const status = execSync('git status', { cwd, encoding: 'utf8' });
  console.log(status);
  
  console.log('\n=== Git Diff (staged) ===');
  try {
    const diffStaged = execSync('git diff --staged --name-only', { cwd, encoding: 'utf8' });
    console.log('Staged files:', diffStaged || '(none)');
  } catch (e) {
    console.log('No staged changes');
  }
  
  console.log('\n=== Git Diff (unstaged) ===');
  try {
    const diffUnstaged = execSync('git diff --name-only', { cwd, encoding: 'utf8' });
    console.log('Unstaged files:', diffUnstaged || '(none)');
  } catch (e) {
    console.log('No unstaged changes');
  }
  
  console.log('\n=== Git Log (last 5) ===');
  const log = execSync('git log --oneline -5', { cwd, encoding: 'utf8' });
  console.log(log);
  
  console.log('\n=== Git Remote -v ===');
  try {
    const remote = execSync('git remote -v', { cwd, encoding: 'utf8' });
    console.log(remote);
  } catch (e) {
    console.log('No remote configured');
  }
  
} catch (e) {
  console.error('Error:', e.message);
  console.error(e.stdout);
  console.error(e.stderr);
}
