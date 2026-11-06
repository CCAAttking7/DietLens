// Token-pair WCAG contrast gate. This checks actual foreground/background combinations used by DietLens states.
const assert = require('node:assert/strict');
const tokens = {
  ink: '#24231f', muted: '#625c56', faint: '#655f58', brand: '#b24e32', brandStrong: '#913b27',
  success: '#3f654d', warning: '#85570f', danger: '#a33e34', info: '#425c86',
  bg: '#f7f6f2', surface: '#ffffff', subtle: '#f1eee8', brandSoft: '#f3e1d9'
};
function luminance(hex) {
  const rgb = [1,3,5].map(index => parseInt(hex.slice(index,index+2),16)/255).map(value => value <= .04045 ? value/12.92 : ((value+.055)/1.055)**2.4);
  return .2126*rgb[0] + .7152*rgb[1] + .0722*rgb[2];
}
function contrast(foreground, background) {
  const a=luminance(foreground), b=luminance(background);
  return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
}
const matrix = [
  ['ink','bg'],['ink','surface'],['muted','bg'],['muted','surface'],['muted','subtle'],['muted','brandSoft'],
  ['faint','bg'],['faint','surface'],['faint','subtle'],['faint','brandSoft'],['brandStrong','bg'],['brandStrong','surface'],
  ['success','bg'],['success','surface'],['success','subtle'],['warning','bg'],['warning','surface'],['warning','subtle'],
  ['info','bg'],['info','surface'],['info','subtle'],['danger','bg'],['danger','surface']
];
const results=matrix.map(([foreground,background])=>({foreground,background,ratio:Number(contrast(tokens[foreground],tokens[background]).toFixed(2))}));
const failures=results.filter(item=>item.ratio<4.5);
if(failures.length){console.error(JSON.stringify({failures},null,2));process.exit(1)}
console.log(JSON.stringify({standard:'WCAG AA normal text',pairs:results,pass:true},null,2));
