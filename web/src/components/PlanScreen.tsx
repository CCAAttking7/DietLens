import { useEffect, useRef, useState } from 'react'
import { api, type Plan } from '../lib/api'
import { useSessionDraft } from '../lib/useSessionDraft'
import { SavedPlans } from './SavedPlans'
import { ShoppingPanel } from './ShoppingPanel'

const slots = [{ key: 'breakfast', label: '早餐' }, { key: 'lunch', label: '午餐' }, { key: 'dinner', label: '晚餐' }]
const localDate = () => {
  const date = new Date()
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

export function PlanScreen({ userId }: { userId: string }) {
  const [startDate, setStartDate] = useSessionDraft(`${userId}:plan-date`, localDate())
  const [meals, setMeals] = useSessionDraft(`${userId}:plan-meals`, slots.map(slot => ({ ...slot, name: '', ingredient: '', quantity: '', unit: '份' })))
  const [draft, setDraft] = useSessionDraft<Plan | null>(`${userId}:plan-preview`, null)
  const [view, setView] = useState<'editor'|'saved'>('editor')
  const [copyCandidate, setCopyCandidate] = useState<Plan|null>(null)
  const copyPromptRef = useRef<HTMLElement>(null)
  useEffect(() => { if (copyCandidate) { copyPromptRef.current?.scrollIntoView({block:'nearest'}); copyPromptRef.current?.focus() } }, [copyCandidate])
  const [expanded, setExpanded] = useState(() => meals.filter(meal => meal.name || meal.key === 'lunch').map(meal => meal.key))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [checkingDraft, setCheckingDraft] = useState(Boolean(draft))
  const [draftError, setDraftError] = useState('')
  const [draftAttempt, setDraftAttempt] = useState(0)
  useEffect(() => {
    if (!draft) return
    let active = true
    setCheckingDraft(true); setDraftError('')
    api.plan(draft.plan_id).then(plan => { if (active) setDraft(plan) })
      .catch(e => { if (active) setDraftError(e instanceof Error ? e.message : '无法恢复计划，请重试') })
      .finally(() => { if (active) setCheckingDraft(false) })
    return () => { active = false }
    // Revalidate the cached draft on entry; commands return subsequent fresh state.
  }, [userId, draftAttempt])

  function invalidate() {
    if (draft) setNotice(draft.status === 'confirmed' ? '原计划已保存。修改后需重新确认；同一日期的新版本会替代旧版，其他日期不受影响。' : '内容已修改，请重新预览后确认。')
    setDraft(null); setError('')
  }
  function update(index: number, field: string, value: string) {
    invalidate()
    setMeals(current => current.map((meal, i) => i === index ? { ...meal, [field]: value } : meal))
  }
  async function run(action: () => Promise<void>) {
    if (busy || checkingDraft || draftError) return
    setBusy(true); setError('')
    try { await action() } catch (e) { setError(e instanceof Error ? e.message : '计划暂时无法保存') } finally { setBusy(false) }
  }
  const preview = () => run(async () => {
    const selected = meals.filter(meal => meal.name.trim())
    if (!startDate) throw new Error('请先选择计划日期')
    if (!selected.length) throw new Error('先填写一餐即可，其他餐次可以留空')
    if (selected.some(meal => meal.ingredient.trim() && (!meal.quantity.trim() || !Number.isFinite(Number(meal.quantity)) || Number(meal.quantity) <= 0))) throw new Error('填写主要食材后，请提供大于 0 的食材数量')
    const items = selected.map(meal => ({ item_id: `web-${startDate}-${meal.key}`, meal_date: startDate, meal_slot: meal.key, name: meal.name.trim(), ingredient_id: meal.ingredient.trim(), ingredient_name: meal.ingredient.trim(), quantity: meal.ingredient.trim() ? Number(meal.quantity) : null, unit: meal.unit, servings: 1 }))
    const next = await api.planPreview({ user_id: userId, start_date: startDate, days: 1, servings: 1, items })
    setDraft(next); setNotice('')
  })
  const confirm = () => run(async () => { if (draft) { setDraft(await api.planConfirm(draft.plan_id)); setNotice('计划已保存。你可以继续生成采购清单。') } })
  const cancel = () => run(async () => { if (draft) { await api.planCancel(draft.plan_id); setDraft(null); setNotice('预览已取消，填写的内容仍然保留。') } })
  function copy(plan: Plan) {
    setStartDate(plan.start_date)
    const next = slots.map(slot => {
      const item = plan.items.find(item => item.meal_slot === slot.key || item.meal_slot === slot.label)
      return {...slot, name:item?String(item.name):'', ingredient:item?String(item.ingredient_name || item.ingredient_id):'', quantity:item?String(item.quantity):'', unit:item?String(item.unit):'份'}
    })
    setMeals(next); setExpanded(next.filter(meal=>meal.name||meal.key==='lunch').map(meal=>meal.key)); setDraft(null); setCopyCandidate(null); setView('editor'); setError(''); setNotice('已带入这份安排。修改后请重新预览；确认相同日期的计划会替代旧版本。')
  }

  return <div className="workspace plan-workspace"><section className="workspace-main">
    <p className="eyebrow">从现在往后 · 留一点余地</p>{view==='saved'?<h1>已保存的计划</h1>:<h1>把下一步安排好，<br/><em>也可以随时改变。</em></h1>}
    <p className="lede">{view==='saved'?'查看已确认的安排，或以它为起点准备下一餐。':'先安排一餐就好。其他餐次可以留空，计划也不会自动变成实际饮食记录。'}</p>
    <div className="review-view-switch" role="group" aria-label="计划内容"><button aria-pressed={view==='editor'} disabled={busy || checkingDraft} onClick={()=>setView('editor')}>编辑安排</button><button aria-pressed={view==='saved'} disabled={busy || checkingDraft} onClick={()=>setView('saved')}>已保存的计划</button></div>
    {copyCandidate&&<section ref={copyPromptRef} tabIndex={-1} className="review-card"><h2>用这份安排替换当前草稿？</h2><p>当前填写内容将被带入的计划替换。已保存的计划保持不变。</p><div className="button-row"><button onClick={()=>copy(copyCandidate)}>使用这份计划</button><button className="button-secondary secondary" onClick={()=>setCopyCandidate(null)}>保留当前草稿</button></div></section>}
    {view==='saved'?<SavedPlans userId={userId} onCopy={plan=>{if(meals.some(meal=>meal.name.trim()))setCopyCandidate(plan);else copy(plan)}}/>:<>
    <div className="plan-form">
      <label htmlFor="plan-date">计划日期</label><input id="plan-date" type="date" disabled={busy || checkingDraft || Boolean(draftError)} value={startDate} onChange={e => { invalidate(); setStartDate(e.target.value) }} />
      <div className="meal-sections">{meals.map((meal, i) => <section className="meal-section" key={meal.key}>
        <button className="meal-toggle" type="button" aria-expanded={expanded.includes(meal.key)} aria-controls={`plan-${meal.key}`} disabled={busy || checkingDraft || Boolean(draftError)} onClick={() => setExpanded(current => current.includes(meal.key) ? current.filter(key => key !== meal.key) : [...current, meal.key])}>
          <span>{meal.label}</span><span>{meal.name.trim() || (expanded.includes(meal.key) ? '填写这一餐' : '按需添加')}<span aria-hidden="true">{expanded.includes(meal.key) ? ' −' : ' ＋'}</span></span>
        </button>
        <fieldset className="meal-row" id={`plan-${meal.key}`} hidden={!expanded.includes(meal.key)} disabled={busy || checkingDraft || Boolean(draftError)}><legend className="sr-only">{meal.label}</legend>
          <label className="meal-name">餐食<input aria-label={`${meal.label}名称`} value={meal.name} onChange={e => update(i, 'name', e.target.value)} placeholder="例如：番茄鸡蛋面" /></label>
          <label className="meal-ingredient">主要食材<input aria-label={`${meal.label}食材`} value={meal.ingredient} onChange={e => update(i, 'ingredient', e.target.value)} placeholder="可选；留空不会生成食材清单" /></label>
          <label>主要食材数量<input aria-label={`${meal.label}主要食材数量`} inputMode="decimal" value={meal.quantity} onChange={e => update(i, 'quantity', e.target.value)} placeholder={meal.ingredient.trim() ? '例如：500' : '有主要食材时填写'} /></label>
          <label>单位<select aria-label={`${meal.label}单位`} value={meal.unit} onChange={e => update(i, 'unit', e.target.value)}>{['份', '个', 'g', 'kg', 'ml', 'l', '件', '包', '瓶'].map(unit => <option key={unit}>{unit}</option>)}</select></label>
        </fieldset>
      </section>)}</div>
      <button className="button-primary" onClick={preview} disabled={busy || checkingDraft || Boolean(draftError)}>{busy ? '正在处理…' : '预览这一天'}</button>
    </div><p className="field-help">这是单日计划。餐食本身可以没有主要食材；采购核对只覆盖你明确填写的主要食材，且不会自动换算单位。</p>
    {notice && <p className="notice" role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {checkingDraft && <p className="busy-note" role="status">正在恢复计划…</p>}{draftError && <div className="error-state"><p className="error" role="alert">{draftError}</p><button onClick={()=>setDraftAttempt(value=>value+1)}>重新读取当前计划</button><button onClick={()=>{setDraft(null);setDraftError('');setNotice('已清除失效预览，填写内容保留，请重新预览。')}}>保留填写，重新预览</button></div>}
    {draft && !checkingDraft && !draftError && <section className="review-card" aria-label="计划预览">
      <p className="eyebrow">{draft.status === 'confirmed' ? '已保存' : '核对后再保存'}</p>
      <h2>{draft.status === 'confirmed' ? '这一天，已经安排好' : draft.status === 'draft' ? '这份计划还没有保存' : '这份计划已有更新'}</h2>
      <p>{draft.start_date} · {draft.items.length} 个餐次</p>
      <ul className="plan-summary">{draft.items.map(item => <li key={String(item.item_id)}><span>{slots.find(slot => slot.key === item.meal_slot)?.label ?? String(item.meal_slot)} · {String(item.name)} · {item.servings ?? 1} 份</span><strong>{item.ingredient_id ? `主要食材 ${String(item.quantity)}${String(item.unit)}` : '未填写主要食材'}</strong></li>)}</ul>
      {draft.status === 'draft' && <p>确认后会替代相同日期范围的旧计划；其他日期的安排会保留。</p>}
      {draft.status === 'draft' ? <div className="button-row"><button className="button-primary" disabled={busy || checkingDraft || Boolean(draftError)} onClick={confirm}>确认计划</button><button className="button-secondary secondary" disabled={busy || checkingDraft || Boolean(draftError)} onClick={cancel}>取消预览</button></div> : draft.status === 'confirmed' && draft.start_date === startDate ? <ShoppingPanel key={`${draft.plan_id}:${startDate}`} planId={draft.plan_id}/> : draft.status === 'confirmed' ? <p>日期已经改变。请重新预览后确认新的安排，采购清单不会沿用旧日期。</p> : <p>这份计划已被替代或取消。请在“已保存的计划”中选择当前版本。</p>}
    </section>}
    </>}
  </section><aside className="status-card"><p className="eyebrow">这一天的安排</p><h2>给未来留一点余地</h2><div className="state-track"><span className={draft ? 'on' : ''}>预览</span><span className={draft?.status === 'confirmed' ? 'on' : ''}>确认</span><span>采购</span></div><p>修改后需要重新预览和确认。旧版本可在“已保存的计划”中查看，实际吃了什么由你另行记录。</p></aside></div>
}
