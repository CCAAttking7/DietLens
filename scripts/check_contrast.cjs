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
console.log(JSON.stringify({source:'web/src/styles/design-system.css :root', standard:'WCAG AA normal text', pairs:results, pass:true}, null, 2))
