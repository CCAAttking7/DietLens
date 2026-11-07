import { useEffect, useRef, useState } from 'react'
import { api, type Task } from '../lib/api'
import { clearSessionDrafts } from '../lib/useSessionDraft'
import { StatusPill } from './StatusPill'

type Props = {userId:string;onSignOut?:()=>Promise<void>;onEditProfile:()=>void;onDataDeleted:()=>void;onResume:(task:Task)=>void|Promise<void>}
const message=(error:unknown,fallback:string)=>error instanceof Error?error.message:fallback
function updatedAt(value?:string) {
  if(!value)return ''
  const date=new Date(value)
  return Number.isNaN(date.getTime())?'':new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(date)
}
function taskSummary(task:Task) {
  const selected=task.candidates?.find(candidate=>candidate.action_id===task.selected_action_id)
  if(selected)return selected.behavior
  const linked=(task as any).linked_objects?.meal_record
  if(linked)return `${String(linked.name)} · ${linked.quantity==null?'份量未知':`${linked.quantity}${linked.unit}`}`
  if(String(task.task_type)==='plan' && (task as any).linked_objects?.plan_id)return '已保存的餐食安排，可继续查看或调整'
  if(String(task.task_type)==='reflect')return '阶段回顾与下一步调整'
  return Array.isArray(task.context?.options)?task.context.options.map(String).join('、'):'还没有补充餐食信息'
}
function taskKind(task:Task) {
  return ({quick_log:'快速记录', plan:'安排计划', explore:'查资料', reflect:'回顾', micro_action:'小行动'} as Record<string,string>)[String((task as any).task_type)] ?? '未完成事项'
}

