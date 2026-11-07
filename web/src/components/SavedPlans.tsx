import { useEffect, useRef, useState } from 'react'
import { api, type Plan } from '../lib/api'
import { ShoppingPanel } from './ShoppingPanel'
const slotLabel=(slot:unknown)=>({breakfast:'早餐',lunch:'午餐',dinner:'晚餐'}[String(slot)]??String(slot))

export function SavedPlans({userId,onCopy}:{userId:string;onCopy:(plan:Plan)=>void}) {
  const [plans,setPlans]=useState<Plan[]>([])
  const [selected,setSelected]=useState<Plan|null>(null)
  const detailsRef=useRef<HTMLElement>(null)
  useEffect(()=>{if(selected){detailsRef.current?.scrollIntoView({block:'nearest'});detailsRef.current?.focus()}},[selected])
  const [loading,setLoading]=useState(true)
  const [opening,setOpening]=useState(false)
  const [error,setError]=useState('')
  const [readError,setReadError]=useState('')
  const [attempt,setAttempt]=useState(0)
  useEffect(()=>{
    let active=true;setLoading(true);setError('')
    api.plans(userId).then(result=>{if(active)setPlans(result)}).catch(e=>{if(active)setError(e instanceof Error?e.message:'已保存的计划暂时不可用')}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[userId,attempt])
  async function open(plan:Plan) {
    if(opening)return
    setOpening(true);setReadError('');setSelected(null)
    try{setSelected(await api.plan(plan.plan_id))}catch(e){setReadError(e instanceof Error?e.message:'这份计划暂时无法打开')}finally{setOpening(false)}
  }
  return <section className="saved-plans" aria-label="已保存的计划">
    <h2 className="sr-only">计划列表与详情</h2>{!selected&&<p className="result-summary">不同日期分别保留，同一日期范围的新版本会替代旧版。最多展示 30 份。</p>}
    {loading&&<p className="busy-note" role="status">正在读取已保存的计划…</p>}
    {error&&<div className="error-state"><p className="error" role="alert">{error}</p><button onClick={()=>setAttempt(value=>value+1)}>重新读取计划</button></div>}
    {!loading&&!error&&!selected&&(plans.length?<div className="saved-plan-list">{plans.map(plan=><button disabled={opening} key={plan.plan_id} onClick={()=>open(plan)}><span><strong>{plan.start_date}{plan.days>1?` 起 · ${plan.days} 天`:''}</strong><span>{plan.items.map(item=>String(item.name)).join('、')}</span></span><span>{plan.status==='confirmed'?'当前版本':'旧版本'} ↗</span></button>)}</div>:<div className="empty-state"><h3>还没有保存的计划</h3><p>在“编辑安排”中填写一餐，预览并确认后就会出现在这里。</p></div>)}
    {opening&&<p className="busy-note" role="status">正在打开计划…</p>}{readError&&<p className="error" role="alert">{readError}</p>}
    {selected&&<section ref={detailsRef} tabIndex={-1} className="review-card" aria-label="已保存计划详情"><button className="button-secondary secondary" onClick={()=>setSelected(null)}>返回计划列表</button><p className="eyebrow">{selected.status==='confirmed'?'当前版本':'旧版本 · 仅供查看'}</p><h2>{selected.start_date} 的安排</h2>
      <ul className="plan-summary">{selected.items.map(item=><li key={String(item.item_id)}><span>{String(item.meal_date)} · {slotLabel(item.meal_slot)}<br/>{String(item.name)} · {item.servings ?? 1} 份</span><strong>{item.ingredient_id ? `主要食材 ${String(item.quantity)}${String(item.unit)}` : '未填写主要食材'}</strong></li>)}</ul>
      {selected.days===1&&<button className="button-primary primary-action" onClick={()=>onCopy(selected)}>以此为基础安排</button>}
      {selected.status==='confirmed'?<ShoppingPanel key={selected.plan_id} planId={selected.plan_id}/>:<p className="field-help">这份旧计划的采购清单已失效，请选择当前版本生成。</p>}
    </section>}
  </section>
}
