import { Component, Suspense, lazy, type ComponentType, type ReactNode } from 'react'

type SkeletonKind = 'food' | 'inventory' | 'plan' | 'review' | 'settings' | 'default'
const skeletonKind = (title: string): SkeletonKind => title.includes('食品') ? 'food' : title.includes('库存') ? 'inventory' : title.includes('计划') ? 'plan' : title.includes('回顾') ? 'review' : title.includes('设置') ? 'settings' : 'default'
function RouteSkeleton({title}:{title:string}) {
  const kind = skeletonKind(title)
  const rows = kind === 'food' ? 3 : kind === 'inventory' ? 5 : kind === 'plan' ? 4 : kind === 'review' ? 3 : kind === 'settings' ? 4 : 2
  return <section className={`tool-loading tool-skeleton skeleton-${kind}`} role="status" aria-label={`正在加载${title}`} aria-busy="true">
    <p className="eyebrow">DietLens · {title}</p><div className="skeleton-line skeleton-title" /><div className="skeleton-line skeleton-copy" />
    {kind === 'food' && <div className="skeleton-search"><div className="skeleton-line" /><div className="skeleton-button" /></div>}
    {kind === 'plan' && <div className="skeleton-date"><div className="skeleton-line" /><div className="skeleton-line" /></div>}
    {kind === 'review' && <div className="skeleton-metrics">{[1,2,3].map(item => <div className="skeleton-card" key={item} />)}</div>}
    <div className="skeleton-list">{Array.from({length: rows}, (_, index) => <div className="skeleton-card" key={index}><div className="skeleton-line" /><div className="skeleton-line" /><div className="skeleton-line skeleton-short" /></div>)}</div>
    <p>正在打开{title}…</p>
  </section>
}

class ToolBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  state = {failed: false}
  static getDerivedStateFromError() { return {failed: true} }
  render() {
    if (this.state.failed) return <section className="tool-loading" role="alert">
      <h2>这个工具暂时未能打开</h2>
      <p>请检查网络后重新载入，也可以使用上方导航切换工具。已保留的草稿会随页面恢复。</p>
      <button className="primary-action" onClick={() => window.location.reload()}>重新载入页面</button>
    </section>
    return this.props.children
  }
}

/** A failed module stays rejected in the browser cache; reload is the reliable recovery. */
export function loadTool<P extends object>(loader: () => Promise<{default: ComponentType<P>}>, title = '页面') {
  const Tool = lazy(loader)
  return function LoadedTool(props: P) {
    return <ToolBoundary><Suspense fallback={<RouteSkeleton title={title} />}><Tool {...props} /></Suspense></ToolBoundary>
  }
}
