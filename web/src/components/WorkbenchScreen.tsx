import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useSessionDraft, writeSessionDraft } from '../lib/useSessionDraft'
import { MealJournal } from './MealJournal'

function Metric({title,value,caption}:{title:string;value:string|number;caption:string}) {
  return <div className="metric"><span>{title}</span><strong>{value}</strong><p>{caption}</p></div>
}
function Lens({tone,title,value,caption,detail}:{tone:string;title:string;value:string;caption:string;detail:string}) {
  return <article className={`lens-card lens-${tone}`}><div className="lens-top"><span className="lens-dot" aria-hidden="true"/><span>{title}</span></div><strong>{value}</strong><p>{caption}</p><small>{detail}</small></article>
}
const ratio=(value:any)=>value?.value==null?'暂无反馈':`${Math.round(value.value*100)}%`
function narrative(data:any) {
  const planned = Number(data.plan?.planned_meals ?? 0)
  const recorded = Number(data.actual?.recorded_meals ?? 0)
  const adopted = Number(data.actions?.adopted ?? 0)
  const coverage = data.actions?.feedback_coverage?.value
  if (!planned && !recorded && !adopted) return '这段时间还没有足够的记录来形成判断。从下一餐开始就好，空白不会被算成失败。'
  const parts:string[] = []
  if (planned) parts.push(`你安排过 ${planned} 餐`)
  if (recorded) parts.push(`主动记下了 ${recorded} 餐`)
  if (adopted) parts.push(`选择过 ${adopted} 个小行动`)
  const lead = `${parts.join('，')}。`
  if (coverage == null) return `${lead}目前还没有足够的反馈，先把发生过的事情留在这里。`
  if (coverage < 1) return `${lead}有些行动还没有回来反馈，这些部分先保持未知；下一步可以从最容易完成的一餐开始。`
  return `${lead}你已经把选择和结果都留了下来，可以从重复出现的情境里挑一个最值得调整的地方。`
}

