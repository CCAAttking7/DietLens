// Mobile More Sheet regression: semantic dialog, focus trap, Escape, restoration and safe-area layout.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
  const browser=await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}), args:['--no-sandbox']});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    await page.route('**/api/status',r=>r.fulfill({json:{auth_mode:'demo'}}));
    await page.route('**/api/profile/**',r=>r.fulfill({json:{user_id:'web-demo-user',version:1,goal:'移动导航测试',allergies:[],hard_avoids:[],dislikes:[],consents:{}}}));
    await page.goto(process.env.DIETLENS_PREVIEW_URL||'http://127.0.0.1:5174/');
    await page.getByRole('textbox',{name:'描述这一餐'}).waitFor();
    const trigger=page.locator('#mobile-more-trigger');
    await page.evaluate(() => window.scrollTo(0, 120));
    const scrollBefore=await page.evaluate(() => window.scrollY);
    await trigger.click();
    assert.equal(await trigger.getAttribute('aria-expanded'),'true');
    const sheet=page.getByRole('dialog',{name:'更多页面'});
    await sheet.waitFor();
    assert.equal(await sheet.getAttribute('aria-modal'),'true');
    assert.equal(await page.locator('#mobile-more-sheet').count(),1);
    assert.equal(await page.locator('.sidebar').getAttribute('inert'),'');
    assert.equal(await page.locator('.main-stage').getAttribute('inert'),'');
    assert.equal(await page.locator('.mobile-nav').getAttribute('inert'),'');
    assert.equal(await page.evaluate(() => document.body.style.overflow),'hidden');
    assert.equal(await page.getByRole('button',{name:'关闭更多页面'}).evaluate(el=>el===document.activeElement),true);
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    assert.equal(await sheet.evaluate(el=>el.contains(document.activeElement)),true);
    await page.keyboard.press('Shift+Tab');
    assert.equal(await sheet.evaluate(el=>el.contains(document.activeElement)),true);
    await page.keyboard.press('Escape');
    await sheet.waitFor({state:'hidden'});
    assert.equal(await trigger.getAttribute('aria-expanded'),'false');
    assert.equal(await trigger.evaluate(el=>el===document.activeElement),true);
    assert.equal(await page.evaluate(() => document.body.style.overflow),'');
    assert.equal(await page.evaluate(expected => Math.abs(window.scrollY-expected)<2, scrollBefore),true);
    await trigger.click();
    await page.locator('.mobile-more-sheet').click({position:{x:5,y:5}});
    await sheet.waitFor({state:'hidden'});
    assert.equal(await trigger.getAttribute('aria-expanded'),'false');
    for (const label of ['食品资料','食材库存','设置']) {
      await trigger.click();
      await page.getByRole('button',{name:label,exact:true}).click();
      await page.getByRole('dialog',{name:`${label} · 当前情境`}).waitFor();
      assert.equal(await page.locator('.mobile-nav').evaluate(el=>getComputedStyle(el).display),'none');
      await page.getByRole('button',{name:'关闭面板',exact:true}).click();
      await page.getByRole('textbox',{name:'描述这一餐'}).waitFor();
      assert.equal(await trigger.evaluate(el=>el===document.activeElement),true);
    }
    console.log(JSON.stringify({moreSheetSemantics:'passed',focusTrap:'passed',reverseFocusTrap:'passed',escape:'passed',focusRestoration:'passed',routeFocusRestoration:'passed',scrollLock:'passed',backdrop:'passed',drawerIsolation:'passed'}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
