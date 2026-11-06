export type TaskState = 'created' | 'context' | 'candidates' | 'awaiting_confirmation' | 'adopted' | 'feedback' | 'review' | 'done' | 'stopped' | 'cancelled'
export type Candidate = { action_id: string; behavior: string; cue: string; effort: string; rationale: string; dimension?: string }
export type ProfileDraft = { task_id: string; user_id: string; expected_version: number; proposed: Record<string, unknown>; changes: Record<string, unknown> }
export type Task = { task_id: string; task_type?: 'micro_action'|'quick_log'|'plan'|'explore'|'reflect'|string; state: TaskState; care_state?: string; version: number; context?: Record<string, unknown>; pending_record?: Record<string, unknown> | null; candidates?: Candidate[]; selected_action_id?: string; linked_objects?: Record<string, unknown>; updated_at?: string }
export type TaskEvent = { event_type: string; task_id: string; user_id: string; payload?: Record<string, unknown>; timestamp: string }
export type MealRecord = { record_id: string; user_id: string; meal_date: string; meal_slot: string; name: string; quantity: number | null; unit: string | null; source: string; status: string; version: number; plan_id?: string | null; plan_item_id?: string | null }
export type Plan = { plan_id: string; user_id: string; start_date: string; days: number; servings: number; version: number; status: string; items: Array<Record<string, any>> }
export type ShoppingList = { list_id: string; status: string; items: Array<Record<string, any>> }
export type ShoppingItem = {item_id:string;name:string;quantity:number;unit:string;needed:number}

