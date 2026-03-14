@echo off
cd /d C:\Users\PC\hiveclip
git status > git-status.txt 2>&1
git diff --staged --name-only > git-staged.txt 2>&1
git diff --name-only > git-unstaged.txt 2>&1
echo Done