export function WorkbenchScreen({userId,onEditConsent,onStartAction,initialRecording=false}:{userId:string;onEditConsent:()=>void;onStartAction?:()=>void;initialRecording?:boolean}) {
  const [period,setPeriod]=useSessionDraft(`${userId}:review-period`,'week')
  const [view,setView]=useSessionDraft<'overview'|'journal'>(`${userId}:review-view`,initialRecording?'journal':'overview')
  const [data,setData]=useState<Record<string,any>|null>(null)
  const [error,setError]=useState('')
  const [consentRequired,setConsentRequired]=useState(false)
  const [loading,setLoading]=useState(true)
  const [attempt,setAttempt]=useState(0)
  const [copied,setCopied]=useState(false)
  useEffect(()=>{if(initialRecording)setView('journal')},[initialRecording])
  useEffect(()=>{
    let active=true;setLoading(true);setError('');setData(null);setConsentRequired(false)
    api.workbenchReview(userId,period).then(result=>{if(active)setData(result)}).catch(e=>{
      if(!active)return
      if(e instanceof Error&&e.message==='review_consent_required')setConsentRequired(true)
      else setError(e instanceof Error?e.message:'回顾暂时不可用')
    }).finally(()=>{if(active)setLoading(false)})
    return ()=>{active=false}
  },[userId,period,attempt])
  const empty=data&&(data.plan?.planned_meals??0)===0&&(data.actual?.recorded_meals??0)===0&&(data.actions?.adopted??0)===0
  function recordPlanned(item:any, timeline:any) {
    const slot = ({早餐:'breakfast',午餐:'lunch',晚餐:'dinner'} as Record<string,string>)[String(timeline.slot)] ?? String(timeline.slot)
    writeSessionDraft(`${userId}:actual-meal-draft`, {fields:{meal_date:String(timeline.date),meal_slot:slot,name:String(item.name??''),quantity:item.quantity==null?'':String(item.quantity),unit:String(item.unit??'份'),plan_id:String(item.plan_id??''),plan_item_id:String(item.item_id??'')},editing:null,preview:null,open:true})
    setView('journal')
  }
  async function copyReview() {
    if (!data) return
    const text = [`DietLens · ${data.period?.start ?? ''} — ${data.period?.end ?? ''}`, narrative(data), ...(data.next_steps ?? []).map((item:string)=>`下一步：${item}`)].join('\n')
    let success = false
    try { await navigator.clipboard.writeText(text); success = true } catch {
      try {
        const fallback = document.createElement('textarea')
        fallback.value = text; fallback.setAttribute('readonly',''); fallback.style.position = 'fixed'; fallback.style.opacity = '0'
        document.body.appendChild(fallback); fallback.select(); success = document.execCommand('copy'); fallback.remove()
      } catch { success = false }
    }
    if (success) { setCopied(true); window.setTimeout(() => setCopied(false), 2500) } else setCopied(false)
  }
  return <div className="workspace review-workspace"><section className="workspace-main">
    <p className="eyebrow">过一段时间 · 回来看一眼</p><h1>把走过的这段，<br/><em>放在一起看。</em></h1>
    <div className="review-view-switch" role="group" aria-label="回顾内容"><button aria-pressed={view==='overview'} onClick={()=>setView('overview')}>这段时间</button><button aria-pressed={view==='journal'} onClick={()=>setView('journal')}>用餐记录</button></div>
    {view==='journal'?<MealJournal userId={userId} initiallyOpen={initialRecording} onChanged={()=>setAttempt(value=>value+1)}/>:<>
      <div className="period-tabs" role="group" aria-label="回顾时间范围">{['day','week','month'].map(item=><button key={item} aria-pressed={period===item} className={period===item?'nav-active':''} onClick={()=>setPeriod(item)}>{item==='day'?'今天':item==='week'?'本周':'本月'}</button>)}</div>
      {loading&&<p className="busy-note" role="status">正在读取这段时间的记录…</p>}
      {consentRequired&&<div className="empty-state"><h2>回顾由你决定是否开启</h2><p>开启后，才会汇总历史计划、用餐记录和行动反馈。你仍然可以单独记录一餐，之后随时撤回授权。</p><button onClick={onEditConsent}>查看并开启历史回顾</button><button onClick={()=>setView('journal')}>先记下一餐</button></div>}
      {error&&<div className="error-state"><p className="error" role="alert">{error}</p><button onClick={()=>setAttempt(value=>value+1)}>重新读取回顾</button></div>}
      {data&&<>
        {data.period&&<p className="result-summary">{data.period.start} — {data.period.end}</p>}
        {empty&&<div className="empty-state"><h2>这一段，还没有留下记录</h2><p>从现在的一餐开始就好。没有记录的日子不会算作失败。</p><button onClick={()=>setView('journal')}>记录已吃的一餐</button></div>}
        <section className="planning-compass" aria-label="饮食目标罗盘"><div className="compass-heading"><div><p className="eyebrow">你的饮食罗盘</p><h2>把今天，放回更大的方向里。</h2></div><span className="compass-period">{period==='day'?'今天':period==='week'?'本周':'本月'}</span></div><p className="compass-lede">先看清现在，再决定下一步。这里不评判你，只把已经发生的事情整理出来。</p><div className="lens-grid">
          <Lens tone="liquidity" title="手边的余地" value={data.plan?.planned_meals ? `${data.plan.planned_meals} 餐已安排` : '还没安排'} caption="计划与可获得的选择" detail="预算、时间和现有食材，决定今天能有多轻松。"/>
          <Lens tone="lifestyle" title="日常的节奏" value={data.actual?.recorded_meals ? `${data.actual.recorded_meals} 餐已记录` : '留一点空白'} caption="你愿意留下的真实记录" detail="记录是为了看见生活，不是为了给自己打分。"/>
          <Lens tone="legacy" title="一起吃的关系" value={data.actions?.adopted ? `${data.actions.adopted} 个小行动` : '从一件小事开始'} caption="对未来习惯的温和投入" detail="每次可执行的选择，都会为之后的自己留下线索。"/>
          <Lens tone="growth" title="正在变好的方向" value={ratio(data.actions?.completion_among_feedback)} caption="已反馈行动中的完成度" detail="不确定和未反馈会保留为未知，不被误算成失败。"/>
        </div></section><section className="review-narrative" aria-label="这段时间发生了什么"><div className="narrative-heading"><p className="eyebrow">把数字说成人话</p><button className={`copy-review ${copied?'is-copied':''}`} onClick={()=>void copyReview()} aria-label="复制这段回顾">{copied?'✓ 已复制':'复制回顾'}</button></div><p>{narrative(data)}</p></section>
        {data.insights?.length>0&&<section className="review-insights" aria-label="从记录里看到的线索"><div className="insights-heading"><div><p className="eyebrow">Agent 看到的线索</p><h2>把发生过的事，变成下一步的依据。</h2></div><span>基于本段记录</span></div><div className="insight-grid">{data.insights.map((item:any)=>{const retry=item.kind==='barrier'||item.kind==='preference';return <article className={`insight-card insight-${item.tone}`} key={item.kind}><p className="eyebrow">{item.evidence}</p><h3>{item.title}</h3><p>{item.body}</p><button className="insight-action" onClick={()=>retry?onStartAction?.():setView('journal')}>{retry?'开始一次新的尝试':'去记录一餐'}<span aria-hidden="true">↗</span></button></article>})}</div></section>}
        {data.timeline?.length>0&&<section className="review-timeline" aria-label="计划与实际时间线"><div className="timeline-heading"><div><p className="eyebrow">这一段是怎么走过来的</p><h2>计划和真实生活，放在同一条线上。</h2></div><button className="timeline-record" onClick={()=>setView('journal')}>补记一餐</button></div><div className="timeline-list">{data.timeline.map((item:any)=><article className={`timeline-item timeline-${item.status}`} key={`${item.date}-${item.slot}`}><div className="timeline-marker" aria-hidden="true"/><div className="timeline-date"><strong>{item.date.slice(5).replace('-', ' / ')}</strong><span>{item.slot}</span></div><div className="timeline-content">{item.planned.length>0&&<div><span className="timeline-label">计划</span><span>{item.planned.map((entry:any)=>entry.name).join('、')}</span></div>}{item.recorded.length>0&&<div><span className="timeline-label timeline-label-recorded">实际</span><span>{item.recorded.map((entry:any)=>`${entry.name}${entry.quantity==null?' · 份量未知':` · ${entry.quantity}${entry.unit||''}`}`).join('、')}</span></div>}{item.status==='unplanned'&&<small>这餐没有对应计划，是生活留下的线索。</small>}{item.status==='same_slot'&&<small>日期和餐次相同，但还没有明确关联计划。</small>}{item.status==='planned'&&<><small>已安排，还没有对应的实际记录。</small><button className="timeline-inline-action" onClick={()=>recordPlanned(item.planned[0],item)}>按计划记录这一餐 <span aria-hidden="true">↗</span></button></>}</div><span className="timeline-status">{item.status==='matched'?'已明确关联':item.status==='same_slot'?'同餐次，待核对':item.status==='unplanned'?'计划外':'待记录'}</span></article>)}</div></section>}
        <div className="review-grid">
          <Metric title="计划餐次" value={data.plan?.planned_meals??0} caption="你确认过的安排"/>
          <Metric title="实际记录" value={data.actual?.recorded_meals??0} caption="你主动记下的用餐"/>
          <Metric title="已反馈的行动" value={ratio(data.actions?.feedback_coverage)} caption={data.actions?.feedback_coverage?.denominator?`${data.actions.feedback_coverage.numerator} / ${data.actions.feedback_coverage.denominator} 个已选择的行动`:'有行动和反馈后再计算'}/>
          <Metric title="反馈中已完成" value={ratio(data.actions?.completion_among_feedback)} caption={data.actions?.completion_among_feedback?.denominator?`${data.actions.completion_among_feedback.numerator} / ${data.actions.completion_among_feedback.denominator} 次明确反馈`:'未知和未反馈不按失败计算'}/>
          <div className="review-panel"><h2>暂时不知道的部分</h2>{data.unknowns?.length?data.unknowns.map((item:any)=><p key={item.kind}>{item.message}</p>):<p>目前没有额外未知项。</p>}</div>
          <div className="review-panel next-route"><p className="eyebrow">下一条可走的路</p><h2>接下来，可以轻一点</h2>{data.next_steps?.map((item:string)=><p key={item}>{item}</p>)}<button className="button-primary primary-action" onClick={()=>setView('journal')}>查看或补充用餐记录</button></div>
        </div>
      </>}
    </>}
  </section><aside className="status-card"><p className="eyebrow">你的这段时间</p><h2>留白也可以</h2><p>计划、实际用餐和行动反馈分别保留。不确定的份量保持未知，没有记录也不会被当成没有吃饭。</p></aside></div>
}
