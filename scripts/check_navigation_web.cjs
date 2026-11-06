// Verify actual mobile viewport behavior and browser history using a synthetic user.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH, args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const user = 'synthetic-navigation-' + Date.now();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/**', async route => {
      const req = route.request();
      await route.continue({url:req.url().replaceAll('web-demo-user',user), ...(req.postData() ? {postData:req.postData().replaceAll('web-demo-user',user)} : {})});
    });
    const base = process.env.DIETLENS_PREVIEW_URL || 'http://127.0.0.1:5174/';
    await page.goto(base + '#inventory');
    await page.locator('#setup-goal').fill('合成导航测试');
    assert.equal(await page.getByRole('dialog').count(),1);
    await page.getByRole('button',{name:/核对与确认/}).click();
    await page.getByRole('button',{name:'确认并进入',exact:true}).click();
    await page.getByRole('dialog',{name:'食材库存',exact:true}).waitFor();
    assert.equal(await page.evaluate(() => innerWidth),390);
    assert.equal(await page.evaluate(() => document.compatMode),'CSS1Compat');
    assert.equal(await page.locator('html').getAttribute('lang'),'zh-CN');
    const tools = page.getByRole('navigation',{name:'切换工具'});
    await page.getByRole('textbox',{name:'食材名称',exact:true}).fill('导航草稿燕麦');
    await page.getByRole('textbox',{name:'库存数量',exact:true}).fill('300');
    await tools.getByRole('button',{name:'饮食计划',exact:true}).click();
    await page.getByRole('textbox',{name:'午餐名称',exact:true}).fill('导航草稿午餐');
    await tools.getByRole('button',{name:'食材库存',exact:true}).click();
    assert.equal(await page.getByRole('textbox',{name:'食材名称',exact:true}).inputValue(),'导航草稿燕麦');
    await page.goBack();
    await page.getByRole('dialog',{name:'饮食计划',exact:true}).waitFor();
    assert.equal(await page.getByRole('textbox',{name:'午餐名称',exact:true}).inputValue(),'导航草稿午餐');
    await page.goForward();
    await page.getByRole('dialog',{name:'食材库存',exact:true}).waitFor();
    await page.reload();
    await page.getByRole('dialog',{name:'食材库存',exact:true}).waitFor();
    assert.equal(await page.title(),'食材库存 · DietLens');
    assert.equal(await page.getByRole('textbox',{name:'库存数量',exact:true}).inputValue(),'300');
    assert.equal(await page.locator('.sidebar').getAttribute('inert'),'');
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({state:'hidden'});
    assert.equal(new URL(page.url()).hash,'');
    await page.goBack();
    await page.getByRole('dialog',{name:'食材库存',exact:true}).waitFor();
    for (const label of ['食品资料','饮食回顾','设置']) {
      await tools.getByRole('button',{name:label,exact:true}).click();
      await page.getByRole('dialog',{name:label,exact:true}).waitFor();
      assert.equal(await page.locator('.drawer').evaluate(e => e.scrollWidth > e.clientWidth+1),false);
      await page.screenshot({path:`/tmp/dietlens-navigation-${label}.png`});
    }
    await page.getByRole('button',{name:'编辑档案与授权',exact:true}).click();
    await page.locator('#setup-goal').waitFor();
    assert.equal(await page.getByRole('dialog').count(),1);
    assert.equal(new URL(page.url()).hash,'#settings');
    await page.getByRole('button',{name:'稍后设置',exact:true}).click();
    await page.getByRole('dialog',{name:'设置',exact:true}).waitFor();
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({state:'hidden'});
    await page.locator('.side-nav button').filter({hasText:'饮食计划'}).click();
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(() => document.activeElement?.textContent?.includes('饮食计划')),true);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({mobileViewport:'passed',deepLinkOnboarding:'passed',browserHistory:'passed',refreshAndDrafts:'passed',singleModal:'passed',focusRestoration:'passed',pageErrors:errors}));
  } finally { await browser.close(); }
})().catch(e => {console.error(e);process.exitCode=1});
