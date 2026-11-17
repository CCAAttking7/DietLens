const fs=require('fs');const path=require('path');
const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{const out=path.resolve(__dirname,'../final/视觉整合版');
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage({viewport:{width:1200,height:820},deviceScaleFactor:1.5});
 for(const name of ['care','food','plan','inventory','meal','action','workbench','settings']){
  await page.goto('file:///'+path.join(out,name+'.html').replaceAll('\\','/'));
  if(name==='inventory')await page.addStyleTag({content:'.main{padding-top:20px}.main h1{font-size:32px}.main .paper{padding:18px}.main .table td{padding:10px}.main p{margin-bottom:10px}'});
  if(name==='action')await page.evaluate(()=>{const label=[...document.querySelectorAll('.label')].find(x=>x.textContent==='稍后反馈');if(label)label.textContent='采纳后开放：执行反馈';});
  const metrics=await page.locator('.main').evaluate(el=>({页面:el.clientHeight,内容:el.scrollHeight}));console.log(name,JSON.stringify(metrics));
  await page.screenshot({path:path.join(out,name+'.png')});
 }
 await page.setContent('<html><meta charset="utf-8"><body></body></html>');
 await page.addScriptTag({path:path.join(out,'mermaid.min.js')});
 await page.evaluate(()=>mermaid.initialize({startOnLoad:false,securityLevel:'loose',theme:'base',themeVariables:{fontFamily:'SimSun',primaryColor:'#ffffff',primaryTextColor:'#000000',primaryBorderColor:'#000000',lineColor:'#000000',secondaryColor:'#ffffff',tertiaryColor:'#ffffff',fontSize:'18px'},flowchart:{htmlLabels:false,useMaxWidth:false},sequence:{useMaxWidth:false,actorFontSize:18,messageFontSize:16,noteFontSize:16},class:{useMaxWidth:false}}));
 for(const file of fs.readdirSync(out).filter(n=>n.endsWith('.mmd'))){
  const txt=fs.readFileSync(path.join(out,file),'utf8');
  const svg=await page.evaluate(async txt=>(await mermaid.render('model'+Math.random().toString(36).slice(2),txt)).svg,txt);
  fs.writeFileSync(path.join(out,file.replace('.mmd','.svg')),svg);
  await page.locator('body').evaluate((el,s)=>el.innerHTML=s,svg);
  await page.locator('svg').screenshot({path:path.join(out,file.replace('.mmd','.png'))});
 }
 await browser.close();console.log('已渲染八个界面与八张设计模型。');
})().catch(e=>{console.error(e);process.exit(1)});
