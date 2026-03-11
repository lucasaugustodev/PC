const { chromium } = require('playwright');

(async () => {
  // Launch chromium with headless: true
  const browser = await chromium.launch({ headless: true });
  
  // Create a new page
  const page = await browser.newPage();
  
  // Navigate to the URL
  await page.goto('https://minivps.com.br/');
  
  // Wait for the page to load
  await page.waitForLoadState('domcontentloaded');
  
  // Take a full page screenshot and save to the specified path
  await page.screenshot({ 
    path: 'C:/Users/PC/minivps_screenshot.png', 
    fullPage: true 
  });
  
  // Close the browser
  await browser.close();
  
  console.log('Screenshot saved to C:/Users/PC/minivps_screenshot.png');
})();
