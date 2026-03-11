
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://github.com/microsoft/playwright-cli');

  const description = await page.locator('p.f4.my-3').innerText();
  const stars = await page.locator('a[href$="/stargazers"] span.text-bold').innerText();

  const data = `Description: ${description}\nStars: ${stars}`;
  fs.writeFileSync('C:/Users/PC/teste-cline.txt', data);

  await browser.close();
})();
