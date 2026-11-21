import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { useSessionDraft } from '../lib/useSessionDraft'

type Item = { inventory_id: string; ingredient_id: string; name: string; quantity: number; unit: string; version:number }
const emptyForm = { inventory_id: '', ingredient_id: '', name: '', quantity: '', unit: 'g', version:1 }
const units = ['g', 'kg', 'ml', 'l', '个', '份', '件', '包', '瓶']

export function InventoryScreen({ userId }: { userId: string }) {
  const [items, setItems] = useState<Item[]>([])
  const [form, setForm] = useSessionDraft(`${userId}:inventory-input`, emptyForm)
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [conflict,setConflict] = useState(false)
  const [latest,setLatest] = useState<Item|null>(null)
  const [checking,setChecking] = useState(false)
  const quantityRef = useRef<HTMLInputElement>(null)
  const formRef = useRef<HTMLFormElement>(null)
  useEffect(() => {
    let active = true
    setLoading(true); setLoadError('')
    api.inventory(userId).then(result => { if (active) setItems(result as Item[]) })
      .catch(e => { if (active) setLoadError(e instanceof Error ? e.message : '库存暂时不可用') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [userId, attempt])
  function edit(item: Item) {
    setForm({ ...item, quantity: String(item.quantity) }); setError(''); setSaved(false)
    setConflict(false);setLatest(null)
    formRef.current?.scrollIntoView({ block: 'nearest' }); quantityRef.current?.focus()
  }
  async function save() {
    if (saving || loading || loadError || conflict) return
    setError(''); setSaved(false)
    const name = form.name.trim(), quantity = Number(form.quantity)
    if (!name) { setError('请填写食材名称'); return }
    if (!form.quantity.trim() || !Number.isFinite(quantity) || quantity < 0) { setError('数量必须是大于或等于 0 的数字'); quantityRef.current?.focus(); return }
    if (items.some(item => item.inventory_id !== form.inventory_id && item.name.trim() === name && item.unit === form.unit)) { setError('清单里已有这项食材，请点击它的“调整”按钮修改余量。'); return }
    setSaving(true)
    try {
      const item = await api.inventoryUpsert({ inventory_id: form.inventory_id || `web-${userId}-${encodeURIComponent(name)}-${form.unit}`, user_id: userId, ingredient_id: form.ingredient_id || name, name, quantity, unit: form.unit, version:form.version??1 }) as Item
      setItems(current => [...current.filter(existing => existing.inventory_id !== item.inventory_id), item])
      setForm(emptyForm); setSaved(true)
    } catch (e) {
      if(e instanceof ApiError && e.code==='version_conflict') {setConflict(true);setError('这项食材已在别处更新。请先读取最新余量，再决定保留哪一个数量。')}
      else setError(e instanceof Error ? e.message : '库存保存失败')
    } finally { setSaving(false) }
  }
  async function checkLatest() {
    if(checking)return
    setChecking(true);setLatest(null)
    try {
      const result=await api.inventory(userId) as Item[];setItems(result)
      const item=result.find(item=>item.inventory_id===form.inventory_id)
      if(!item)throw new Error('这条记录已被移除，请取消调整后重新添加。')
      setLatest(item)
    }catch(e){setError(e instanceof Error?e.message:'无法读取最新余量，请重试')}finally{setChecking(false)}
  }
  return <div className="workspace inventory-workspace"><section className="workspace-main">
    <p className="eyebrow">此刻手边 · 留一点余地</p><h1>先看看手边有什么，<br/><em>下一步会轻一点。</em></h1>
    <p className="lede">记下现有食材，之后可以随时调整余量。用完了填 0，计划不会自动扣减库存。</p>
    <form ref={formRef} className="inventory-form" onSubmit={e => { e.preventDefault(); void save() }}>
      {form.inventory_id && <p className="inventory-edit-note">正在调整：{items.find(item => item.inventory_id === form.inventory_id)?.name ?? form.name}</p>}
      <label className="inventory-name">食材名称<input disabled={saving || Boolean(form.inventory_id)} aria-label="食材名称" value={form.name} onChange={e => { setSaved(false); setForm({ ...form, name: e.target.value }) }} placeholder="例如：燕麦、鸡蛋" /></label>
      <label>数量<input ref={quantityRef} disabled={saving} aria-label="库存数量" inputMode="decimal" value={form.quantity} onChange={e => { setSaved(false); setForm({ ...form, quantity: e.target.value }) }} placeholder="例如：500" /></label>
      <label>单位<select disabled={saving || Boolean(form.inventory_id)} aria-label="库存单位" value={form.unit} onChange={e => { setSaved(false); setForm({ ...form, unit: e.target.value }) }}>{[...new Set([...units, form.unit])].map(unit => <option key={unit}>{unit}</option>)}</select></label>
      <button className="button-primary" type="submit" disabled={saving || loading || conflict || checking || Boolean(loadError) || !form.quantity.trim() || !form.name.trim()}>{saving ? '正在保存…' : form.inventory_id ? '保存调整' : '保存到手边'}</button>
      {form.inventory_id && <button className="button-secondary secondary" type="button" disabled={saving || checking} onClick={() => { setForm(emptyForm); setError(''); setSaved(false);setConflict(false);setLatest(null) }}>取消调整</button>}
    </form>
    {error && <p className="error" role="alert">{error}</p>}{saved && <p className="notice" role="status">已保存到手边清单。</p>}
    {conflict&&<section className="review-card" aria-label="库存版本核对">{latest?<><h2>核对这次调整</h2><p>最新记录：{latest.name} · {latest.quantity}{latest.unit}</p><p>你的填写：{form.quantity}{form.unit}</p><div className="button-row"><button disabled={checking} onClick={()=>edit(latest)}>改用最新余量</button><button className="button-secondary secondary" disabled={checking} onClick={()=>{setForm({...latest,quantity:form.quantity});setConflict(false);setLatest(null);setError('')}}>保留我的数量</button></div><p className="field-help">保留填写后，还需要点击“保存调整”才会写入。</p></>:<button disabled={checking} onClick={checkLatest}>{checking?'正在读取最新余量…':'读取最新余量'}</button>}</section>}
    {loading && <p className="busy-note" role="status">正在读取手边食材…</p>}
    {loadError && <div className="error-state"><p className="error" role="alert">{loadError}</p><button onClick={() => setAttempt(value => value + 1)}>重新读取清单</button></div>}
    {!loading && !loadError && <div className="inventory-list">{items.length ? <><p className="result-summary">{items.length} 项食材 · {items.filter(item => item.quantity > 0).length} 项还有余量</p>{items.map(item => <div className="inventory-item" key={item.inventory_id}><div><strong>{item.name}</strong><p>{item.quantity}{item.unit}{item.quantity === 0 ? ' · 已用完' : ''}</p></div><button type="button" aria-label={`调整${item.name}`} disabled={saving} onClick={() => edit(item)}>调整</button></div>)}</> : <div className="empty-state"><h2>从手边的一样食材开始</h2><p>记下名称和余量，之后生成采购清单时就能核对。没有记录的食材会保持未知。</p></div>}</div>}
  </section><aside className="status-card"><p className="eyebrow">手边的食材</p><h2>有多少，你说了算</h2><p>点“调整”更新余量。同名但单位不同的记录会分开保留；不会自动换算或扣减。</p></aside></div>
}
