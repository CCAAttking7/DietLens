import { useEffect, useRef, useState } from 'react'
import { loadTool } from './components/ToolLoader'
import { api, setAccessToken, type Candidate, type ProfileDraft, type Task, type TaskEvent, type TaskState } from './lib/api'
import { getSupabase } from './lib/supabase'
import type { Session, SupabaseClient } from '@supabase/supabase-js'
import './styles/tokens.css'
import { focusableWithin } from './lib/focus'
import { useSessionDraft, clearSessionDrafts, writeSessionDraft, removeSessionDraft } from './lib/useSessionDraft'
import { useScreen, screenLabels, type Screen } from './lib/useScreen'

const SettingsScreen = loadTool(async () => { const module = await import('./components/SettingsScreen'); return {default: module.SettingsScreen} }, '设置')
const FoodScreen = loadTool(async () => { const module = await import('./components/FoodScreen'); return {default: module.FoodScreen} }, '食品资料')
const PlanScreen = loadTool(async () => { const module = await import('./components/PlanScreen'); return {default: module.PlanScreen} }, '饮食计划')
const InventoryScreen = loadTool(async () => { const module = await import('./components/InventoryScreen'); return {default: module.InventoryScreen} }, '食材库存')
const WorkbenchScreen = loadTool(async () => { const module = await import('./components/WorkbenchScreen'); return {default: module.WorkbenchScreen} }, '饮食回顾')

