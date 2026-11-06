// Auth UI fixtures only: no emails or real account operations are sent.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.DIETLENS_PREVIEW_URL || 'http://127.0.0.1:5174/';
(async () => {
 const browser = await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {}),args:['--no-sandbox']});
 const context = await browser.newContext();
 const page = await context.newPage();
 const errors=[]; page.on('pageerror', error => errors.push(error.message));
 let profileCalls=0, failOtp=true;
 await page.route('**/api/status',route=>route.fulfill({json:{auth_mode:'supabase'}}));
 await page.route('**/api/profile/**',route=>{profileCalls++;return route.fulfill({status:401,json:{detail:{code:'authentication_required'}}})});
 await page.route('**/auth/v1/otp**',route=>{
   if(failOtp){failOtp=false;return route.fulfill({status:503,json:{message:'fixture unavailable'}})}
   return route.fulfill({status:200,json:{}});
 });
 await page.goto(base);
 await page.getByRole('button',{name:'发送登录链接',exact:true}).waitFor();
 if(profileCalls)throw Error('unauthenticated user entered profile workflow');
 await page.getByRole('textbox',{name:'邮箱',exact:true}).fill('synthetic@example.invalid');
 await page.getByRole('button',{name:'发送登录链接',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'登录链接暂时无法发送'}).waitFor();
 await page.getByRole('button',{name:'发送登录链接',exact:true}).click();
 await page.getByRole('status').filter({hasText:'登录链接已发送到'}).waitFor();
 if(!await page.getByRole('button',{name:/秒后可重发/}).isDisabled())throw Error('no resend cooldown');
 await page.getByRole('button',{name:'修改邮箱'}).click();
 if(await page.getByRole('textbox',{name:'邮箱'}).inputValue()!=='synthetic@example.invalid')throw Error('email input lost');
 // Populate two distinct synthetic sessions through SDK's local storage format.
 const config = require('fs').readFileSync(require('path').join(__dirname,'../web/.env'),'utf8');
 const url = config.match(/^VITE_SUPABASE_URL=(.*)$/m)?.[1]?.trim();
 if(!url)throw Error('Supabase test URL required');
 const storageKey='sb-'+new URL(url).hostname.split('.')[0]+'-auth-token';
 const makeSession=id=>{
   const exp=Math.floor(Date.now()/1000)+7200;
   const token=[{alg:'HS256',typ:'JWT'},{sub:id,exp,role:'authenticated'},'fixture'].map((v,i)=>i===2?v:Buffer.from(JSON.stringify(v)).toString('base64url')).join('.');
   return {access_token:token,refresh_token:'fixture-refresh',token_type:'bearer',expires_in:7200,expires_at:exp,user:{id,email:id+'@example.invalid',aud:'authenticated',role:'authenticated',app_metadata:{},user_metadata:{},created_at:new Date().toISOString()}};
 };
 await page.unroute('**/api/profile/**');
 await page.route('**/api/profile/**',route=>route.fulfill({json:{user_id:decodeURIComponent(route.request().url().split('/').pop()),version:1,goal:'测试档案',consents:{},allergies:[],dislikes:[],hard_avoids:[]}}));
 await page.route('**/api/tasks?**',route=>route.fulfill({json:[]}));
 await page.route('**/auth/v1/logout**',route=>route.fulfill({status:204}));
 await page.evaluate(({key,session})=>localStorage.setItem(key,JSON.stringify(session)),{key:storageKey,session:makeSession('fixture-user-a')});
 await page.reload();
 await page.getByRole('textbox',{name:'描述这一餐'}).fill('用户 A 未发送的内容');
 await page.evaluate(({key,session})=>localStorage.setItem(key,JSON.stringify(session)),{key:storageKey,session:makeSession('fixture-user-b')});
 await page.reload();
 await page.getByRole('textbox',{name:'描述这一餐'}).waitFor();
 if(await page.getByRole('textbox',{name:'描述这一餐'}).inputValue())throw Error('account draft leaked');
 await page.locator('.sidebar-bottom>button').click();
 await page.getByRole('button',{name:'退出登录'}).click();
 await page.getByRole('button',{name:'发送登录链接',exact:true}).waitFor();
 if(await page.evaluate(()=>Object.keys(sessionStorage).some(key=>key.startsWith('dietlens:fixture-user-b:'))))throw Error('signed-out draft remains');
 if(errors.length)throw Error(errors.join(';'));
 console.log(JSON.stringify({loginRequired:'passed',otpFailureRetry:'passed (fixture)',resendCooldown:'passed',accountIsolation:'passed (fixture sessions)',signOut:'passed (fixture endpoint)',pageErrors:errors}));
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
