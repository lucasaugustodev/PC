@echo off
cd /d C:\Users\PC\hiveclip
git status
echo ---
git add server/src/launcher-proxy.ts
echo ---
git commit -m "fix: simplify Express route path pattern for launcher proxy"
echo ---
git push
