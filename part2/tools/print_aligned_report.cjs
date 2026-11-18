const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {execFileSync} = require('node:child_process');

const {chromium} = require(process.argv[2] || 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1117-835-0_26.1117.835.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'final/原文配图整合');

async function main() {
  execFileSync('python', ['-X', 'utf8', path.join(__dirname, 'align_report_ui.py')], {stdio: 'inherit'});
  fs.mkdirSync(path.join(out, 'images'), {recursive: true});
  const browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 800}, deviceScaleFactor: 2});
    for (const name of ['care', 'food', 'plan', 'inventory', 'workbench', 'settings']) {
      await page.goto(pathToFileURL(path.join(out, '界面图源/html', `${name}.html`)).href);
      await page.evaluate(() => document.fonts.ready);
      const overflow = await page.locator('.dmain').evaluate(el => ({
        horizontal: el.scrollWidth - el.clientWidth, vertical: el.scrollHeight - el.clientHeight
      }));
      if (overflow.horizontal > 1 || overflow.vertical > 1) throw new Error(`${name} overflow ${JSON.stringify(overflow)}`);
      await page.locator('.desk').screenshot({path: path.join(out, 'images', `${name}.png`)});
    }
    execFileSync('python', ['-X', 'utf8', path.join(__dirname, 'format_source_report.py'), '--ui-v2'], {stdio: 'inherit'});
    await page.goto(pathToFileURL(path.join(out, '原文排版.html')).href);
    await page.evaluate(() => document.fonts.ready);
    const counts = await page.evaluate(() => [document.querySelectorAll('table').length,
      document.querySelectorAll('pre').length, document.querySelectorAll('math').length,
      [...document.images].filter(image => image.naturalWidth).length]);
    if (counts.join(',') !== '25,4,1,14') throw new Error(`报告对象数异常 ${counts}`);
    await page.pdf({path: path.join(root, 'DietLens_系统设计报告_原文配图整合版.pdf'),
      preferCSSPageSize: true, printBackground: true, outline: true});
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
