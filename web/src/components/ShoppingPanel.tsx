import { useState } from 'react'
import { api, type ShoppingItem, type ShoppingList } from '../lib/api'

export function ShoppingPanel({planId}:{planId:string}) {
  const [list,setList]=useState<ShoppingList|null>(null)
  const [items,setItems]=useState<ShoppingItem[]|null>(null)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  async function generate() {
    if(busy)return
    setBusy(true);setError('');setItems(null)
    try {
      const next=await api.shoppingList(planId)
      setList(next)
      setItems(await api.shoppingDiff(next.list_id))
    }catch(e){setError(e instanceof Error?e.message:'采购清单暂时不可用')}finally{setBusy(false)}
  }
  return <section className="shopping-panel" aria-label="采购与库存核对">
    <button className="button-secondary secondary" disabled={busy} onClick={generate}>{busy?'正在核对库存…':list?'重新核对库存':'生成采购清单'}</button>
    {error&&<p className="error" role="alert">{error}</p>}
    {items&&<div className="shopping-results"><h3>采购清单</h3><p>已按同名食材、相同单位核对当前库存，不会自动扣减。库存变化后可重新核对。</p>
      <div className="workbench">{items.map(item=><div className="shopping-row" key={item.item_id}><div><strong>{item.name}</strong><p>计划需要 {item.quantity}{item.unit}</p></div><strong>{item.needed>0?`还需 ${item.needed}${item.unit}`:'库存已覆盖'}</strong></div>)}</div>
      {items.length>0&&items.every(item=>item.needed===0)&&<p className="notice">现有库存已覆盖这份计划，暂时无需采购。</p>}
    </div>}
  </section>
}
