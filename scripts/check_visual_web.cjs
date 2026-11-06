// Deterministic rendering fixtures; this does not assert upstream source availability.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs');
const path=require('node:path');
const artifactRoot=process.env.DIETLENS_ARTIFACT_DIR||path.join(process.cwd(),'artifacts/dietlens-round-3');
const screenshotDir=process.env.DIETLENS_SCREENSHOT_DIR||'after';
fs.mkdirSync(path.join(artifactRoot,'after'),{recursive:true});
fs.mkdirSync(path.join(artifactRoot,'before'),{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/status',r=>r.fulfill({json:{auth_mode:'demo'}}));
 await page.route('**/api/profile/**',r=>r.fulfill({json:{user_id:'web-demo-user',goal:'合成视觉测试',version:1,consents:{review_history:true},allergies:[],hard_avoids:[],dislikes:[]}}));
 await page.route('**/api/tasks?**',r=>r.fulfill({json:Array.from({length:8},(_,i)=>({task_id:'fixture-task-'+i,state:['adopted','awaiting_confirmation','feedback','cancelled'][i%4],version:1,context:{meal:'午餐',options:['合成测试长名称鸡肉饭配时蔬和一份番茄鸡蛋面']},updated_at:'2026-11-04T06:00:00+00:00'}))}));
 await page.route('**/api/meal-records?**',r=>r.fulfill({json:Array.from({length:12},(_,i)=>({record_id:'fixture-record-'+i,user_id:'web-demo-user',meal_date:'2026-11-04',meal_slot:'lunch',name:`合成测试用餐 ${i+1} · 一份含有较长餐食名称说明的鸡肉蔬菜面`,quantity:i===0?null:1,unit:i===0?null:'份',source:'synthetic_visual_fixture',status:'active',version:1}))}));
 await page.route('**/api/inventory?**',r=>r.fulfill({json:Array.from({length:12},(_,i)=>({inventory_id:'fixture-'+i,ingredient_id:'fixture-'+i,name:`合成测试食材 ${i+1} · 含有较长规格说明的谷物食品`,quantity:i===0?0:500,unit:'g'}))}));
 await page.route('**/api/reviews?**',r=>r.fulfill({json:{plan:{planned_meals:4},actual:{recorded_meals:2},actions:{feedback_coverage:{value:.5},completion_among_feedback:{value:.5}},unknowns:[{kind:'unrecorded',message:'未记录的餐次保持未知。'}],next_steps:['从下一餐继续。']}}));
 await page.route('**/api/foods/search?**',r=>r.fulfill({json:{assessments:Array.from({length:20},(_,i)=>({record:{name:`合成测试谷物食品 ${i+1} · 含有较长品牌规格说明的燕麦产品`,source:'synthetic_visual_fixture',source_id:'fixture-'+i,nutrients:{protein_g_100g:12,fat_g_100g:8}},status:'needs_confirmation',reasons:['配料信息待确认'],unknown_fields:['ingredients']})),failures:{fixture_secondary:'timeout'},conflicts:[{field:'protein_g_100g'}]}}));
 const savedPlans=Array.from({length:8},(_,i)=>({plan_id:'visual-plan-'+i,user_id:'web-demo-user',start_date:`2026-11-${String(i+1).padStart(2,'0')}`,days:1,servings:1,version:2,status:i===0?'superseded':'confirmed',items:[{item_id:'lunch-'+i,meal_date:`2026-11-${String(i+1).padStart(2,'0')}`,meal_slot:'lunch',name:'合成视觉长名称鸡肉饭配时蔬与杂粮',ingredient_id:'鸡肉',ingredient_name:'鸡肉',quantity:200,unit:'g'}]}));
 await page.route('**/api/plans?**',r=>r.fulfill({json:savedPlans}));
 await page.route('**/api/plans/visual-plan-*',r=>r.fulfill({json:savedPlans.find(plan=>r.request().url().endsWith(plan.plan_id))}));
 await page.route('**/api/plans/visual-plan-*/shopping-list',r=>r.fulfill({json:{list_id:'visual-shopping',status:'active',items:[]}}));
 await page.route('**/api/shopping-lists/*/inventory-diff',r=>r.fulfill({json:[{item_id:'visual-chicken',name:'合成测试鸡肉配料长规格名称',quantity:200,unit:'g',needed:50}]}));
 const reports=[];
 const mobile = width => width <= 760;
 const openTool = async (label, width) => {
   if (!mobile(width)) {
     const navigation = label === '设置' ? page.locator('.sidebar-bottom > button') : page.locator('.side-nav button');
     await navigation.filter({hasText:label}).click();
     return;
   }
   if (['今日饮食','饮食计划','饮食回顾'].includes(label)) { await page.locator('.mobile-nav button').filter({hasText:label}).click(); return; }
   await page.locator('#mobile-more-trigger').click();
   await page.locator('#mobile-more-sheet').getByRole('button',{name:label,exact:true}).click();
 };
 for(const width of [1440,1280,768,390,375]){
  await page.setViewportSize({width,height:900});
  await page.goto(process.env.DIETLENS_PREVIEW_URL||'http://127.0.0.1:5174/');
  await page.getByRole('textbox',{name:'描述这一餐'}).waitFor();
  await page.screenshot({animations:'disabled',path:path.join(artifactRoot,screenshotDir,`dietlens-home-${width}.png`)});
  for(const [screen,label] of [['plan','饮食计划'],['saved-plans','饮食计划'],['inventory','食材库存'],['review','饮食回顾'],['journal','饮食回顾'],['food','食品资料'],['settings','设置']]){
   if(screen==='settings')await openTool('设置',width);
   else await openTool(label,width);
   if(screen==='food'){
    await page.getByRole('textbox',{name:'搜索食品'}).fill('测试燕麦');
    await page.getByRole('button',{name:'查资料',exact:true}).click();
    await page.locator('.food-card').first().waitFor();
   }
   if(screen==='review'){await page.getByRole('button',{name:'这段时间',exact:true}).click();await page.locator('.review-grid').waitFor();}
   if(screen==='journal'){await page.getByRole('button',{name:'用餐记录',exact:true}).click();await page.locator('.journal-list article').first().waitFor();}
   if(screen==='inventory')await page.locator('.inventory-item').first().waitFor();
   if(screen==='settings')await page.locator('.recent-tasks>button').first().waitFor();
   if(screen==='saved-plans'){await page.getByRole('button',{name:'已保存的计划',exact:true}).click();await page.locator('.saved-plan-list>button').first().waitFor();}
   const overflow=await page.locator('.drawer').evaluate(e=>e.scrollWidth>e.clientWidth+1);
   const pageOverflow=await page.evaluate(() => ({clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,clientHeight:document.documentElement.clientHeight}));
   if(pageOverflow.scrollWidth>pageOverflow.clientWidth+1)throw Error(`${screen} page overflow at ${width}px: ${JSON.stringify(pageOverflow)}`);
   if(overflow)throw Error(`${screen} overflow at ${width}px`);
   await page.screenshot({animations:'disabled',path:path.join(artifactRoot,'after',`dietlens-${screen}-${width}.png`)});
   reports.push({screen,width,overflow});
   if(screen==='saved-plans'){
    await page.locator('.saved-plan-list>button').filter({hasText:'当前版本'}).first().click();
    await page.getByRole('button',{name:'生成采购清单',exact:true}).click();
    await page.locator('.shopping-row').waitFor();
    if(await page.locator('.drawer').evaluate(e=>e.scrollWidth>e.clientWidth+1))throw Error('saved plan details overflow');
    await page.screenshot({animations:'disabled',path:path.join(artifactRoot,'after',`dietlens-saved-plan-detail-${width}.png`)});
   }
   if(screen==='settings'){await page.locator('.recent-tasks').scrollIntoViewIfNeeded();await page.screenshot({animations:'disabled',path:path.join(artifactRoot,'after',`dietlens-settings-recent-${width}.png`)});}
   if(screen==='journal'){
    await page.getByRole('button',{name:'记录已吃的一餐',exact:true}).click();
    await page.getByRole('textbox',{name:'实际餐食名称',exact:true}).fill('合成视觉测试晚餐');
    if(await page.locator('.drawer').evaluate(e=>e.scrollWidth>e.clientWidth+1))throw Error('journal form overflow');
    await page.screenshot({animations:'disabled',path:path.join(artifactRoot,'after',`dietlens-journal-form-${width}.png`)});
    await page.getByRole('button',{name:'取消填写',exact:true}).click();
   }
   await page.keyboard.press('Escape');
  }
 }
 if(errors.length)throw Error(errors.join(';'));
 console.log(JSON.stringify({screens:reports,pageErrors:errors}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
