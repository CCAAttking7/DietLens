import { useEffect, useRef, useState } from 'react'
import { api, type MealRecord, type Plan } from '../lib/api'
import { useSessionDraft } from '../lib/useSessionDraft'

const slots = [{value:'breakfast',label:'早餐'}, {value:'lunch',label:'午餐'}, {value:'dinner',label:'晚餐'}]
const label = (slot:string) => slots.find(item => item.value === slot)?.label ?? slot
const localDate = () => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}` }
const suggestedSlot = () => { const hour = new Date().getHours(); return hour < 10 ? 'breakfast' : hour < 15 ? 'lunch' : 'dinner' }
const emptyFields = () => ({meal_date:localDate(),meal_slot:suggestedSlot(),name:'',quantity:'',unit:'份'})

export function MealJournal({userId, onChanged, initiallyOpen=false}:{userId:string;onChanged:()=>void;initiallyOpen?:boolean}) {
  const [draft,setDraft] = useSessionDraft<{fields:ReturnType<typeof emptyFields>&{plan_id?:string;plan_item_id?:string};editing:MealRecord|null;preview:MealRecord|null;quickTaskId?:string;open:boolean}>(`${userId}:actual-meal-draft`,{fields:emptyFields(),editing:null,preview:null,open:initiallyOpen})
  const [records,setRecords] = useState<MealRecord[]>([])
  const [plans,setPlans] = useState<Plan[]>([])
  const [loading,setLoading] = useState(true)
  const [loadError,setLoadError] = useState('')
  const [attempt,setAttempt] = useState(0)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [notice,setNotice] = useState('')
  const [deleting,setDeleting] = useState<MealRecord|null>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const formRef = useRef<HTMLFormElement>(null)
  useEffect(() => {
    let active=true; setLoading(true);setLoadError('')
    api.mealRecords(userId).then(items=>{if(active)setRecords(items)}).catch(e=>{if(active)setLoadError(e instanceof Error?e.message:'暂时无法读取记录')}).finally(()=>{if(active)setLoading(false)})
    api.plans(userId).then(items=>{if(active)setPlans(items.filter(item=>item.status==='confirmed'))}).catch(()=>{if(active)setPlans([])})
    return ()=>{active=false}
  },[userId,attempt])
  useEffect(()=>{if(initiallyOpen)setDraft(current=>({...current,open:true}))},[initiallyOpen])
  function change(key:keyof ReturnType<typeof emptyFields>, value:string) {
    setDraft(current=>({...current,fields:{...current.fields,[key]:value,...(key==='meal_date'||key==='meal_slot'?{plan_id:undefined,plan_item_id:undefined}:{})},preview:null}));setError('');setNotice('')
  }
  function open(record?:MealRecord, repeat=false) {
    setDraft({fields:record?{meal_date:repeat?localDate():record.meal_date,meal_slot:slots.find(slot => slot.label===record.meal_slot)?.value??record.meal_slot,name:record.name,quantity:record.quantity==null?'':String(record.quantity),unit:record.unit??'份',...(repeat?{}:{plan_id:record.plan_id??undefined,plan_item_id:record.plan_item_id??undefined})}:emptyFields(),editing:repeat?null:(record??null),preview:null,quickTaskId:undefined,open:true})
    setError('');setNotice('');setDeleting(null)
    requestAnimationFrame(()=>{formRef.current?.scrollIntoView({block:'nearest'});nameRef.current?.focus()})
  }
  async function run(action:()=>Promise<void>) {
    if(busy)return
    setBusy(true);setError('');setNotice('')
    try{await action()}catch(e){setError(e instanceof Error?e.message:'操作未完成，请重试')}finally{setBusy(false)}
  }
  function changes() {
    const {fields}=draft
    if(!fields.meal_date)throw new Error('请选择用餐日期')
    if(!fields.name.trim())throw new Error('请填写实际吃的餐食')
    const quantity=fields.quantity.trim()?Number(fields.quantity):null
    if(quantity!==null&&(!Number.isFinite(quantity)||quantity<0))throw new Error('份量需要是非负数字，不确定时可以留空')
    return {meal_date:fields.meal_date,meal_slot:fields.meal_slot,name:fields.name.trim(),quantity,unit:quantity===null?null:fields.unit,plan_id:fields.plan_id||null,plan_item_id:fields.plan_item_id||null}
  }
  const matchingPlanItems=plans.flatMap(plan=>plan.items.filter(item=>item.meal_date===draft.fields.meal_date&&(item.meal_slot===draft.fields.meal_slot||item.meal_slot===label(draft.fields.meal_slot))).map(item=>({plan,item})))
  const preview=()=>run(async()=>{
    if (draft.editing) {
      const result=await api.mealPreview({user_id:userId,...changes()})
      setDraft(current=>({...current,preview:result}))
    } else {
      const result=await api.quickLogPreview({user_id:userId,...changes()})
      setDraft(current=>({...current,preview:result.record,quickTaskId:result.task.task_id}))
    }
  })
  const confirm=()=>run(async()=>{
    if(!draft.preview)return
    const saved=draft.editing?await api.mealUpdate(draft.editing,changes()):(draft.quickTaskId?(await api.quickLogConfirm(draft.quickTaskId,draft.preview)).record:await api.mealConfirm(draft.preview))
    setRecords(current=>[saved,...current.filter(item=>item.record_id!==saved.record_id)].sort((a,b)=>b.meal_date.localeCompare(a.meal_date)).slice(0,20))
    setDraft({fields:emptyFields(),editing:null,preview:null,open:false});setNotice('这一餐已保存，回顾已更新。');onChanged()
  })
  const remove=()=>run(async()=>{
    if(!deleting)return
    await api.mealDelete(deleting)
    setRecords(current=>current.filter(record=>record.record_id!==deleting.record_id))
    if(draft.editing?.record_id===deleting.record_id)setDraft({fields:emptyFields(),editing:null,preview:null,open:false})
    setDeleting(null);setNotice('这条记录已删除，回顾已更新。');onChanged()
  })
  return <section className="meal-journal" aria-label="实际餐食记录">
    <div className="journal-heading"><div><h2>吃过的，单独记下来</h2><p>选择行动、安排计划都不会自动成为用餐记录。</p></div>{!draft.open&&<button className="button-primary primary-action" onClick={()=>open()}>记录已吃的一餐</button>}</div>
    {draft.open&&<form ref={formRef} className="journal-form" onSubmit={e=>{e.preventDefault();void preview()}}>
      <h3>{draft.editing?'修改这条记录':'记下实际吃过的一餐'}</h3>
      <fieldset disabled={busy}><div className="journal-fields">
        <label>用餐日期<input aria-label="用餐日期" type="date" value={draft.fields.meal_date} onChange={e=>change('meal_date',e.target.value)}/></label>
        <label>餐次<select aria-label="实际用餐餐次" value={draft.fields.meal_slot} onChange={e=>change('meal_slot',e.target.value)}>{slots.map(slot=><option key={slot.value} value={slot.value}>{slot.label}{slot.value===suggestedSlot()?' · 根据当前时间':''}</option>)}</select></label>
        <label className="journal-name">吃了什么<input ref={nameRef} aria-label="实际餐食名称" value={draft.fields.name} onChange={e=>change('name',e.target.value)} placeholder="例如：番茄鸡蛋面"/></label>
        <label>份量（可留空）<input aria-label="实际餐食份量" inputMode="decimal" value={draft.fields.quantity} onChange={e=>change('quantity',e.target.value)} placeholder="不确定就留空"/></label>
        <label>单位<select aria-label="实际餐食单位" disabled={!draft.fields.quantity.trim()} value={draft.fields.unit} onChange={e=>change('unit',e.target.value)}>{['份','个','g','kg','ml','l','件','包','瓶'].map(unit=><option key={unit}>{unit}</option>)}</select></label>
        {matchingPlanItems.length>0&&<label className="journal-plan-link">关联这餐计划（可选）<select aria-label="关联计划餐次" value={draft.fields.plan_item_id??''} onChange={e=>{const selected=matchingPlanItems.find(entry=>entry.item.item_id===e.target.value);setDraft(current=>({...current,fields:{...current.fields,plan_id:selected?.plan.plan_id,plan_item_id:selected?.item.item_id},preview:null}))}}><option value="">暂不关联</option>{matchingPlanItems.map(({plan,item})=><option value={item.item_id} key={`${plan.plan_id}-${item.item_id}`}>{item.name} · {plan.start_date} 的安排</option>)}</select></label>}
      </div></fieldset>
      <p className="field-help">餐次会先按当前时间预选，你可以随时改成实际情况。份量留空会保存为未知，不会按 0 计算。</p>
      <div className="button-row"><button className="button-primary primary-action" disabled={busy} type="submit">{busy?'正在处理…':'预览这条记录'}</button><button className="button-secondary secondary" disabled={busy} type="button" onClick={()=>{setDraft({fields:emptyFields(),editing:null,preview:null,open:false});setError('')}}>取消填写</button></div>
      {draft.preview&&<section className="review-card" aria-label="实际餐食预览"><h3>核对后再保存</h3><p>{draft.preview.meal_date} · {label(draft.preview.meal_slot)}</p><p><strong>{draft.preview.name}</strong> · {draft.preview.quantity==null?'份量未知':`${draft.preview.quantity}${draft.preview.unit}`}</p><button className="button-primary primary-action" type="button" disabled={busy} onClick={confirm}>{draft.editing?'确认修改记录':'确认保存这一餐'}</button></section>}
    </form>}
    {error&&<p className="error" role="alert">{error}</p>}{notice&&<p className="notice" role="status">{notice}</p>}
    {deleting&&<section className="review-card" aria-label="确认删除餐食记录"><h3>删除这条用餐记录？</h3><p>{deleting.meal_date} · {deleting.name}。删除后会从回顾中移除。</p><div className="button-row"><button className="button-primary primary-action" disabled={busy} onClick={remove}>确认删除这条记录</button><button className="button-secondary secondary" disabled={busy} onClick={()=>{setDeleting(null);setError('')}}>保留记录</button></div></section>}
    {loading&&<p className="busy-note" role="status">正在读取用餐记录…</p>}
    {loadError&&<div className="error-state"><p className="error" role="alert">{loadError}</p><button onClick={()=>setAttempt(value=>value+1)}>重新读取用餐记录</button></div>}
    {!loading&&!loadError&&(records.length?<><p className="result-summary">最近 {records.length} 条用餐记录（最多展示 20 条）</p><div className="journal-list">{records.map(record=><article key={record.record_id}><div><p>{record.meal_date} · {label(record.meal_slot)}</p><h3>{record.name}</h3><p>{record.quantity==null?'份量未知':`${record.quantity}${record.unit}`}</p></div><div className="journal-record-actions"><button disabled={busy} aria-label={`再记一次${record.name}`} onClick={()=>open(record,true)}>再记一次</button><button disabled={busy} aria-label={`修改餐食${record.name}`} onClick={()=>open(record)}>修改</button><button disabled={busy} aria-label={`删除餐食${record.name}`} onClick={()=>{setDeleting(record);setError('')}}>删除</button></div></article>)}</div></>:<div className="empty-state"><h3>还没有实际用餐记录</h3><p>从愿意记下的一餐开始，无需补齐过去。</p></div>)}
  </section>
}
