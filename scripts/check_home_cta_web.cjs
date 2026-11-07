// Home manual-entry CTA geometry and keyboard accessibility at supported widths.
const assert = require('node:assert/strict')
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']})
  try {
    const results=[]
    for (const width of [375,390,768,1280,1440]) {
      const page=await browser.newPage({viewport:{width,height:900}})
      await page.route('**/api/status',r=>r.fulfill({json:{auth_mode:'demo'}}))
      await page.route('**/api/profile/**',r=>r.fulfill({json:{user_id:'web-demo-user',version:1,goal:'CTA geometry',allergies:[],hard_avoids:[],dislikes:[],consents:{}}}))
      await page.route('**/api/tasks?**',r=>r.fulfill({json:[]}))
      await page.goto(process.env.DIETLENS_PREVIEW_URL||'http://127.0.0.1:5174/')
      await page.getByRole('textbox',{name:'描述这一餐'}).waitFor()
      const button=page.getByRole('button',{name:'手动填写这一餐',exact:true})
      await button.waitFor({state:'visible'})
      const metrics=await button.evaluate(el=>{const rect=el.getBoundingClientRect();const parent=el.parentElement?.getBoundingClientRect();const style=getComputedStyle(el);return {width:rect.width,height:rect.height,parentWidth:parent?.width||0,whiteSpace:style.whiteSpace,overflow:style.overflow}})
      assert(metrics.width>=44 && metrics.width<=metrics.parentWidth+1,`invalid CTA width at ${width}: ${JSON.stringify(metrics)}`)
      assert(metrics.height<=60,`CTA wrapped vertically at ${width}: ${JSON.stringify(metrics)}`)
      assert.equal(metrics.whiteSpace,'nowrap')
      await button.focus(); assert.equal(await button.evaluate(el=>el===document.activeElement),true)
      results.push({viewport:width,...metrics})
      await page.close()
    }
    console.log(JSON.stringify({manualEntryCta:'passed',viewports:results}))
  } finally { await browser.close() }
})().catch(e=>{console.error(e);process.exit(1)})