const base = (import.meta.env.VITE_DIETLENS_API_URL as string | undefined) ?? ''
let accessToken: string | null = null
export function setAccessToken(token: string | null) { accessToken = token }
export class ApiError extends Error {
  constructor(public readonly code: string, message: string) { super(message) }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {'Content-Type': 'application/json'}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  let response: Response
  try {
    response = await fetch(`${base}${path}`, {...init, headers: {...headers, ...(init?.headers ?? {})}, signal: AbortSignal.timeout(20000)})
  } catch {
    throw new Error('暂时无法连接服务，请确认后端已启动，然后重试。填写的内容仍然保留。')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as {detail?: {code?: string}} | null
    const code = body?.detail?.code
    const messages: Record<string,string> = {
      authentication_required: '登录状态已失效，请重新登录。',
      version_conflict: '这份内容已更新，请重新读取后再确认。',
      invalid_inventory_item: '请检查数量和单位，支持 g、kg、ml、l、个、份、包等单位。',
      overlapping_plan_range: '这段日期与已有的多日计划重叠，请选择其他日期，或使用相同日期范围修改整份计划。',
      plan_not_confirmed: '这份计划已更新，请重新打开已保存的计划。',
      inventory_duplicate: '已有相同食材和单位的记录，请调整已有记录。',
      invalid_food_query: '请输入 1 至 120 个字符的食物名称或品牌。',
      quick_log_draft_changed: '这条记录已经被修改，请重新预览后再保存。',
    }
    throw new ApiError(code ?? `http_${response.status}`, code ? (messages[code] ?? code) : response.status >= 500 ? '服务暂时不可用，请稍后重试，填写的内容已保留。' : `请求未完成（${response.status}），请检查输入后重试。`)
  }
  return response.json() as Promise<T>
}
export const api = {
  status: () => request<{auth_mode:'demo'|'supabase'}>('/api/status'),
  profilePreview: (body: {user_id:string; changes:Record<string,unknown>; expected_version:number; consents:Record<string,boolean>}) => request<ProfileDraft>('/api/profile/preview',{method:'POST',body:JSON.stringify(body)}),
  profileConfirm: (body: {user_id:string; task_id:string; operation_key:string; expected_version:number}) => request<Record<string,unknown>>('/api/profile/confirm',{method:'POST',body:JSON.stringify(body)}),
  recentTasks: (userId:string) => request<Task[]>(`/api/tasks?user_id=${encodeURIComponent(userId)}`),
  createTask: (body: {user_id: string; task_type?: 'micro_action'|'quick_log'|'plan'|'explore'|'reflect'}) => request<{task_id:string}>('/api/tasks',{method:'POST',body:JSON.stringify(body)}),
  sendMessage: (taskId:string, content:string) => request<{intent:Record<string,unknown>;task:Task}>(`/api/tasks/${taskId}/messages`,{method:'POST',body:JSON.stringify({content})}),
  confirmContext: (taskId:string, meal:string, options:string[]) => request<Task>(`/api/tasks/${taskId}/context`,{method:'POST',body:JSON.stringify({meal,options})}),
  confirm: (taskId:string, actionIndex:number) => request<Task>(`/api/tasks/${taskId}/confirm`,{method:'POST',body:JSON.stringify({action_index:actionIndex})}),
  feedback: (taskId:string, execution:string, note='') => request<Task>(`/api/tasks/${taskId}/feedback`,{method:'POST',body:JSON.stringify({execution,note})}),
  correctFeedback: (taskId:string, execution:string, note='', operationKey?:string, expectedVersion?:number) => request<Task>(`/api/tasks/${taskId}/feedback/correct`,{method:'POST',body:JSON.stringify({execution,note,operation_key:operationKey,expected_version:expectedVersion})}),
  reminderStatus: (taskId:string) => request<{eligible:boolean;due:boolean;next_at:string|null;reminder_count:number}>(`/api/tasks/${taskId}/reminder`),
  remind: (taskId:string, operationKey?:string) => request<Task>(`/api/tasks/${taskId}/reminder${operationKey?`?operation_key=${encodeURIComponent(operationKey)}`:''}`,{method:'POST'}),
  review: (taskId:string) => request<Record<string,unknown>>(`/api/tasks/${taskId}/review`),
  workbenchReview: (userId:string, period='week') => request<Record<string,any>>(`/api/reviews?user_id=${encodeURIComponent(userId)}&period=${period}`),
  mealPreview: (body: Record<string,unknown>) => request<MealRecord>('/api/meal-records/preview',{method:'POST',body:JSON.stringify(body)}),
  quickLogPreview: (body: Record<string,unknown>) => request<{task:Task;record:MealRecord}>('/api/quick-log/preview',{method:'POST',body:JSON.stringify(body)}),
  quickLogConfirm: (taskId:string, body:MealRecord, operationKey?:string) => request<{task:Task;record:MealRecord}>(`/api/quick-log/confirm${operationKey?`?operation_key=${encodeURIComponent(operationKey)}`:''}`,{method:'POST',body:JSON.stringify({...body,task_id:taskId})}),
  mealConfirm: (body: MealRecord) => request<MealRecord>('/api/meal-records/confirm',{method:'POST',body:JSON.stringify(body)}),
  mealRecords: (userId:string) => request<MealRecord[]>(`/api/meal-records?user_id=${encodeURIComponent(userId)}&limit=20`),
  mealUpdate: (record:MealRecord, changes:Record<string,unknown>) => request<MealRecord>(`/api/meal-records/${encodeURIComponent(record.record_id)}`,{method:'PATCH',body:JSON.stringify({expected_version:record.version,changes})}),
  mealDelete: (record:MealRecord) => request<MealRecord>(`/api/meal-records/${encodeURIComponent(record.record_id)}?expected_version=${record.version}`,{method:'DELETE'}),
  planPreview: (body: Record<string,unknown>) => request<Plan>('/api/plans/preview',{method:'POST',body:JSON.stringify(body)}),
  plans: (userId:string) => request<Plan[]>(`/api/plans?user_id=${encodeURIComponent(userId)}&limit=30`),
  plan: (planId:string) => request<Plan>(`/api/plans/${encodeURIComponent(planId)}`),
  planConfirm: (planId:string) => request<Plan>(`/api/plans/${planId}/confirm`,{method:'POST'}),
  planCancel: (planId:string) => request<Plan>(`/api/plans/${planId}/cancel`,{method:'POST'}),
  shoppingList: (planId:string) => request<ShoppingList>(`/api/plans/${planId}/shopping-list`,{method:'POST'}),
  shoppingDiff: (listId:string) => request<ShoppingItem[]>(`/api/shopping-lists/${encodeURIComponent(listId)}/inventory-diff`),
  inventory: (userId:string) => request<Array<Record<string,any>>>(`/api/inventory?user_id=${encodeURIComponent(userId)}`),
  inventoryUpsert: (body:Record<string,unknown>) => request<Record<string,any>>('/api/inventory',{method:'POST',body:JSON.stringify(body)}),
  profile: (userId:string) => request<Record<string,any>>(`/api/profile/${encodeURIComponent(userId)}`),
  task: (taskId:string) => request<Task>(`/api/tasks/${encodeURIComponent(taskId)}`),
  taskEvents: (taskId:string) => request<TaskEvent[]>(`/api/tasks/${encodeURIComponent(taskId)}/events`),
  foodSearch: (userId:string, query:string) => request<Record<string,any>>(`/api/foods/search?user_id=${encodeURIComponent(userId)}&q=${encodeURIComponent(query)}`),
  exportData: (userId:string) => request<Record<string,any>>('/api/export',{method:'POST',body:JSON.stringify({user_id:userId})}),
  deleteData: (userId:string) => request<Record<string,any>>('/api/delete',{method:'POST',body:JSON.stringify({user_id:userId, confirmed:true})}),
}
