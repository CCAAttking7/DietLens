from __future__ import annotations

import math
from .agent import DietLensAgent
from .cleaning import clean_terms
from .models import ProfileDraft
from .profile_workflow import CONSENT_SCOPES

LABELS = {"goal": "目标", "budget": "每餐预算", "allergies": "过敏", "hard_avoids": "绝对忌口", "dislikes": "软偏好/不喜欢",
          "history": "历史偏好分析", "image_transfer": "图片外传", "review_history": "历史回顾", "reminders": "提醒"}


def confirm_draft(agent: DietLensAgent, draft: ProfileDraft, input_fn=input, output_fn=print) -> bool:
    output_fn(f"档案变更预览（当前 v{draft.expected_version}；任务 {draft.task_id}）：")
    for name, delta in draft.changes.items():
        label = LABELS.get(name.removeprefix("consents."), name)
        output_fn(f"  {label}：{delta['before']} → {delta['after']}")
    if not draft.changes:
        output_fn("没有字段变化，不会增加已有档案版本。" if draft.expected_version else "未填写字段，将创建空档案 v1。")
    if input_fn("确认保存？y 保存，其他输入取消：").strip().lower() != "y":
        agent.cancel_profile(draft.user_id, draft.task_id)
        output_fn("已取消，原档案与授权保持不变。")
        return False
    profile = agent.confirm_profile(draft.user_id, draft.task_id, operation_key=draft.task_id, expected_version=draft.expected_version)
    output_fn(f"已保存档案 v{profile.version}。未填写字段保持未知。")
    return True


def initialize_user(agent: DietLensAgent, input_fn=input, output_fn=print, *, force_edit=False) -> str | None:
    user_id = input_fn("用户 ID（直接回车使用 cli-user）：").strip() or "cli-user"
    current = agent.harness.store.get_profile(user_id)
    if current:
        output_fn(f"已有档案 v{current.version}：目标={current.goal}，每餐预算={current.budget}；约束与授权可复用。")
        if not force_edit:
            choice = input_fn("回车复用，e 修改档案/授权，c 退出：").strip().lower()
            if choice != "e":
                return None if choice == "c" else user_id
    output_fn("留空保留已有值；新用户留空为未知。输入 ! 清除可选字段，过敏/忌口输入 无 确认没有。")
    changes = {}
    goal = input_fn("这段时间最想改善什么？（可跳过）：").strip()
    if goal:
        changes["goal"] = None if goal == "!" else goal
    while True:
        raw = input_fn("每餐预算（元，可跳过）：").strip()
        try:
            if raw:
                value = None if raw == "!" else float(raw)
                if value is not None and (not math.isfinite(value) or value < 0):
                    raise ValueError
                changes["budget"] = value
            break
        except ValueError:
            output_fn("请输入非负有限金额，或留空。")
    for field, label in (("allergies", "过敏"), ("hard_avoids", "绝对忌口"), ("dislikes", "软偏好/不喜欢")):
        raw = input_fn(f"{label}（逗号分隔；无=明确没有；留空保留/未知）：").strip()
        if raw:
            if field == "allergies":
                changes["allergy_status"] = "none" if raw == "无" else "specified"
                if raw != "无":
                    changes[field] = clean_terms(raw.replace("，", ",").split(","))
            else:
                changes[field] = [] if raw == "无" or (raw == "!" and field == "dislikes") else clean_terms(raw.replace("，", ",").split(","))
    consents = {}
    output_fn("分项授权均可拒绝，留空保留当前设置，新用户默认关闭。")
    for scope in CONSENT_SCOPES:
        while True:
            raw = input_fn(f"允许{LABELS[scope]}？y 允许 / n 拒绝 / 回车保留：").strip().lower()
            if raw in {"", "y", "n"}:
                if raw:
                    consents[scope] = raw == "y"
                break
            output_fn("请输入 y、n 或回车。")
    draft = agent.preview_profile(user_id, changes, expected_version=current.version if current else 0, consents=consents)
    saved = confirm_draft(agent, draft, input_fn, output_fn)
    return user_id if saved or current else None
