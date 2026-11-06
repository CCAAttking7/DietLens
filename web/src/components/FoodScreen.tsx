import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useSessionDraft } from '../lib/useSessionDraft'

type FoodRecord={name:string;source:string;source_id?:string|null;source_url?:string|null;retrieved_at?:string;nutrients?:Record<string,number|null>;ingredients_known?:boolean;allergens_known?:boolean;ingredients?:string[];allergens?:string[]}
type Assessment={record:FoodRecord;status:string;reasons?:string[];unknown_fields?:string[]}
type Result={assessments?:Assessment[];failures?:Record<string,string>;conflicts?:unknown[]}
const sources:Record<string,string>={open_food_facts:'Open Food Facts · 包装食品资料',china_cdc_food_composition:'中国疾控中心 · 食物编码资料',usda_fooddata_central:'USDA · 食品资料'}
const reasonLabels:Record<string,string>={explicit_hard_constraint_match:'与已确认的过敏或忌口条件冲突',key_ingredient_or_allergen_unknown:'缺少关键配料或过敏原资料',hard_constraints_unknown:'需要先确认你的饮食边界',price_over_budget:'已知价格超过参考预算'}
const fieldLabels:Record<string,string>={ingredients:'配料',allergens:'过敏原',allergies:'过敏信息',price:'价格',nutrients:'营养资料'}
function safeLink(value?:string|null) {
  try{const url=new URL(value??'');return ['https:','http:'].includes(url.protocol)?url.href:null}catch{return null}
}
function Nutrients({record}:{record:FoodRecord}) {
  const values=record.nutrients??{}
  const known=(suffix:string)=>Object.entries(values).some(([key,value])=>key.endsWith(suffix)&&typeof value==='number'&&Number.isFinite(value))
  const basis=!known('_100g')&&known('_100ml')?'100ml':'100g'
  const metrics=[{name:'热量',unit:'kcal',keys:[`energy-kcal_${basis}`,`energy_kcal_${basis}`]},{name:'蛋白质',unit:'g',keys:[`proteins_${basis}`,`protein_g_${basis}`]},{name:'脂肪',unit:'g',keys:[`fat_${basis}`,`fat_g_${basis}`]},{name:'碳水',unit:'g',keys:[`carbohydrates_${basis}`,`carbohydrates_g_${basis}`]}]
  if(!known('_100g')&&!known('_100ml'))return <p className="field-help">这个来源暂未提供可按相同基准核对的营养数据。</p>
  return <><p className="nutrient-basis">每 {basis==='100ml'?'100 毫升':'100 克'} · 按来源标注</p><dl className="food-nutrients">{metrics.map(metric=>{const key=metric.keys.find(key=>typeof values[key]==='number'&&Number.isFinite(values[key]));return <div key={metric.name}><dt>{metric.name}</dt><dd>{key?`${values[key]} ${metric.unit}`:'未知'}</dd></div>})}</dl></>
}
function FoodCard({item,onEditProfile}:{item:Assessment;onEditProfile:()=>void}) {
  const {record}=item,link=safeLink(record.source_url)
  const timestamp=record.retrieved_at?new Date(record.retrieved_at):null
  return <article className="food-card"><div className="food-card-head"><h2>{record.name}</h2><span className={`food-status food-${item.status}`}>{item.status==='safe'?'未发现约束冲突':item.status==='blocked'?'与条件冲突':'需要核对'}</span></div>
    <p className="food-source-label">{sources[record.source]??record.source}</p>
    {item.reasons?.length? <p className="food-interpretation">{item.status==='blocked'?'这项选择触及已确认的边界。':item.unknown_fields?.length?'资料还不完整，先不要把它当成安全结论。':'目前没有发现已知边界冲突。'}</p>:null}
    {!!item.unknown_fields?.length&&<p>待核对：{item.unknown_fields.map(field=>fieldLabels[field]??field).join('、')}</p>}
    {item.reasons?.includes('hard_constraints_unknown')&&<button className="primary-action secondary" onClick={onEditProfile}>核对饮食边界</button>}
    <details className="food-data-summary"><summary>查看营养与核对字段</summary><Nutrients record={record}/>
    <div className="food-field-status"><span>配料：{record.ingredients_known?'来源有提供':'待核对'}</span><span>过敏原：{record.allergens_known?'来源有提供':'待核对'}</span></div></details>
    <details className="food-provenance"><summary>查看来源与配料详情</summary>
      <p>来源编号：{record.source_id||'未提供'}</p>
      {timestamp&&!Number.isNaN(timestamp.getTime())&&<p>资料读取时间：<time dateTime={record.retrieved_at}>{timestamp.toLocaleString('zh-CN')}</time></p>}
      <p>配料：{record.ingredients?.length?record.ingredients.join('、'):record.ingredients_known?'来源未列出具体配料，请核对包装':'来源未提供'}</p>
      <p>过敏原：{record.allergens?.length?record.allergens.join('、'):record.allergens_known?'来源未列出过敏原，请核对包装':'来源未提供'}</p>
      {link&&<a href={link} target="_blank" rel="noreferrer">打开原始来源 ↗</a>}
    </details>
  </article>
}

