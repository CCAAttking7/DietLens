import { Component, Suspense, lazy, type ComponentType, type ReactNode } from 'react'

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
    return <ToolBoundary><Suspense fallback={<section className="tool-loading tool-skeleton" role="status" aria-label={`正在加载${title}`}><p className="eyebrow">DietLens · {title}</p><div className="skeleton-line skeleton-title" /><div className="skeleton-line skeleton-copy" /><div className="skeleton-panel" /><p>正在打开{title}…</p></section>}><Tool {...props} /></Suspense></ToolBoundary>
  }
}
