import subprocess
import os

os.chdir('C:/Users/PC/hiveclip')

try:
    print('=== Git Status ===')
    result = subprocess.run(['git', 'status'], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print('STDERR:', result.stderr)
    
    print('\n=== Git Diff (staged) ===')
    result = subprocess.run(['git', 'diff', '--staged', '--name-only'], capture_output=True, text=True)
    print('Staged files:', result.stdout.strip() or '(none)')
    
    print('\n=== Git Diff (unstaged) ===')
    result = subprocess.run(['git', 'diff', '--name-only'], capture_output=True, text=True)
    print('Unstaged files:', result.stdout.strip() or '(none)')
    
    print('\n=== Git Log (last 5) ===')
    result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
    print(result.stdout)
    
    print('\n=== Git Remote -v ===')
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
    print(result.stdout or 'No remote')
    
except Exception as e:
    print(f'Error: {e}')
