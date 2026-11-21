// WCAG contrast gate sourced from the authoritative CSS custom properties.
const fs = require('node:fs')
const assert = require('node:assert/strict')
const css = fs.readFileSync('web/src/styles/design-system.css', 'utf8')
const root = css.match(/:root\s*\{([\s\S]*?)\}/)?.[1] ?? ''
const tokens = Object.fromEntries([...root.matchAll(/--([\w-]+)\s*:\s*(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\s*;/g)].map(match => [match[1], match[2]]))
const required = ['ink','ink-muted','ink-faint','brand','brand-strong','success','warning','danger','info','bg','surface','surface-subtle','brand-soft']
for (const name of required) assert(tokens[name], `Missing CSS source token --${name}`)
const luminance = hex => {
  const value = hex.length === 4 ? hex.slice(1).split('').map(char => char + char).join('') : hex.slice(1)
  const rgb = [0,2,4].map(index => parseInt(value.slice(index,index+2),16)/255).map(channel => channel <= .04045 ? channel/12.92 : ((channel+.055)/1.055)**2.4)
  return .2126*rgb[0] + .7152*rgb[1] + .0722*rgb[2]
}
const contrast = (foreground, background) => {
  const a=luminance(foreground), b=luminance(background)
  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)
}
const pairs = [
  ['ink','bg'],['ink','surface'],['ink-muted','bg'],['ink-muted','surface'],['ink-muted','surface-subtle'],['ink-muted','brand-soft'],
  ['ink-faint','bg'],['ink-faint','surface'],['ink-faint','surface-subtle'],['ink-faint','brand-soft'],
  ['brand-strong','bg'],['brand-strong','surface'],['brand','surface'],['success','bg'],['success','surface'],['success','surface-subtle'],
  ['warning','bg'],['warning','surface'],['warning','surface-subtle'],['info','bg'],['info','surface'],['info','surface-subtle'],
  ['danger','bg'],['danger','surface'],['danger','surface-subtle'],
]
const results = pairs.map(([foreground,background]) => ({foreground,background,ratio:Number(contrast(tokens[foreground],tokens[background]).toFixed(2))}))
const failures = results.filter(item => item.ratio < 4.5)
if (failures.length) { console.error(JSON.stringify({failures}, null, 2)); process.exit(1) }
const resolveColor = value => {
  let resolved = value.trim()
  const seen = new Set()
  while (resolved.startsWith('var(')) {
    const name = resolved.match(/^var\((--[\w-]+)\)$/)?.[1]
    assert(name && !seen.has(name), `Unable to resolve CSS color ${value}`)
    seen.add(name)
    resolved = tokens[name.slice(2)]
    assert(resolved, `Missing CSS source token ${name}`)
  }
  return resolved
}
const selectorBlock = selector => {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = css.match(new RegExp(`${escaped}[^{}]*\\{([^{}]*)\\}`))
  assert(match, `Missing required CSS selector ${selector}`)
  return match[1]
}
const declaration = (block, property, selector) => {
  const match = block.match(new RegExp(`${property}\\s*:\\s*([^;]+)`))
  assert(match, `Missing ${property} declaration for ${selector}`)
  return resolveColor(match[1])
}
const buttonPairs = [
  ['white / primary button', '.button-primary', '#fff', 'background'],
  ['white / destructive button', '.button-destructive', '#fff', 'background'],
  ['normal text / secondary surface', '.button-secondary', 'color', 'background'],
].map(([name, selector, foreground, background]) => {
  const block = selectorBlock(selector)
  const foregroundColor = foreground.startsWith('#') ? foreground : declaration(block, foreground, selector)
  const backgroundColor = declaration(block, background, selector)
  return {name, selector, foreground:foregroundColor, background:backgroundColor, ratio:Number(contrast(foregroundColor, backgroundColor).toFixed(2))}
})
const buttonFailures = buttonPairs.filter(item => item.ratio < 4.5)
if (buttonFailures.length) { console.error(JSON.stringify({buttonFailures}, null, 2)); process.exit(1) }
console.log(JSON.stringify({source:'web/src/styles/design-system.css :root and semantic button selectors', standard:'WCAG AA normal text', pairs:results, buttonPairs, pass:true}, null, 2))