type Intent = { user_message?: string; entities?: { meal?: string; options?: string[] }; missing_fields?: string[]; confidence?: number }
const demoUserId = 'web-demo-user'
const today = () => { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}` }
const eventLabel = (name: string) => ({
  'task.created': '开始这一餐', 'context.confirmed': '确认了餐次和可选项', 'candidates.generated': '整理出可比较的路径',
  'action.decision_saved': '记下了你的选择', 'action.feedback_saved': '保存了这次反馈',
  'action.feedback_corrected': '修正了这次反馈', 'action.reminder_sent': '把行动放回稍后的节奏',
  'review.generated': '生成了这段回顾',
} as Record<string,string>)[name] ?? '更新了这条记录'
const formatEventTime = (value: string) => { const date = new Date(value); return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(date) }

export default function App() {
  const [screen, setScreen] = useScreen()
  const [recordingMeal, setRecordingMeal] = useState(false)
  const [mobileMore, setMobileMore] = useState(false)
  const mobileMoreRef = useRef<HTMLDivElement>(null)
  const mobileMoreTriggerRef = useRef<HTMLButtonElement>(null)
  const [setupReturn, setSetupReturn] = useState<Screen>(screen)
  const [setupStart, setSetupStart] = useState(0)
  const drawerRef = useRef<HTMLElement>(null)
  const returnFocus = useRef<HTMLElement | null>(null)
  const panelWasOpen = useRef(false)
  const [onboarding, setOnboarding] = useState(true)
  const [hasProfile, setHasProfile] = useState(false)
  const [profileVersion, setProfileVersion] = useState(0)
  const [setupCompletion, setSetupCompletion] = useState(0)
  const [resetNotice, setResetNotice] = useState('')
  const [profileReady, setProfileReady] = useState(false)
  const [workspaceRevision, setWorkspaceRevision] = useState(0)
  const [session, setSession] = useState<Session | null>(null)
  const [supabase, setSupabase] = useState<SupabaseClient | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [authMode, setAuthMode] = useState<'demo' | 'supabase' | null>(null)
  const [startupError, setStartupError] = useState('')
  const [startupAttempt, setStartupAttempt] = useState(0)
  const [profileError, setProfileError] = useState('')
  const [profileOwner, setProfileOwner] = useState('')
  const previousUser = useRef<string | null>(null)
  useEffect(() => {
    let active = true
    setStartupError('')
    api.status().then(status => {
      if (active) {
        if (!['demo', 'supabase'].includes(status.auth_mode)) throw new Error('服务配置暂时不可用。')
        setAuthMode(status.auth_mode)
      }
    }).catch(e => { if (active) setStartupError(e instanceof Error ? e.message : '暂时无法连接服务。') })
    return () => { active = false }
  }, [startupAttempt])
  useEffect(() => {
    if (!authMode) return
    if (authMode === 'demo') { setSession(null); setAccessToken(null); setAuthReady(true); return }
    let active = true
    let receivedEvent = false
    let unsubscribe: (() => void) | undefined
    const applySession = (next: Session | null) => {
      if (!active) return
      const nextId = next?.user.id ?? null
      if (previousUser.current && previousUser.current !== nextId) {
        clearSessionDrafts(previousUser.current)
        setResetNotice('')
        setScreen('care'); setWorkspaceRevision(value => value + 1)
      }
      previousUser.current = nextId
      setSession(next); setAccessToken(next?.access_token ?? null); setAuthReady(true)
    }
    getSupabase().then(client => {
      if (!active) return
      if (!client) { setStartupError('登录服务尚未配置，请检查前端 Supabase 配置。'); return }
      setSupabase(client)
      const { data: listener } = client.auth.onAuthStateChange((_event, next) => { receivedEvent = true; applySession(next) })
      unsubscribe = () => listener.subscription.unsubscribe()
      return client.auth.getSession().then(({data,error}) => {
        if (active && !receivedEvent) {
          if (error) setStartupError('无法恢复登录状态，请重试。')
          else applySession(data.session)
        }
      })
    }).catch(() => { if (active) setStartupError('登录服务暂时未能加载，请检查网络后重试。') })
    return () => { active = false; unsubscribe?.() }
  }, [authMode, startupAttempt])
  const userId = authMode === 'supabase' ? session?.user.id ?? '' : demoUserId
  useEffect(() => {
    if (!authReady || !userId) return
    let active = true
    setProfileReady(false); setProfileError('')
    api.profile(userId).then(profile => { if (active) { setOnboarding(false); setHasProfile(true); setProfileVersion(Number(profile.version??0)) } }).catch(e => {
      if (!active) return
      if (e instanceof Error && e.message === 'profile_not_found') { setOnboarding(true); setHasProfile(false) }
      else setProfileError(e instanceof Error ? e.message : '档案暂时无法读取。')
    }).finally(() => { if (active) { setProfileReady(true); setProfileOwner(userId) } })
    return () => { active = false }
  }, [authReady, userId, startupAttempt])
  const signOut = async () => { if (supabase) { const { error } = await supabase.auth.signOut(); if (error) throw error; clearSessionDrafts(userId); setWorkspaceRevision(value => value + 1) } }
  const openPanel = (next: Screen) => {
    if (screen === 'care') returnFocus.current = document.activeElement as HTMLElement | null
    setRecordingMeal(false); setScreen(next)
  }
  const editProfile = (returnTo: Screen, step = 0) => { setSetupReturn(returnTo); setSetupStart(step); setOnboarding(true) }
  const panelOpen = screen !== 'care' && !onboarding && profileReady && profileOwner === userId && !profileError
  useEffect(() => {
    if (!mobileMore) return
    const previous = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    const previousScrollY = window.scrollY
    document.body.style.overflow = 'hidden'
    const first = mobileMoreRef.current?.querySelector<HTMLElement>('button')
    first?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); setMobileMore(false); return }
      if (event.key !== 'Tab') return
      event.stopPropagation()
      const items = focusableWithin(mobileMoreRef.current)
      if (!items?.length) return
      const firstItem = items[0], lastItem = items[items.length - 1]
      if (event.shiftKey && document.activeElement === firstItem) { event.preventDefault(); lastItem.focus() }
      else if (!event.shiftKey && document.activeElement === lastItem) { event.preventDefault(); firstItem.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => { document.body.style.overflow = previousOverflow; window.scrollTo(0, previousScrollY); document.removeEventListener('keydown', onKeyDown); if (previous?.isConnected) window.setTimeout(() => previous.focus(), 0) }
  }, [mobileMore])
  useEffect(() => { document.title = `${onboarding ? '饮食档案' : screenLabels[screen]} · DietLens` }, [screen, onboarding])
  useEffect(() => {
    if (!panelOpen) {
      if (panelWasOpen.current && !onboarding) {
        const target = returnFocus.current
        if (target?.isConnected) target.focus()
        else document.querySelector<HTMLButtonElement>('.side-nav button')?.focus()
        returnFocus.current = null
      }
      panelWasOpen.current = false
      return
    }
    panelWasOpen.current = true
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    drawerRef.current?.focus()
    if (drawerRef.current) drawerRef.current.scrollTop = 0
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented && !(event.target instanceof HTMLElement && event.target.closest('.confirm-modal-layer, .mobile-more-sheet'))) setScreen('care')
      if (event.key !== 'Tab') return
      const items = focusableWithin(drawerRef.current)
      if (!items?.length) return
      const first = items[0], last = items[items.length - 1]
      if (event.shiftKey && (document.activeElement === first || document.activeElement === drawerRef.current)) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && (document.activeElement === last || document.activeElement === drawerRef.current)) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => { window.removeEventListener('keydown', closeOnEscape); document.body.style.overflow = overflow }
  }, [screen, panelOpen, onboarding, setScreen])
  if (startupError) return <main className="auth-shell"><section className="auth-card"><h1>暂时未能连接</h1><p className="error" role="alert">{startupError}</p><div className="button-row"><button className="button-primary primary-action" onClick={() => setStartupAttempt(value => value + 1)}>重新连接</button><button className="button-secondary secondary" onClick={() => window.location.reload()}>重新载入页面</button></div></section></main>
  if (!authReady) return <main className="loading-shell"><span className="spinner" /><p role="status">正在准备你的空间…</p></main>
  if (authMode === 'supabase' && !session && supabase) return <AuthScreen client={supabase} />
  if (!profileReady || profileOwner !== userId) return <main className="loading-shell"><span className="spinner" /><p role="status">正在读取饮食档案…</p></main>
  if (profileError) return <main className="auth-shell"><section className="auth-card"><h1>档案暂时无法读取</h1><p className="error" role="alert">{profileError}</p><div className="button-row"><button className="button-primary primary-action" onClick={() => setStartupAttempt(value => value + 1)}>重新读取</button>{session && <button className="button-secondary secondary" onClick={() => signOut().catch(() => setProfileError('退出未完成，请稍后重试。'))}>重新登录</button>}</div></section></main>
  return <main className="product-shell">
    <aside className="sidebar" inert={panelOpen || onboarding || mobileMore}>
      <div className="brand"><span className="brand-mark">D</span><span>DietLens</span></div>
      <div className="side-date">{new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' }).format(new Date())}</div>
      <nav className="side-nav" aria-label="主要页面">
        <button aria-current={screen === 'care' ? 'page' : undefined} data-tooltip="记录今天的饮食" className={screen === 'care' ? 'side-active' : ''} onClick={() => openPanel('care')}><span>✦</span>今日饮食</button>
        <button aria-current={screen === 'plan' ? 'page' : undefined} data-tooltip="安排未来几天" className={screen === 'plan' ? 'side-active' : ''} onClick={() => openPanel('plan')}><span>▦</span>饮食计划</button>
        <button aria-current={screen === 'food' ? 'page' : undefined} data-tooltip="查看来源和未知项" className={screen === 'food' ? 'side-active' : ''} onClick={() => openPanel('food')}><span>◌</span>食品资料</button>
        <button aria-current={screen === 'inventory' ? 'page' : undefined} data-tooltip="看看已有的食材" className={screen === 'inventory' ? 'side-active' : ''} onClick={() => openPanel('inventory')}><span>□</span>食材库存</button>
        <button aria-current={screen === 'workbench' ? 'page' : undefined} data-tooltip="回看计划、记录和行动" className={screen === 'workbench' ? 'side-active' : ''} onClick={() => openPanel('workbench')}><span>↗</span>饮食回顾</button>
      </nav>
    <div className="sidebar-bottom"><button aria-current={screen === 'settings' ? 'page' : undefined} data-tooltip="档案、授权和数据" className={screen === 'settings' ? 'side-active' : ''} onClick={() => openPanel('settings')}><span>⚙</span>设置</button><div className="user-chip"><span className="avatar">{session?.user.email?.slice(0, 1).toUpperCase() ?? 'D'}</span><span>{session?.user.email ?? '演示空间'}</span></div></div>
    </aside>
    <nav className="mobile-nav" aria-label="移动端主要页面" inert={mobileMore || panelOpen || onboarding}>
      {(['care','plan','workbench'] as const).map(item => <button key={item} aria-current={screen === item ? 'page' : undefined} className={screen === item ? 'active' : ''} onClick={() => { setMobileMore(false); openPanel(item) }}><span aria-hidden="true">{item === 'care' ? '✦' : item === 'plan' ? '▦' : '↗'}</span>{screenLabels[item]}</button>)}
      <button ref={mobileMoreTriggerRef} id="mobile-more-trigger" aria-expanded={mobileMore} aria-controls="mobile-more-sheet" className={mobileMore || ['food','inventory','settings'].includes(screen) ? 'active' : ''} onClick={() => setMobileMore(value => !value)}><span aria-hidden="true">•••</span>更多</button>
    </nav>
    <div id="mobile-more-sheet" className="mobile-more-sheet" hidden={!mobileMore} role="dialog" aria-modal="true" aria-labelledby="mobile-more-title" onClick={() => setMobileMore(false)}><div ref={mobileMoreRef} className="mobile-more-panel" onClick={event => event.stopPropagation()}><div className="mobile-more-head"><h2 id="mobile-more-title">更多页面</h2><button className="mobile-more-close" aria-label="关闭更多页面" onClick={() => setMobileMore(false)}>×</button></div>{(['food','inventory','settings'] as const).map(item => <button key={item} aria-current={screen === item ? 'page' : undefined} className={screen === item ? 'active' : ''} onClick={() => { setMobileMore(false); openPanel(item) }}>{screenLabels[item]}<span aria-hidden="true">→</span></button>)}</div></div>
    <section className="main-stage" inert={panelOpen || onboarding || mobileMore}>
      <header className="stage-header"><div><p className="eyebrow">今天 · 轻一点</p><h2>陪你处理眼前这一餐</h2></div><div className="stage-actions"><span className="live-dot">{authMode === 'demo' ? '本地演示' : '私人空间'}</span><button className="button-quiet quiet-button" aria-label="打开设置" onClick={() => openPanel('settings')}>设</button></div></header>
      <CareScreen key={`${userId}:${workspaceRevision}`} userId={userId} setupCompletion={setupCompletion} onWorkbench={() => openPanel('workbench')} onPlan={() => openPanel('plan')} onFood={() => openPanel('food')} onInventory={() => openPanel('inventory')} onSetup={() => editProfile('care')} onRecord={() => { setRecordingMeal(true); setScreen('workbench') }} ready={hasProfile} />
    </section>
    {panelOpen && <div className="drawer-layer" onClick={() => setScreen('care')}><aside ref={drawerRef} className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title" tabIndex={-1} onClick={event => event.stopPropagation()}><div className="drawer-topbar"><div className="drawer-context"><button onClick={() => setScreen('care')}>← 回到这一餐</button><span id="drawer-title">{screenLabels[screen]} · 当前情境</span></div><button className="drawer-close" aria-label="关闭面板" onClick={() => setScreen('care')}>×</button><nav className="drawer-tools" aria-label="切换工具">{(['plan', 'food', 'inventory', 'workbench', 'settings'] as const).map(tool => <button key={tool} aria-current={screen === tool ? 'page' : undefined} aria-label={screenLabels[tool]} onClick={() => openPanel(tool)}>{{plan: '饮食计划', food: '食品资料', inventory: '食材库存', workbench: '饮食回顾', settings: '设置'}[tool]}</button>)}</nav></div>{screen === 'plan' && <PlanScreen key={userId} userId={userId} />}{screen === 'food' && <FoodScreen userId={userId} profileVersion={profileVersion} onEditProfile={() => editProfile('food', 1)} />}{screen === 'inventory' && <InventoryScreen key={userId} userId={userId} />}{screen === 'workbench' && <WorkbenchScreen userId={userId} initialRecording={recordingMeal} onEditConsent={() => editProfile('workbench', 2)} onStartAction={() => { setScreen('care'); setWorkspaceRevision(value => value + 1) }} />}{screen === 'settings' && <SettingsScreen userId={userId} onResume={async task => {
      if (task.task_type === 'quick_log' && task.pending_record) {
        const record = task.pending_record as Record<string, any>
        writeSessionDraft(`${userId}:actual-meal-draft`, { fields: { meal_date: String(record.meal_date ?? ''), meal_slot: String(record.meal_slot ?? 'lunch'), name: String(record.name ?? ''), quantity: record.quantity == null ? '' : String(record.quantity), unit: String(record.unit ?? '份') }, editing: null, preview: { ...record }, quickTaskId: task.task_id, open: true })
        setRecordingMeal(true); setScreen('workbench'); setWorkspaceRevision(value => value + 1)
      } else if (task.task_type === 'plan' && task.linked_objects?.plan_id) {
        try {
          const plan = await api.plan(String(task.linked_objects.plan_id))
          writeSessionDraft(`${userId}:plan-preview`, plan)
          setScreen('plan'); setWorkspaceRevision(value => value + 1)
        } catch {
          setScreen('plan'); setWorkspaceRevision(value => value + 1)
        }
      } else {
        for (const field of ['meal-intent','meal-messages','meal-message','meal-slot','meal-options']) removeSessionDraft(`${userId}:${field}`)
        writeSessionDraft(`${userId}:meal-task`, task)
        setScreen('care'); setWorkspaceRevision(value => value + 1)
      }
    }} onDataDeleted={() => { setResetNotice('数据已删除。当前账号的 DietLens 数据和本页草稿已清空，你可以重新设置，或稍后再开始。'); setScreen('care'); setOnboarding(true); setHasProfile(false); setWorkspaceRevision(value => value + 1) }} onEditProfile={() => editProfile('settings')} onSignOut={authMode === 'supabase' && session ? signOut : undefined} />}</aside></div>}
    {onboarding && <OnboardingDrawer userId={userId} initialStep={setupStart} notice={resetNotice} onComplete={(saved, version) => { setResetNotice(''); setOnboarding(false); setScreen(setupReturn); setSetupReturn('care'); setSetupStart(0); if (saved) { setProfileVersion(current => version && version > 0 ? version : current + 1); setHasProfile(true); setSetupCompletion(value => value + 1) } }} />}
  </main>
}

function OnboardingDrawer({ userId, initialStep = 0, notice, onComplete }: { userId: string; initialStep?: number; notice?: string; onComplete: (saved: boolean, version?: number) => void }) {
  const [step, setStep] = useState(initialStep)
  const dialogRef = useRef<HTMLElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialogRef.current?.focus()
    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return
      const items = focusableWithin(dialogRef.current)
      if (!items?.length) return
      const first = items[0], last = items[items.length - 1]
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.current)) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialogRef.current)) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', trapFocus)
    return () => { document.body.style.overflow = previousOverflow; document.removeEventListener('keydown', trapFocus); previous?.focus() }
  }, [])
  useEffect(() => { bodyRef.current?.scrollTo({ top: 0 }) }, [step])
  const [goal, setGoal] = useState('')
  const [lunchBudget, setLunchBudget] = useState('40')
  const [allergies, setAllergies] = useState('')
  const [hardAvoids, setHardAvoids] = useState('')
  const [dislikes, setDislikes] = useState('')
  const [reviewConsent, setReviewConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [profileLoading, setProfileLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [loadAttempt, setLoadAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setProfileLoading(true); setLoadError('')
    api.profile(userId).then(profile => {
      if (!active) return
      setGoal(profile.goal ?? '')
      setLunchBudget(profile.budget == null ? '' : String(profile.budget))
      setAllergies((profile.allergies ?? []).join('、'))
      setHardAvoids((profile.hard_avoids ?? []).join('、'))
      setDislikes((profile.dislikes ?? []).join('、'))
      setReviewConsent(Boolean(profile.consents?.review_history))
    }).catch(e => {
      if (active && !(e instanceof Error && e.message === 'profile_not_found')) setLoadError(e instanceof Error ? e.message : '档案读取失败，请重试。')
    }).finally(() => { if (active) setProfileLoading(false) })
    return () => { active = false }
  }, [userId, loadAttempt])
  const steps = [
    { kicker: '01 / 03', title: '先从你的目标开始', sub: '告诉我眼前想解决的问题。先从一餐开始就好。', content: <><label htmlFor="setup-goal">你希望 DietLens 先帮你处理什么？</label><textarea id="setup-goal" className="onboarding-textarea" value={goal} onChange={e => setGoal(e.target.value)} placeholder="例如：加班后想吃得简单一点，也不想超预算" /><label htmlFor="setup-budget">这一餐参考预算（元，可留空）</label><input id="setup-budget" type="number" min="0" step="0.01" value={lunchBudget} onChange={e => setLunchBudget(e.target.value)} placeholder="暂不设置" /><p className="field-help">只在有预算时填写，不会要求你规划完整一天。</p></> },
    { kicker: '02 / 03', title: '告诉我你的边界', sub: '未知会保持未知，只有你确认过的内容才会影响建议。', content: <><label>过敏或绝对忌口</label><input value={allergies} onChange={e => setAllergies(e.target.value)} placeholder="例如：花生、虾（可留空）" /><label>不太喜欢的食物</label><input value={dislikes} onChange={e => setDislikes(e.target.value)} placeholder="例如：香菜、太辣" /><label>不能接受的食物</label><input value={hardAvoids} onChange={e => setHardAvoids(e.target.value)} placeholder="没有就留空" /></> },
    { kicker: '03 / 03', title: '确认这份饮食档案', sub: '核对后再保存。只有以下内容会写入档案。', content: <><dl className="setup-summary"><div><dt>你的目标</dt><dd>{goal.trim() || '尚未填写，请回到第一步补充'}</dd></div><div><dt>参考预算</dt><dd>{lunchBudget.trim() ? `这一餐 ${lunchBudget} 元` : '暂不设置'}</dd></div><div><dt>过敏信息</dt><dd>{allergies.trim() || '未提供'}</dd></div><div><dt>不能接受</dt><dd>{hardAvoids.trim() || '未提供'}</dd></div><div><dt>不太喜欢</dt><dd>{dislikes.trim() || '未提供'}</dd></div></dl><label className="setup-consent"><input type="checkbox" checked={reviewConsent} onChange={e => setReviewConsent(e.target.checked)} /><span>允许在回顾中使用历史记录（可选）</span></label><div className="memory-note"><span>✦</span><p>点击“确认并进入”才会保存。未提供的信息会保持未知。</p></div></> },
  ]
  const next = async () => {
    if (busy || profileLoading || loadError) return
    if ((step === 0 || step === 2) && !goal.trim()) { setError('先写一句你想解决的问题，也可以选择“稍后设置”。'); setStep(0); requestAnimationFrame(() => document.getElementById('setup-goal')?.focus()); return }
    const budgetValue = lunchBudget.trim() ? Number(lunchBudget) : null
    if ((step === 0 || step === 2) && budgetValue !== null && (!Number.isFinite(budgetValue) || budgetValue < 0)) { setError('预算需要是非负数字，也可以留空。'); setStep(0); requestAnimationFrame(() => document.getElementById('setup-budget')?.focus()); return }
    setError('')
    if (step < 2) { setStep(step + 1); return }
    setBusy(true); setError('')
    try {
      const split = (value: string) => value.split(/[、,，]/).map(item => item.trim()).filter(Boolean)
      if (budgetValue !== null && (!Number.isFinite(budgetValue) || budgetValue < 0)) throw new Error('预算需要是非负数字，也可以留空')
      let version = 0
      try { const current = await api.profile(userId); version = Number(current.version ?? 0) } catch (e) { if (!(e instanceof Error) || e.message !== 'profile_not_found') throw e }
      const draft = await api.profilePreview({ user_id: userId, expected_version: version, changes: { goal: goal || null, budget: budgetValue, allergies: split(allergies), hard_avoids: split(hardAvoids), dislikes: split(dislikes) }, consents: { review_history: reviewConsent } })
      const confirmed = await api.profileConfirm({ user_id: userId, task_id: draft.task_id, operation_key: 'web-onboarding:' + draft.task_id, expected_version: draft.expected_version })
      onComplete(true, Number(confirmed.version ?? 0))
    } catch (e) { setError(e instanceof Error ? ({version_conflict:'档案已发生变化，请返回重新核对后保存。', authentication_required:'登录已失效，请重新登录后保存。', invalid_budget:'请检查预算，金额需要是非负数字。'}[e.message] ?? e.message) : '暂时无法保存，请稍后重试') } finally { setBusy(false) }
  }
  return <div className="onboarding-layer">
    <div className="onboarding-backdrop" />
    <aside ref={dialogRef} className="onboarding-drawer" role="dialog" aria-modal="true" aria-labelledby="onboarding-title" tabIndex={-1}>
      <div className="onboarding-top"><div className="brand"><span className="brand-mark">D</span><span>DietLens</span></div><button className="onboarding-skip" onClick={() => onComplete(false)} disabled={busy}>稍后设置</button></div>
      <nav className="onboarding-steps" aria-label="首次设置步骤">{['目标与预算', '饮食边界', '核对与确认'].map((label, index) => <button type="button" key={label} aria-current={step === index ? 'step' : undefined} className={step === index ? 'current' : ''} disabled={busy} onClick={() => { setError(''); setStep(index) }}><span>0{index + 1}</span>{label}</button>)}</nav>
      <div ref={bodyRef} className="onboarding-body">{notice && <p className="notice" role="status">{notice}</p>}<p className="eyebrow">{steps[step].kicker}</p><h1 id="onboarding-title">{steps[step].title}</h1><p className="onboarding-sub">{steps[step].sub}</p><div className="onboarding-fields">{steps[step].content}</div></div>
      <div className="onboarding-footer">{profileLoading && <p role="status">正在读取档案…</p>}{loadError && <div className="error-state"><p className="error" role="alert">{loadError}</p><button disabled={profileLoading} onClick={() => setLoadAttempt(value => value + 1)}>重新读取档案</button></div>}{error && <p className="error" role="alert">{error}</p>}<div className="onboarding-footer-row"><span>第 {step + 1} 步，共 3 步</span><div className="onboarding-actions"><button className="button-secondary secondary" disabled={busy || step === 0} onClick={() => { setError(''); setStep(step - 1) }}>上一步</button><button onClick={next} disabled={busy || profileLoading || Boolean(loadError)}>{busy ? '正在保存…' : step === 2 ? '确认并进入' : '下一步'}</button></div></div></div>
    </aside>
  </div>
}

function AuthScreen({client}: {client: SupabaseClient}) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [cooldown, setCooldown] = useState(0)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!cooldown) return
    const timer = window.setTimeout(() => setCooldown(value => value - 1), 1000)
    return () => window.clearTimeout(timer)
  }, [cooldown])
  const submit = async () => {
    if (!email.trim() || busy || cooldown) return
    setBusy(true); setError('')
    try {
      const { error: authError } = await client.auth.signInWithOtp({ email: email.trim(), options: { emailRedirectTo: window.location.origin } })
      if (authError) throw authError
      setSent(true); setCooldown(60)
    } catch { setError('登录链接暂时无法发送，请检查网络或稍后重试。') }
    finally { setBusy(false) }
  }
  return <main className="auth-shell"><section className="auth-card"><p className="eyebrow">DietLens · 私人空间</p><h1>从你的空间，<br/><em>开始这一餐。</em></h1><p className="lede">用邮箱登录，让你的档案、计划和餐次记录跟随同一个账号。</p>{sent ? <div><div className="notice" role="status">登录链接已发送到 {email}。请在当前浏览器中打开邮件里的链接。</div><p className="field-help">没有收到？可以检查垃圾邮件，或稍后重新发送。</p><div className="button-row"><button className="button-primary primary-action" disabled={busy || cooldown > 0} onClick={submit}>{cooldown ? `${cooldown} 秒后可重发` : '重新发送'}</button><button className="button-secondary secondary" onClick={() => { setSent(false); setError('') }}>修改邮箱</button></div></div> : <form className="composer" onSubmit={e => { e.preventDefault(); void submit() }}><label htmlFor="auth-email">邮箱</label><input id="auth-email" type="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email"/><button type="submit" disabled={busy || !email.trim() || cooldown > 0}>{busy ? '正在发送…' : cooldown ? `${cooldown} 秒后可重发` : '发送登录链接'}</button></form>}{error && <p className="error" role="alert">{error}</p>}</section></main>
}

function CareScreen({ userId, setupCompletion, onWorkbench, onPlan, onFood, onInventory, onSetup, onRecord, ready = false }: { userId: string; setupCompletion: number; onWorkbench: () => void; onPlan: () => void; onFood: () => void; onInventory: () => void; onSetup: () => void; onRecord: () => void; ready?: boolean }) {
  const [message, setMessage] = useSessionDraft(`${userId}:meal-message`, '')
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const [messages, setMessages] = useSessionDraft<Array<{ role: 'user' | 'assistant'; text: string }>>(`${userId}:meal-messages`, [])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [task, setTask] = useSessionDraft<Task | null>(`${userId}:meal-task`, null)
  const [intent, setIntent] = useSessionDraft<Intent | null>(`${userId}:meal-intent`, null)
  const [meal, setMeal] = useSessionDraft(`${userId}:meal-slot`, '')
  const [options, setOptions] = useSessionDraft(`${userId}:meal-options`, '')
  const [feedbackNote, setFeedbackNote] = useSessionDraft(`${userId}:meal-feedback-note`, '')
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [reminderDue, setReminderDue] = useState(false)
  const [taskEvents, setTaskEvents] = useState<TaskEvent[]>([])
  const [resumeTask, setResumeTask] = useState<Task | null>(null)
  const [todayPlanItems, setTodayPlanItems] = useState<Array<Record<string,any>>>([])
  const [notice, setNotice] = useState('')
  const [switchPending, setSwitchPending] = useState(false)
  const [readAttempt, setReadAttempt] = useState(0)
  const [profileContext, setProfileContext] = useState<Record<string, any> | null>(null)
  const switchRef = useRef<HTMLElement>(null)
  const contextRef = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 2600)
    return () => window.clearTimeout(timer)
  }, [notice])
  useEffect(() => {
    if (!ready) return
    let active = true
    api.profile(userId).then(profile => { if (active) setProfileContext(profile) }).catch(() => { if (active) setProfileContext(null) })
    return () => { active = false }
  }, [userId, ready, setupCompletion])
  useEffect(() => {
    if (!ready || task) { if (task) setResumeTask(null); return }
    let active = true
    api.recentTasks(userId).then(items => {
      if (!active) return
      const pending = items.find(item => item.task_type === 'micro_action' && ['created','context','candidates','awaiting_confirmation','adopted'].includes(item.state))
      setResumeTask(pending ?? null)
    }).catch(() => { if (active) setResumeTask(null) })
    return () => { active = false }
  }, [userId, ready, task?.task_id])
  useEffect(() => {
    if (!ready) { setTodayPlanItems([]); return }
    let active = true
    api.plans(userId).then(plans => {
      if (!active) return
      const items = plans.filter(plan => plan.status === 'confirmed').flatMap(plan => plan.items.filter(item => String(item.meal_date) === today()).map(item => ({...item, plan_id: plan.plan_id})))
      setTodayPlanItems(items)
    }).catch(() => { if (active) setTodayPlanItems([]) })
    return () => { active = false }
  }, [userId, ready, setupCompletion])
  useEffect(() => {
    if (switchPending) {
      switchRef.current?.scrollIntoView({block:'center',behavior:'smooth'})
      switchRef.current?.focus({preventScroll:true})
    }
  }, [switchPending])
  useEffect(() => {
    if (task?.state !== 'adopted' || !profileContext?.consents?.reminders) { setReminderDue(false); return }
    let active = true
    api.reminderStatus(task.task_id).then(status => { if (active) setReminderDue(Boolean(status.eligible && status.due)) }).catch(() => { if (active) setReminderDue(false) })
    return () => { active = false }
  }, [task?.task_id, task?.state, profileContext?.consents?.reminders])
  useEffect(() => {
    if (!task?.task_id) { setTaskEvents([]); return }
    let active = true
    api.taskEvents(task.task_id).then(events => { if (active) setTaskEvents(events) }).catch(() => { if (active) setTaskEvents([]) })
    return () => { active = false }
  }, [task?.task_id, task?.version])
  const startManual = async () => {
    if (busy) return
    setBusy(true); setError('')
    try {
      if (!task || task.state !== 'created') {
        const created = await api.createTask({ user_id: userId })
        setTask({ ...created, state: 'created', version: 0 })
      }
      setIntent({}); setNotice('直接填写餐次和可选餐食，核对后继续。原来的描述已保留。')
      requestAnimationFrame(() => {
        contextRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
        contextRef.current?.querySelector('input')?.focus({ preventScroll: true })
      })
    } catch (e) { setError(e instanceof Error ? e.message : '暂时无法开始，请重试。') }
    finally { setBusy(false) }
  }
  useEffect(() => {
    if (!setupCompletion) return
    setError(''); setNotice('饮食档案已保存。接下来，描述你眼前这一餐。')
    composerRef.current?.focus()
  }, [setupCompletion])
  useEffect(() => {
    if (!task?.task_id) return
    let active = true
    setBusy(true); setError('')
    api.task(task.task_id).then(current => {
      if (!active) return
      setTask(current)
      if (current.state !== 'created') setIntent(null)
      setNotice('已恢复这一餐，可以从上次停下的地方继续。')
    }).catch(e => { if (active) setError(e instanceof Error ? e.message : '无法恢复这一餐，请重试') })
      .finally(() => { if (active) setBusy(false) })
    return () => { active = false }
    // Revalidate a cached task on mount; subsequent commands return fresh server state.
  }, [userId, readAttempt])
  const send = async (allowSwitch = false) => {
    if (!message.trim() || busy) return
    if (!ready) { setError('先确认饮食档案，再开始这一餐。你填写的描述会保留。'); return }
    if (!allowSwitch && task && ['awaiting_confirmation','adopted','context','candidates'].includes(task.state)) { setSwitchPending(true); return }
    const text = message.trim(); setBusy(true); setError('')
    try {
      const reuse = task?.state === 'created'
      const created = reuse ? task : await api.createTask({ user_id: userId })
      setSwitchPending(false); setIntent(null); setNotice('')
      setTask({ ...created, state: 'created', version: 'version' in created ? Number(created.version) : 0 })
      setMessages(current => {
        const previous = reuse ? current : []
        const last = previous[previous.length - 1]
        return last?.role === 'user' && last.text === text ? previous : [...previous, {role:'user',text}]
      })
      const parsed = await api.sendMessage(created.task_id, text)
      const intent = parsed.intent as Intent
      setTask(parsed.task); setIntent(intent); setMeal(intent.entities?.meal ?? ''); setOptions((intent.entities?.options ?? []).join('、')); setMessage('')
      const meal = intent.entities?.meal
      const options = intent.entities?.options ?? []
      setMessages(current => {
        const lead = meal && options.length ? `我先把你刚才说的放在一起：${meal}，现在手边有 ${options.join('、')}。` : (intent.user_message ?? '我还需要一点信息，才能帮你继续。')
        const follow = meal && options.length ? '先不急着做决定。你可以修改我听到的内容；确认后，我会根据你的边界、预算和今天的精力，给出几条不同负担的下一步。' : '你可以补充餐次或眼前的可选项，也可以直接手动填写。'
        return [...current, { role: 'assistant', text: lead }, { role: 'assistant', text: follow }]
      })
    } catch (e) { setError(e instanceof Error ? e.message : '暂时无法连接，请稍后重试') } finally { setBusy(false) }
  }
  async function advance(action: () => Promise<Task>) {
    if (busy) return
    setBusy(true); setError('')
    try { setTask(await action()); setIntent(null); setSwitchPending(false) }
    catch (e) { setError(e instanceof Error ? e.message : '操作未完成，请重试') }
    finally { setBusy(false) }
  }
  const quick = ['午餐可选鸡肉饭和番茄面，帮我整理一下', '晚餐有米饭和蔬菜面，想简单一点']
  const selectedAction = task?.candidates?.find(candidate => candidate.action_id === task.selected_action_id)
  const journeyState = task?.state === 'awaiting_confirmation' ? 1 : task?.state === 'adopted' ? 2 : ['feedback','review','done'].includes(task?.state ?? '') ? 3 : 0
  const journey = [{title:'看清眼前', hint:'先把这一餐说清楚'}, {title:'比较路径', hint:'看看哪一步适合今天'}, {title:'做一个选择', hint:'只记录你的打算'}, {title:'回来回看', hint:'把经验留给下一次'}]
  return <div className="chat-board">
    <div className="board-decor decor-lemon" aria-hidden="true" /><div className="board-decor decor-leaf" aria-hidden="true" /><div className="board-decor decor-tomato" aria-hidden="true" />
    <div className="chat-column">
      <div className={messages.length ? "chat-welcome compact" : "chat-welcome"}><span className="welcome-mark">D</span><p className="eyebrow">{ready ? '档案已准备好 · 今天' : 'DietLens · 今天'}</p><h1>{ready ? <>从你现在面对的<br/><em>这一餐开始。</em></> : <>把饮食这件事，<br/><em>变得轻一点。</em></>}</h1><p>{ready ? '告诉我你现在的时间、地点和可选项。我会先整理，再把决定交还给你。' : '一个可以记住你的目标、边界和节奏的饮食陪伴。'}</p></div>
      {ready && <nav className="journey-strip" aria-label="这一餐的进度">{journey.map((item,index)=><div className={`journey-step ${index === journeyState ? 'current' : ''} ${index < journeyState ? 'passed' : ''}`} key={item.title}><span className="journey-index">{index < journeyState ? '✓' : `0${index + 1}`}</span><span><strong>{item.title}</strong><small>{item.hint}</small></span></div>)}</nav>}
      {messages.length > 0 && <div className="chat-thread">{messages.map((item, index) => <div className={item.role === 'user' ? 'chat-bubble user' : 'chat-bubble assistant'} key={index}>{item.text}</div>)}</div>}
      {busy && <p className="busy-note" role="status"><span className="spinner" />正在处理，请稍候…</p>}
      {intent && task && <section ref={contextRef} className="meal-flow-card" aria-label="核对这一餐"><p className="eyebrow">第一步 · 核对理解</p><h2>这些信息对吗？</h2><p>可以直接修改，再继续。</p><label>餐次<input value={meal} onChange={e => setMeal(e.target.value)} placeholder="例如：午餐" /></label><label>可选餐食<input value={options} onChange={e => setOptions(e.target.value)} placeholder="用顿号分隔，例如：鸡肉饭、番茄面" /></label><div className="button-row"><button className="button-primary" disabled={busy || !meal.trim() || !options.split(/[、，,]/).some(v => v.trim())} onClick={() => advance(() => api.confirmContext(task.task_id, meal.trim(), options.split(/[、，,]/).map(v => v.trim()).filter(Boolean)))}>确认信息，看看下一步</button><button className="button-secondary secondary" disabled={busy} onClick={() => { setIntent(null); composerRef.current?.focus() }}>重新描述</button></div></section>}
      {!intent && task?.state === 'awaiting_confirmation' && <section className="meal-flow-card" aria-label="选择一个行动"><p className="eyebrow">第二步 · 由你选择</p><h2>这一餐，先做一件小事</h2><p>这里给你的不是标准答案，而是几条可以比较的路：有的更省力，有的更接近你的目标，有的只是先把今天照顾好。选择后只记录你的打算，之后再反馈是否做到。</p><button className="button-quiet quiet-button" disabled={busy} onClick={() => {
        setMeal(String(task.context?.meal ?? '')); setOptions(Array.isArray(task.context?.options) ? task.context.options.join('、') : ''); setIntent({}); setError('')
        requestAnimationFrame(() => { contextRef.current?.scrollIntoView({block:'center'}); contextRef.current?.querySelector('input')?.focus({preventScroll:true}) })
      }}>修改餐次与选项</button><div className="action-options">{task.candidates?.map((candidate, index) => <article key={candidate.action_id}><p className="candidate-label">路径 {index + 1} · {candidate.dimension ?? '轻行动'}</p><h3>{candidate.behavior}</h3><p>{candidate.cue}</p><details className="candidate-details"><summary>为什么是这条路？</summary><div><p>{candidate.rationale}</p><p className="candidate-effort">执行负担：{candidate.effort}</p></div></details><button className="button-primary" disabled={busy} onClick={() => advance(() => api.confirm(task.task_id, index))}>选择这条路</button></article>)}</div></section>}
      {task?.state === 'adopted' && <section className="meal-flow-card"><p className="eyebrow">第三步 · 等你回来</p><h2>这一步已经记下了</h2><p>反馈没有正确答案。先选一个最接近的状态，也可以留下一句当时发生了什么；这会帮助下一次建议更贴近你的生活。</p>{selectedAction && <blockquote className="selected-action"><strong>{selectedAction.behavior}</strong><p>{selectedAction.cue}</p></blockquote>}{reminderDue&&<div className="reminder-row"><span><strong>想晚一点再回来？</strong><small>把这条行动放回稍后的节奏，不会打扰你。</small></span><button className="button-quiet quiet-button" disabled={busy} onClick={() => advance(async () => { const next = await api.remind(task.task_id, `ui-${Date.now()}`); setReminderDue(false); return next })}>稍后提醒我</button></div>}<label className="feedback-note-label">想补充一句吗？<textarea className="feedback-note" value={feedbackNote} onChange={e=>setFeedbackNote(e.target.value)} maxLength={1000} placeholder="例如：临时加班，回家太晚；或者：这次做起来比想象中容易。" /></label><div className="feedback-choices">{[['complete','做到了','这条路和今天的状态匹配'],['partial','做到一部分','有尝试，剩下的部分也值得被看见'],['not_done','这次没做到','记录阻碍，下一次可以换一条路'],['unknown','暂不确定','先保留未知，不急着下结论']].map(([value,label,hint]) => <button className={`feedback-choice feedback-${value}`} key={value} disabled={busy} onClick={() => advance(() => api.feedback(task.task_id, value, feedbackNote.trim()))}><strong>{label}</strong><small>{hint}</small></button>)}</div></section>}
      {(task?.state === 'feedback' || task?.state === 'review' || task?.state === 'done') && <section className="meal-flow-card"><p className="eyebrow">这一餐 · 已收好</p><h2>谢谢你回来告诉我</h2><p>反馈已保存。不确定的部分会保留为未知。</p>{taskEvents.length>0&&<details className="activity-trace"><summary>这条记录是怎么形成的</summary><ol>{taskEvents.filter(event=>!event.event_type.startsWith('model.')).map((event,index)=><li key={`${event.timestamp}-${index}`}><span>{eventLabel(event.event_type)}</span><time dateTime={event.timestamp}>{formatEventTime(event.timestamp)}</time></li>)}</ol><p>每一步都由你的确认推进；系统不会把未确认的建议写成事实。</p></details>}{correctionOpen&&<div className="feedback-correction" role="region" aria-label="修改反馈"><p className="field-help">修改只会更新这条行动的最新状态，不会创建新的行动。</p><div className="feedback-choices">{[['complete','改为做到了'],['partial','改为做到一部分'],['not_done','改为这次没做到'],['unknown','改为暂不确定']].map(([value,label])=><button className={`feedback-choice feedback-${value}`} key={value} disabled={busy} onClick={() => advance(() => api.correctFeedback(task.task_id, value, feedbackNote.trim(), `ui-${Date.now()}`, task.version))}><strong>{label}</strong></button>)}</div></div>}<div className="button-row"><button className="button-secondary secondary" onClick={()=>setCorrectionOpen(value=>!value)}>{correctionOpen?'收起修改':'修改刚才的反馈'}</button><button onClick={() => { setTask(null); setIntent(null); setMessages([]); setNotice('可以开始描述新的一餐。') }}>开始新的一餐</button><button className="button-secondary secondary" onClick={onRecord}>记下实际吃的一餐</button><button className="button-secondary secondary" onClick={onWorkbench}>饮食回顾</button></div></section>}
      {task && ['stopped','cancelled','context','candidates'].includes(task.state) && <section className="meal-flow-card"><h2>{task.state === 'cancelled' ? '这一餐已取消' : task.state === 'stopped' ? '这一餐暂时停在这里' : '这一餐尚未完成整理'}</h2><p>你可以重新描述可选餐食，再开始一次。已有记录会保留。</p><button disabled={busy} onClick={() => {
        const context = task.context
        setMessage(context?.meal && Array.isArray(context.options) ? `${String(context.meal)}可选${context.options.join('、')}` : '')
        setTask(null); setIntent(null); setMessages([]); setError(''); setNotice('重新描述后发送，开始新的一餐。'); composerRef.current?.focus()
      }}>重新描述这一餐</button></section>}
      {switchPending && <section ref={switchRef} className="meal-flow-card meal-switch" role="region" aria-label="切换到新的一餐" tabIndex={-1}><h2>要开始另一餐吗？</h2><p>当前这一餐还{task?.state === 'adopted' ? '没有反馈' : '没有完成确认'}。开始新餐后仍可从设置中的最近餐次找回它。</p><p className="switch-description">{message}</p><div className="button-row"><button disabled={busy} className="button-secondary secondary" onClick={() => { setSwitchPending(false); composerRef.current?.focus() }}>继续当前这一餐</button><button disabled={busy || !message.trim()} onClick={() => void send(true)}>保留当前记录，开始新餐</button></div></section>}
      {notice && <p role="status" className="notice">{notice}</p>}
      {messages.length === 0 && <div className="board-cards">{resumeTask&&<button className="board-card board-card-wide board-action resume-task-card" onClick={async()=>{setBusy(true);setError('');try{setTask(await api.task(resumeTask.task_id));setResumeTask(null);setNotice('已找回上次停下的这一餐，可以继续。')}catch(e){setError(e instanceof Error?e.message:'暂时无法恢复上一餐')}finally{setBusy(false)}}}><span className="card-icon">↺</span><div><small>上次停在这里</small><strong>继续这一餐</strong><p>{String(resumeTask.context?.meal??'未完成的小行动')} · 你的上下文还在。</p></div><span className="card-arrow">↗</span></button>}<button className="board-card board-card-wide board-action" onClick={() => composerRef.current?.focus()}><span className="card-icon">◒</span><div><small>从眼前开始</small><strong>先说说这一餐</strong><p>菜单、外卖、备餐，都可以直接说。</p></div><span className="card-arrow">↗</span></button><button className="board-card board-action" onClick={onRecord}><span className="card-icon">✓</span><div><small>已经吃过了</small><strong>快速记下一餐</strong><p>不用先计划，份量不确定也可以保留。</p></div><span className="card-arrow">↗</span></button><button className="board-card board-action" onClick={onPlan}><span className="card-icon">⌁</span><div><small>如果已经有打算</small><strong>安排下一步</strong><p>把未来放在手边，之后仍可调整。</p></div><span className="card-arrow">↗</span></button><button className="board-card board-action" onClick={onFood}><span className="card-icon">◌</span><div><small>遇到不确定</small><strong>查一点资料</strong><p>先看来源，再决定要不要。</p></div><span className="card-arrow">↗</span></button><button className="board-card board-action" onClick={onInventory}><span className="card-icon">□</span><div><small>就在厨房里</small><strong>看看手边</strong><p>知道已有的，选择会轻一点。</p></div><span className="card-arrow">↗</span></button><div className="board-card board-card-note"><span>“</span><p>不需要一次把生活整理好，先告诉我眼前这一餐。</p></div></div>}
      {messages.length === 0 && <div className="quick-prompts">{quick.map(item => <button key={item} onClick={() => setMessage(item)}>{item}<span>↗</span></button>)}</div>}
      {ready && !intent && (!task || task.state === 'created') && <div className="manual-entry"><span>也可以直接填写餐次与选项</span><button className="button-quiet quiet-button" disabled={busy} onClick={() => void startManual()}>手动填写这一餐</button></div>}
      <div className="chat-composer"><textarea ref={composerRef} value={message} onChange={event => setMessage(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send() } }} aria-label="描述这一餐" placeholder="告诉我你现在面对什么…" rows={1} /><div className="composer-bar"><span>Enter 发送 · Shift + Enter 换行</span><button className="button-primary" aria-label="发送消息" onClick={() => void send()} disabled={!message.trim() || busy}>{busy ? '…' : '↑'}</button></div></div>
      {error && <div className="error-state"><p className="error" role="alert">{error}</p>{task && <button disabled={busy} onClick={() => setReadAttempt(value => value + 1)}>核对服务器进度</button>}{!ready && <button onClick={onSetup}>设置饮食档案</button>}</div>}
    </div>
    <aside className="chat-side"><div className="side-card"><p className="eyebrow">今天的空间</p><strong>一餐，一步</strong><p>DietLens 不要求你完成完整记录，只从你愿意说的地方开始。</p></div>{profileContext&&<div className="goal-context-card"><p className="eyebrow">你正在照顾的方向</p><strong>{profileContext.goal || '先把今天照顾好'}</strong>{profileContext.budget != null&&<p>参考预算 <b>{profileContext.budget} 元 / 餐</b></p>}{(profileContext.allergies?.length || profileContext.hard_avoids?.length)&&<p className="boundary-line">边界已记住：{[...(profileContext.allergies ?? []), ...(profileContext.hard_avoids ?? [])].slice(0,3).join('、')}{((profileContext.allergies?.length ?? 0)+(profileContext.hard_avoids?.length ?? 0))>3?' 等':''}</p>}<p className="goal-context-note">今天的选择会服务于这个方向，但不需要一次完成全部。</p></div>}{todayPlanItems.length>0&&<div className="today-plan-card"><div><p className="eyebrow">今天已经安排</p><strong>{todayPlanItems.length} 个餐次</strong></div><ul>{todayPlanItems.slice(0,3).map((item,index)=><li key={`${item.plan_id}-${item.item_id||index}`}><span>{String(item.meal_slot)==='breakfast'?'早餐':String(item.meal_slot)==='lunch'?'午餐':String(item.meal_slot)==='dinner'?'晚餐':String(item.meal_slot)}</span><b>{String(item.name)}</b></li>)}</ul>{todayPlanItems.length>3&&<small>还有 {todayPlanItems.length-3} 个安排</small>}<button onClick={onPlan}>查看或调整安排 <span>↗</span></button></div>}<button className="side-link" onClick={onWorkbench}>打开本周回顾 <span>↗</span></button></aside>
  </div>
}

function formatRatio(value: any) { return value?.value == null ? '未知' : `${Math.round(value.value * 100)}%` }
function Metric({ title, value }: { title: string; value: string | number }) { return <div className="metric"><span>{title}</span><strong>{value}</strong></div> }
function ModelReviewCard({ intent, onPrimary, onSecondary, busy }: { intent: Intent; onPrimary: () => void; onSecondary: () => void; busy: boolean }) {
  const meal = intent.entities?.meal ?? ''
  const options = intent.entities?.options ?? []
  const complete = Boolean(meal && options.length)
  return <div className="review-card model-review-card"><p className="eyebrow">模型整理 · 只供你核对</p><h2>我听到的是</h2><div className="intent-summary"><div><span>餐次</span><strong>{meal || '还没听清'}</strong></div><div><span>可选</span><strong>{options.length ? options.join(' / ') : '还没听清'}</strong></div></div><p>{intent.user_message || '请核对餐次和可选餐食。'}</p>{!complete && <div className="notice">还缺少餐次或可选餐食，请返回补充。</div>}<div className="button-row"><button onClick={onPrimary} disabled={busy || !complete}>信息正确，继续</button><button className="button-secondary secondary" onClick={onSecondary} disabled={busy}>重新描述</button></div></div>
}
function ReviewCard({ title, text, primary, secondary, onPrimary, onSecondary, busy }: {title:string;text:string;primary:string;secondary:string;onPrimary:()=>void;onSecondary:()=>void;busy:boolean}) { return <div className="review-card"><p className="eyebrow">需要你确认</p><h2>{title}</h2><p>{text}</p><div className="button-row"><button className="button-primary" onClick={onPrimary} disabled={busy}>{primary}</button><button className="button-secondary secondary" onClick={onSecondary} disabled={busy}>{secondary}</button></div></div> }