export function SettingsScreen({userId,onSignOut,onEditProfile,onDataDeleted,onResume}:Props) {
  const [profile,setProfile]=useState<Record<string,any>|null>(null)
  const [profileLoading,setProfileLoading]=useState(true)
  const [profileError,setProfileError]=useState('')
  const [profileAttempt,setProfileAttempt]=useState(0)
  const [recent,setRecent]=useState<Task[]>([])
  const [recentLoading,setRecentLoading]=useState(true)
  const [recentError,setRecentError]=useState('')
  const [recentAttempt,setRecentAttempt]=useState(0)
  const [resumeError,setResumeError]=useState('')
  const [taskId,setTaskId]=useState('')
  const [task,setTask]=useState<Task|null>(null)
  const [lookupError,setLookupError]=useState('')
  const [busy,setBusy]=useState('')
  const [dataError,setDataError]=useState('')
  const [notice,setNotice]=useState('')
  const [deleteOpen,setDeleteOpen]=useState(false)
  const deleteCancelRef=useRef<HTMLButtonElement>(null)
  const deleteTriggerRef=useRef<HTMLButtonElement>(null)
  const deleteDialogRef=useRef<HTMLElement>(null)
  const busyRef=useRef(busy)
  busyRef.current=busy
  useEffect(()=>{
    if(!deleteOpen)return
    const previous=deleteTriggerRef.current ?? document.activeElement as HTMLElement|null
    const focusTarget=deleteCancelRef.current
    if (focusTarget && !focusTarget.disabled) focusTarget.focus()
    else deleteDialogRef.current?.focus()
    const onKeyDown=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){
        event.preventDefault()
        event.stopPropagation()
        if(!busyRef.current)setDeleteOpen(false)
        return
      }
      if(event.key!=='Tab')return
      event.stopPropagation()
      const dialog=deleteDialogRef.current
      if(!dialog)return
      if(busyRef.current){event.preventDefault();dialog.focus();return}
      const items=Array.from(dialog.querySelectorAll<HTMLElement>('button:not([disabled]),[href]:not([aria-disabled="true"]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')).filter(item=>{
        const style=window.getComputedStyle(item)
        return style.display!=='none'&&style.visibility!=='hidden'&&item.getClientRects().length>0
      })
      if(!items.length){dialog.focus();return}
      const first=items[0],last=items[items.length-1]
      const current=document.activeElement as HTMLElement|null
      if(!dialog.contains(current)){first.focus();return}
      if(current===dialog){(event.shiftKey?last:first).focus();return}
      const index=current ? items.indexOf(current) : -1
      if(index<0){(event.shiftKey?last:first).focus();return}
      if(event.shiftKey&&index===0){event.preventDefault();last.focus()}
      else if(!event.shiftKey&&index===items.length-1){event.preventDefault();first.focus()}
    }
    window.addEventListener('keydown',onKeyDown,true)
    return()=>{window.removeEventListener('keydown',onKeyDown,true);if(previous?.isConnected)previous.focus()}
  },[deleteOpen])
  useEffect(()=>{
    if(!deleteOpen||busy!=='delete')return
    const keepFocus=()=>{if(deleteDialogRef.current&&!deleteDialogRef.current.contains(document.activeElement))deleteDialogRef.current.focus()}
    keepFocus()
    document.addEventListener('focusin',keepFocus,true)
    return()=>document.removeEventListener('focusin',keepFocus,true)
  },[busy,deleteOpen])
  useEffect(()=>{
    let active=true;setProfileLoading(true);setProfileError('')
    api.profile(userId).then(result=>{if(active)setProfile(result)}).catch(e=>{
      if(!active)return
      if(e instanceof Error&&e.message==='profile_not_found')setProfile(null)
      else setProfileError(message(e,'档案暂时无法读取'))
    }).finally(()=>{if(active)setProfileLoading(false)})
    return()=>{active=false}
  },[userId,profileAttempt])
  useEffect(()=>{
    let active=true;setRecentLoading(true);setRecentError('')
    api.recentTasks(userId).then(result=>{if(active)setRecent(result)}).catch(e=>{if(active)setRecentError(message(e,'最近的餐次暂时无法读取'))}).finally(()=>{if(active)setRecentLoading(false)})
    return()=>{active=false}
  },[userId,recentAttempt])
  async function resume(selected:Task) {
    if(busy)return
    setBusy(`resume:${selected.task_id}`);setResumeError('')
    try{onResume(await api.task(selected.task_id))}catch(e){setResumeError(message(e,'暂时无法恢复，请重试'))}finally{setBusy('')}
  }
  async function lookup() {
    if(busy||!taskId.trim())return
    setBusy('lookup');setLookupError('');setTask(null)
    try{setTask(await api.task(taskId.trim()))}catch(e){setLookupError(message(e,'找不到这餐记录，或它不属于当前账号'))}finally{setBusy('')}
  }
  async function exportData() {
    if(busy)return
    setBusy('export');setDataError('');setNotice('')
    try{
      const payload=await api.exportData(userId)
      const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}))
      const anchor=document.createElement('a');anchor.href=url;anchor.download=`dietlens-${userId}-export.json`;anchor.click()
      window.setTimeout(()=>URL.revokeObjectURL(url),1000)
      setNotice('已生成本地导出文件。')
    }catch(e){setDataError(message(e,'导出暂时不可用'))}finally{setBusy('')}
  }
  async function deleteData() {
    if(busy)return
    setBusy('delete');setDataError('');setNotice('')
    try{await api.deleteData(userId);clearSessionDrafts(userId);setDeleteOpen(false);onDataDeleted()}catch(e){setDataError(message(e,'删除暂时不可用'))}finally{setBusy('')}
  }
  async function signOut() {
    if(busy)return
    setBusy('signout');setDataError('')
    try{await onSignOut?.()}catch{setDataError('退出未完成，请重试。')}finally{setBusy('')}
  }
  return <div className="workspace settings-workspace"><section className="workspace-main">
    <p className="eyebrow">你的空间 · 随时调整</p><h1>你的决定始终在手里，<br/><em>随时可以收回来。</em></h1>
    <p className="lede">管理饮食档案和授权，找回未完成的一餐，或带走自己的数据。</p>
    <section className="settings-card" aria-label="档案设置"><h2>饮食档案与授权</h2>
      {profileLoading?<p role="status">正在读取饮食档案…</p>:profileError?<div className="error-state"><p className="error" role="alert">{profileError}</p><button onClick={()=>setProfileAttempt(value=>value+1)}>重新读取档案</button></div>:profile?<>
        <p>{profile.goal||'还没有填写饮食目标'}</p>
        <dl className="profile-facts"><div><dt>参考预算</dt><dd>{profile.budget==null?'未设置':`${profile.budget} 元 / 餐`}</dd></div><div><dt>过敏信息</dt><dd>{profile.allergies?.length?profile.allergies.join('、'):'未提供过敏信息'}</dd></div><div><dt>不能接受</dt><dd>{profile.hard_avoids?.length?profile.hard_avoids.join('、'):'未提供'}</dd></div></dl>
        <div className="setting-row"><span>历史回顾</span><strong>{profile.consents?.review_history?'已开启':'未开启'}</strong></div>
        <p className="field-help">仅在开启后汇总历史记录。随时可以在档案中关闭。</p>
        <div className="button-row"><button disabled={Boolean(busy)} onClick={onEditProfile}>编辑档案与授权</button></div>
      </>:<><p>填写目标和饮食边界，再开始这一餐。</p><div className="button-row"><button disabled={Boolean(busy)} onClick={onEditProfile}>设置饮食档案</button></div></>}
    </section>
    <section className="settings-card" aria-label="最近餐次"><h2>最近的餐次</h2><p>选择一餐，从上次停下的地方继续。最多展示最近 20 餐。</p>
      {recentLoading?<p role="status">正在读取最近餐次…</p>:recentError?<div className="error-state"><p className="error" role="alert">{recentError}</p><button onClick={()=>setRecentAttempt(value=>value+1)}>重新读取最近餐次</button></div>:recent.length?<div className="recent-tasks">{recent.map(item=><button key={item.task_id} disabled={Boolean(busy)} onClick={()=>resume(item)}>
        <span className="recent-task-copy"><strong><span className="task-kind">{taskKind(item)}</span>{String(item.context?.meal??'待补充的事项')}</strong><span>{taskSummary(item)}</span>{item.updated_at&&<time dateTime={item.updated_at}>{updatedAt(item.updated_at)}</time>}</span>
        <StatusPill state={item.state}/><span aria-hidden="true">{busy===`resume:${item.task_id}`?'…':'↗'}</span>
      </button>)}</div>:<p>还没有餐次记录。开始描述这一餐后，会出现在这里。</p>}
      {resumeError&&<p className="error" role="alert">{resumeError}</p>}
    </section>
    <details className="settings-card recovery-details"><summary>通过编号找回一餐</summary><p>如果你保存过这餐的编号，可以在这里查找。只能读取当前账号的记录。</p>
      <form className="search-form" onSubmit={e=>{e.preventDefault();void lookup()}}><input disabled={Boolean(busy)} aria-label="任务 ID" value={taskId} onChange={e=>{setTaskId(e.target.value);setTask(null);setLookupError('')}} placeholder="粘贴记录编号" maxLength={128}/><button type="submit" disabled={Boolean(busy)||!taskId.trim()}>{busy==='lookup'?'正在查找…':'查找'}</button></form>
      {lookupError&&<p className="error" role="alert">{lookupError}</p>}
      {task&&<div className="lookup-result"><h3>{String(task.context?.meal??'待补充的餐次')}</h3><p>{taskSummary(task)}</p><StatusPill state={task.state}/><div className="button-row"><button disabled={Boolean(busy)} onClick={()=>resume(task)}>继续这一餐</button></div></div>}
    </details>
    <section className="settings-card" aria-label="数据管理"><h2>你的数据</h2><p>导出会下载包含档案、计划和记录的 JSON 文件。删除会清除当前账号的全部 DietLens 数据和本页草稿，需要再次确认。</p>
      <div className="button-row"><button className="button-primary" onClick={exportData} disabled={Boolean(busy)}>{busy==='export'?'正在准备导出…':'导出数据'}</button><button ref={deleteTriggerRef} className="button-secondary secondary" onClick={()=>setDeleteOpen(true)} disabled={Boolean(busy)}>删除全部数据</button>{onSignOut&&<button className="button-secondary secondary" onClick={signOut} disabled={Boolean(busy)}>{busy==='signout'?'正在退出…':'退出登录'}</button>}</div>
      {notice&&<p className="notice" role="status">{notice}</p>}{dataError&&<p className="error" role="alert">{dataError}</p>}
    </section>
  </section><aside className="status-card"><p className="eyebrow">属于你的空间</p><h2>可以继续，也可以收回</h2><p>查找一餐只会读取它的状态。选择行动、反馈和修改数据，仍然需要你明确确认。</p></aside>
  {deleteOpen&&<div className="confirm-modal-layer" role="presentation" onClick={()=>!busy&&setDeleteOpen(false)}><section ref={deleteDialogRef} className="confirm-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title" aria-describedby="delete-description" tabIndex={-1} onClick={e=>e.stopPropagation()} onKeyDownCapture={event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();if(!busyRef.current)setDeleteOpen(false)}else if(event.key==='Tab'&&busyRef.current){event.preventDefault();event.stopPropagation();deleteDialogRef.current?.focus()}}}><p className="eyebrow">关键操作 · 需要确认</p><h2 id="delete-title">删除当前账号的全部数据？</h2><p id="delete-description">档案、计划、餐食记录和本页草稿都会被清除。此操作无法撤回。</p><div className="button-row"><button ref={deleteCancelRef} className="button-secondary secondary" onClick={()=>setDeleteOpen(false)} disabled={Boolean(busy)}>先保留</button><button className="button-destructive danger-action" onClick={()=>void deleteData()} disabled={Boolean(busy)}>{busy==='delete'?'正在删除…':'确认删除'}</button></div></section></div>}
  </div>
}