export function FoodScreen({userId,profileVersion,onEditProfile}:{userId:string;profileVersion:number;onEditProfile:()=>void}) {
  const [query,setQuery]=useSessionDraft(`${userId}:food-query`,'')
  const [result,setResult]=useSessionDraft<{term:string;data:Result}|null>(`${userId}:food-result:${profileVersion}`,null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [searched,setSearched]=useState('')
  const generation=useRef(0)
  const composing=useRef(false)
  useEffect(()=>()=>{generation.current+=1},[])
  async function search(value=query) {
    const term=value.trim()
    if(busy||!term)return
    setResult(null);setError('')
    if(term.length>120){setError('请输入 1 至 120 个字符的食物名称或品牌。');return}
    const current=++generation.current;setBusy(true);setSearched(term)
    try{const data=await api.foodSearch(userId,term);if(current===generation.current)setResult({term,data})}
    catch(e){if(current===generation.current)setError(e instanceof Error?e.message:'资料查询暂时不可用')}
    finally{if(current===generation.current)setBusy(false)}
  }
  const data=result?.data,hasFailures=Boolean(data?.failures&&Object.keys(data.failures).length)
  return <div className="workspace food-workspace"><section className="workspace-main">
    <p className="eyebrow">遇到不确定 · 先查一点</p><h1>需要时查一点，<br/><em>决定留给你。</em></h1>
    <p className="lede">输入食品名称或品牌，按来源查看资料。配料、过敏原和营养缺失时会明确标出，仍需以实际包装为准。</p>
    <form className="search-form" onSubmit={e=>{e.preventDefault();if(!composing.current)void search()}}><input aria-label="搜索食品" maxLength={120} value={query} onCompositionStart={()=>{composing.current=true}} onCompositionEnd={()=>{composing.current=false}} onChange={e=>setQuery(e.target.value)} placeholder="例如：燕麦，或具体品牌"/><button type="submit" disabled={busy||!query.trim()}>{busy?'正在查询…':'查资料'}</button></form>
    {busy&&<p className="busy-note" role="status"><span className="spinner"/>正在查找“{searched}”的资料，外部来源可能需要几秒。</p>}
    {!result&&!busy&&!error&&<div className="empty-state"><h2>先从一个具体的食物开始</h2><p>具体品牌通常更容易找到包装食品。食物编码资料可能只提供名称，不包含完整营养和配料。</p><div className="button-row">{['燕麦','鸡蛋','牛奶'].map(term=><button key={term} onClick={()=>{setQuery(term);void search(term)}}>{term}</button>)}</div></div>}
    {error&&<div className="error-state"><p className="error" role="alert">{error}</p><button onClick={()=>void search()} disabled={busy}>重新查询</button></div>}
    {data&&<div className="food-results"><p className="result-summary">“{result.term}” · {data.assessments?.length??0} 条资料。重新查询可核对最新结果。</p>
      {hasFailures&&<div className="notice" role="status"><strong>部分资料源暂时不可用</strong><span>已显示当前拿到的资料；完整性仍需按包装核对。</span></div>}
      {!!data.conflicts?.length&&<div className="notice">同名资料存在规格差异，请按来源逐条核对，不会自动合并。</div>}
      {data.assessments?.length?data.assessments.map((item,index)=><FoodCard key={`${item.record.source}-${item.record.source_id}-${index}`} item={item} onEditProfile={onEditProfile}/>):hasFailures?<div className="empty-state"><h2>这次还没拿到可用资料</h2><p>有来源未能连接，查询结果不完整。可以重试，也可以补充品牌；暂时无法判断是否有匹配资料。</p><button onClick={()=>void search()}>重试查询来源</button></div>:<div className="notice">暂时没有找到匹配资料。可以补充品牌或换个名称；没有结果不代表食物不安全。</div>}
    </div>}
  </section><aside className="status-card"><p className="eyebrow">看得见的依据</p><h2>每一条，保留出处</h2><p>不同来源分开展示。没有过敏原标注不代表没有过敏原，未知营养也不会按零计算。</p></aside></div>
}
