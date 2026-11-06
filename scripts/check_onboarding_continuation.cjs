// Synthetic demo user: onboarding -> failed model request -> manual continuation.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH, args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    const user = 'synthetic-continuation-' + Date.now();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/**', async route => {
      const req = route.request();
      if (/\/messages$/.test(req.url())) return route.fulfill({status:503,contentType:'application/json',body:'{}'});
      return route.continue({url:req.url().replaceAll('web-demo-user',user), ...(req.postData() ? {postData:req.postData().replaceAll('web-demo-user',user)} : {})});
    });
    await page.goto(process.env.DIETLENS_PREVIEW_URL || 'http://127.0.0.1:5174/');
    await page.locator('#setup-goal').fill('合成测试：简单安排这一餐');
    await page.getByRole('button',{name:/核对与确认/}).click();
    await page.getByRole('button',{name:'确认并进入',exact:true}).click();
    await page.getByRole('dialog').waitFor({state:'hidden'});
    await page.getByRole('textbox',{name:'描述这一餐'}).fill('午餐可选米饭和面条');
    await page.getByRole('button',{name:'发送消息',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'服务暂时不可用'}).waitFor();
    assert.equal(await page.getByRole('textbox',{name:'描述这一餐'}).inputValue(),'午餐可选米饭和面条');
    await page.getByRole('button',{name:'手动填写这一餐',exact:true}).click();
    await page.getByRole('textbox',{name:'餐次',exact:true}).fill('午餐');
    await page.getByRole('textbox',{name:'可选餐食',exact:true}).fill('、，,');
    assert(await page.getByRole('button',{name:'确认信息，看看下一步'}).isDisabled());
    await page.getByRole('textbox',{name:'可选餐食',exact:true}).fill('米饭、面条');
    await page.reload();
    await page.getByRole('textbox',{name:'可选餐食',exact:true}).waitFor();
    assert.equal(await page.getByRole('textbox',{name:'可选餐食',exact:true}).inputValue(),'米饭、面条');
    await page.getByRole('button',{name:'确认信息，看看下一步'}).click();
    await page.getByRole('button',{name:'选择这条路',exact:true}).first().click();
    await page.getByRole('button',{name:'做到了',exact:true}).click();
    await page.getByRole('heading',{name:'谢谢你回来告诉我'}).waitFor();
    assert.deepEqual(errors,[]);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false);
    console.log(JSON.stringify({onboardingContinuation:'passed',modelFailureManualRecovery:'passed',draftReload:'passed',selectionAndFeedback:'passed',pageErrors:errors}));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode=1; });
