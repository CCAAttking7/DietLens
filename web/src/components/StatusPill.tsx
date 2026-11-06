import type { TaskState } from '../lib/api'
const labels: Record<TaskState,string> = {created:'待输入',context:'待整理',candidates:'待整理',awaiting_confirmation:'待确认',adopted:'待反馈',feedback:'已反馈',review:'已反馈',done:'已完成',stopped:'已停止',cancelled:'已取消'}
export function StatusPill({state}:{state:TaskState}) { const label = labels[state] ?? '待查看'; return <span className={`status status-${state}`} aria-label={`状态：${label}`}>{label}</span> }
