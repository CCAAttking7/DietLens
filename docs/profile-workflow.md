# 档案确认与授权

## 交互入口

```bash
.venv/bin/python cli.py --profile
.venv/bin/python cli.py --model
.venv/bin/python cli.py --resume TASK_ID
```

新用户输入目标、每餐预算、过敏、绝对忌口和软偏好。可选字段可以跳过，过敏留空是未知，输入“无”才表示用户明确确认没有已知过敏。已有用户直接复用档案，不重复询问预算；选择编辑时留空保留原值。预算只接受非负有限数值。

授权分为历史偏好分析、图片外传、历史回顾和提醒，彼此独立；未选择的授权有效值为关闭。预览展示变更前后差异，输入 y 才保存；取消不会改变已有档案或授权。可以不上传图片、不开启可选授权完成初始化。

本阶段交付 Python/CLI 工作流。Web 档案入口与真实账号认证尚未实现。

## Python 接口

```python
from dietlens_mvp import DietLensAgent, Harness, SQLiteStore

agent = DietLensAgent(Harness(SQLiteStore("dietlens.db")))
draft = agent.preview_profile(
    "demo-user",
    {"goal": "减少含糖饮料", "budget": 30, "allergies": [], "hard_avoids": ["猪肉"]},
    expected_version=0,
    consents={"review_history": True, "image_transfer": False},
)
# UI 展示 draft.changes；用户确认后调用：
profile = agent.confirm_profile(
    "demo-user", draft.task_id,
    operation_key="profile-submit-1", expected_version=0,
)
```

`expected_version=0` 表示当前没有档案。编辑传入当前版本，仅提交需要修改的字段。`cancel_profile(user_id, task_id)` 取消待确认草稿；同一次取消可安全重试。重启后可根据 task_id 恢复草稿。

`onboard` 保留为受信任程序调用的显式确认快捷入口，内部也经过 Harness 预览、确认工具和事务。交互界面使用分开的 preview/confirm。`onboard(allergies=None)` 不再代表确认没有过敏；测试或演示需要明确传 `allergies=[]`。历史回顾也需显式传入 `consents={"review_history": True}`。

## 数据与状态

- `profiles`：当前已确认档案。
- `profile_versions`：不可覆盖的历史版本、task_id、operation_key、UTC 时间和完整字段来源。
- `profile_drafts`：尚未应用的任务草稿，原档案保持不变；取消后的草稿也不进入正式档案。
- `consents`：按用户、范围和档案版本记录明确授权/撤回。

草稿任务从 created 进入 awaiting_confirmation，确认后 done，取消后 cancelled；所有迁移产生事件。档案、版本、授权、任务、事件和幂等回执统一提交；中断时整体回滚。同一操作键更换草稿或参数会被拒绝；两个基于同一版本的草稿不能互相覆盖。相同值确认不增加已有档案版本。

`confirmed_fields` 区分明确确认与未知，`field_sources` 标记已确认值的来源。过敏信息另有持久化的 `allergy_status`：`unknown`（暂未说明）、`none`（明确没有已知过敏）和 `specified`（已记录过敏项）。旧数据库迁移不凭空声明用户已确认；旧过敏信息需重新核对，旧的空列表仍为未知。过敏未知时停止餐食候选生成。绝对忌口参与硬过滤，软偏好只影响排序，不作为硬约束排除。

档案更新后旧候选不能直接采纳，CLI 恢复时会按最新档案重新生成候选，需再次选择。已采纳行动的原情境快照和执行反馈保持独立，不改写历史。

撤回 `review_history` 后，回顾入口在读取记录或缓存回执前检查当前授权；不会返回旧缓存回顾。其他权限已有独立状态，偏好分析、图片工具和提醒执行器在后续业务阶段接入，当前没有这些外部副作用。

任务草稿当前为持久化恢复数据，自动保留期限、导出及删除将在隐私管理阶段补齐。食品配料未知的安全过滤、预算价格校验属于阶段 2，当前餐名过滤仍不能证明配料安全。
