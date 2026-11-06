// Async deletion regression: the topmost dialog owns Escape and focus while all actions are disabled.
const assert = require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
async function setup(page){
  await page.route('**/api/status',r=>r.fulfill({json:{auth_mode:'demo'}}));
  await page.route('**/api/profile/**',r=>r.fulfill({json:{user_id:'web-demo-user',version:1,goal:'删除测试',allergies:[],hard_avoids:[],dislikes:[],consents:{}}}));
  await page.route('**/api/tasks?**',r=>r.fulfill({json:[]}));
  await page.goto(process.env.DIETLENS_PREVIEW_URL||'http://127.0.0.1:5174/');
  await page.getByRole('textbox',{name:'描述这一餐'}).waitFor();
  await page.locator('.sidebar-bottom > button').click();
  await page.getByRole('button',{name:'删除全部数据',exact:true}).click();
  await page.getByRole('dialog',{name:'删除当前账号的全部数据？',exact:true}).waitFor();
}
(async()=>{
  const browser=await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
  try {
    const success=await browser.newPage({viewport:{width:1440,height:900}}); let releaseSuccess; const successGate=new Promise(resolve=>releaseSuccess=resolve);
    await setup(success);
    await success.route('**/api/delete',async route=>{await successGate;await route.fulfill({json:{deleted:true}})});
    await success.getByRole('button',{name:'确认删除',exact:true}).click();
    await success.getByRole('button',{name:'正在删除…',exact:true}).waitFor();
    await success.keyboard.press('Tab'); await success.keyboard.press('Shift+Tab'); await success.keyboard.press('Escape');
    assert.equal(await success.getByRole('dialog',{name:'删除当前账号的全部数据？',exact:true}).count(),1);
    assert.equal(await success.getByRole('dialog',{name:'设置 · 当前情境',exact:true}).count(),1);
    releaseSuccess();
    await success.locator('.onboarding-drawer').waitFor();
    const failure=await browser.newPage({viewport:{width:1440,height:900}}); let releaseFailure; const failureGate=new Promise(resolve=>releaseFailure=resolve);
    await setup(failure);
    await failure.route('**/api/delete',async route=>{await failureGate;await route.fulfill({status:503,json:{detail:'temporary failure'}})});
    await failure.getByRole('button',{name:'确认删除',exact:true}).click();
    await failure.getByRole('button',{name:'正在删除…',exact:true}).waitFor();
    await failure.keyboard.press('Tab'); await failure.keyboard.press('Shift+Tab'); await failure.keyboard.press('Escape'); releaseFailure();
    await failure.getByRole('alert').waitFor();
    assert.equal(await failure.getByRole('dialog',{name:'删除当前账号的全部数据？',exact:true}).count(),1);
    assert.equal(await failure.getByRole('dialog',{name:'设置 · 当前情境',exact:true}).count(),1);
    console.log(JSON.stringify({busyTabWrap:'passed',busyShiftTabWrap:'passed',busyEscapeConsumed:'passed',successFlow:'passed',failurePreservesModal:'passed'}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
