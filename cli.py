from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dietlens_mvp import DietLensAgent, Harness, SQLiteStore
from dietlens_mvp.cold_start import initialize_user, confirm_draft
from dietlens_mvp.models import Execution, Task, TaskState
from dietlens_mvp.config import Settings
from dietlens_mvp.errors import ToolError
from dietlens_mvp.sources import ChinaCDCFoodCompositionSource, FoodSourceRegistry
from dietlens_mvp.food import persist_search_result, search_result, summarize_record


def main() -> None:
    parser = argparse.ArgumentParser(description="DietLens CLI MVP")
    env_parser = argparse.ArgumentParser(add_help=False)
    env_parser.add_argument("--env-file", default=str(Path(__file__).with_name(".env")))
    env_args, _ = env_parser.parse_known_args()
    settings = Settings.from_env(env_args.env_file)
    parser.add_argument("--env-file", default=env_args.env_file, help="模型与运行配置文件")
    parser.add_argument("--model", action="store_true", help="使用真实模型解析餐事情境")
    parser.add_argument("--db", default=settings.database_path)
    parser.add_argument("--resume", metavar="TASK_ID", help="从已保存的任务继续")
    parser.add_argument("--refresh-china", action="store_true")
    parser.add_argument("--profile", action="store_true", help="仅编辑档案与分项授权")
    args = parser.parse_args()
    logging.basicConfig(level=settings.log_level, format="%(message)s")
    try:
        provider = settings.create_provider() if args.model else None
    except ToolError as exc:
        parser.error(f"模型配置不可用：{exc.code}；请检查 --env-file")
    store = SQLiteStore(args.db)
    agent = DietLensAgent(Harness(store, provider=provider))
    try:
        if args.resume:
            task = store.get_task(args.resume)
            if task is None:
                raise ToolError("task_not_found")
            if task.task_type == "profile_update":
                if task.state == TaskState.AWAITING_CONFIRMATION:
                    draft = store.get_profile_draft(task.task_id)
                    confirm_draft(agent, draft)
                else:
                    print(f"档案任务状态：{task.state.value}")
                return
            current_profile = store.get_profile(task.user_id)
            if task.state == TaskState.AWAITING_CONFIRMATION and task.context and current_profile and task.context.profile_version != current_profile.version:
                print("档案已更新，将使用最新约束重新生成候选并核对。")
                task = agent.harness.context(task.task_id, task.context.meal, task.context.options)
            if task.state == TaskState.CREATED:
                task = collect_model_context(agent, task) if args.model else collect_manual_context(agent, task)
            continue_task(agent, task)
            return
        if args.refresh_china:
            count = ChinaCDCFoodCompositionSource().refresh()
            print(f"中国疾控官方食物编码数据已下载：{count} 行")
        user_id = initialize_user(agent, force_edit=args.profile)
        if user_id is None or args.profile:
            return
        if args.model:
            task = agent.harness.create_task(user_id)
            task = collect_model_context(agent, task)
            continue_task(agent, task)
            return
        registry = FoodSourceRegistry()
        query = input("先输入要查询的食品/菜品关键词（可跳过）：").strip()
        source_options = []
        if query:
            profile = store.get_profile(user_id)
            constraints_confirmed = bool(profile and "allergies" in profile.confirmed_fields)
            constraints = (profile.allergies + profile.hard_avoids) if profile and constraints_confirmed else []
            result = search_result(registry, query, constraints, budget=profile.budget if profile else None,
                                   constraints_confirmed=constraints_confirmed)
            persist_search_result(store, user_id, result)
            for assessment in result["assessments"]:
                record = assessment.record
                print(f"[{assessment.status}] [{record.source}] {record.name} | source_id={record.source_id} | unknown={assessment.unknown_fields} | nutrients={record.nutrients}")
                if assessment.status == "blocked":
                    print(f"  已停止：{assessment.reasons}")
            source_options = list(dict.fromkeys(a.record.name for a in result["assessments"] if a.status == "safe" and a.record.name))
            if result["conflicts"]:
                print(f"来源字段存在冲突，请核对后再使用：{[(c.field, c.values) for c in result['conflicts']]}")
            if result["failures"]:
                print(f"部分来源暂不可用：{result['failures']}")
            if not constraints_confirmed:
                print("过敏/硬约束尚未明确确认，来源候选不会自动进入安全推荐；请手动核对标签。")
        if source_options:
            meal = input("餐次（例如：午餐）：").strip()
            raw_options = ",".join(source_options)
            print(f"将使用已检索候选：{raw_options}")
        else:
            print("输入一次餐事情境，格式：餐次|选项1,选项2")
            meal, raw_options = input("> ").strip().split("|", 1)
        task = agent.begin(user_id, meal, [x.strip() for x in raw_options.split(",")])
        continue_task(agent, task)
    except (ToolError, ValueError) as exc:
        print(f"操作未完成：{exc}")
        raise SystemExit(1)
    finally:
        store.close()


def collect_manual_context(agent: DietLensAgent, task: Task, input_fn=input) -> Task:
    meal = input_fn("餐次：").strip()
    options = input_fn("可选餐食（逗号分隔）：").replace("，", ",").split(",")
    from dietlens_mvp.cleaning import clean_options
    if not meal or not clean_options(options):
        raise ToolError("context_required")
    return agent.harness.context(task.task_id, meal, clean_options(options))


def collect_model_context(agent: DietLensAgent, task: Task, input_fn=input, output_fn=print) -> Task:
    from jsonschema import ValidationError, validate
    from dietlens_mvp.cleaning import clean_options
    output_fn(f"任务 ID：{task.task_id}。仅发送本次情境文字给已配置的模型服务。")
    messages = [{"role": "user", "content": input_fn("描述餐次和当前可选餐食：").strip()}]
    try:
        intent = agent.harness.interpret(task.task_id, messages)
    except ToolError as exc:
        if exc.code != "model_budget_exhausted":
            raise
        output_fn("模型调用额度已用完，请手动继续。")
        return collect_manual_context(agent, task, input_fn)
    event = agent.harness.store.list_events(task.task_id)[-1]
    if event.payload.get("outcome") == "manual_fallback":
        output_fn(f"模型未成功完成解析（{event.payload.get('error_code')}），请手动继续。")
        return collect_manual_context(agent, task, input_fn)
    output_fn(intent["user_message"])
    if intent["intent"] not in {"micro_action", "menu_recommendation"}:
        output_fn("当前入口支持饮食微行动，请手动提供餐事情境。")
        return collect_manual_context(agent, task, input_fn)
    try:
        validate(intent["entities"], {"type": "object", "required": ["meal", "options"], "properties": {
            "meal": {"type": "string", "minLength": 1},
            "options": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}}})
        meal = intent["entities"]["meal"].strip()
        options = clean_options(intent["entities"]["options"])
        if set(intent["missing_fields"]) & {"meal", "options", "entities.meal", "entities.options"} or not meal or not options:
            raise ValueError("context_required")
    except (ValidationError, ValueError):
        output_fn("关键情境字段仍需补充，请手动继续。")
        return collect_manual_context(agent, task, input_fn)
    output_fn(f"请核对：餐次={meal}；选项={options}")
    if input_fn("确认使用以上情境？y 确认，其他输入改为手动填写：").strip().lower() != "y":
        return collect_manual_context(agent, task, input_fn)
    return agent.harness.context(task.task_id, meal, options)


def continue_task(agent: DietLensAgent, task: Task, input_fn=input, output_fn=print) -> None:
    output_fn(f"任务 ID：{task.task_id}；状态：{task.state.value}")
    if task.state == TaskState.STOPPED:
        output_fn(f"任务停止：{task.stopped_reason}")
        return
    if task.state == TaskState.AWAITING_CONFIRMATION:
        for index, action in enumerate(task.candidates):
            output_fn(f"[{index}] {action.behavior}；依据：{action.rationale}")
        choice = input_fn("采纳哪个候选？输入序号，或输入 s 跳过：").strip()
        if choice.lower() == "s":
            agent.skip(task.task_id)
            output_fn("已记录跳过，不计为执行失败。")
            return
        task = agent.adopt(task.task_id, int(choice))
    if task.state == TaskState.ADOPTED:
        status = input_fn("执行反馈 complete/partial/not_done/unknown（回车暂不反馈）：").strip()
        if not status:
            output_fn(f"待反馈，可通过 --resume {task.task_id} 继续。")
            return
        task = agent.report(task.task_id, Execution(status))
    if task.state in {TaskState.FEEDBACK, TaskState.DONE}:
        profile = agent.harness.store.get_profile(task.user_id)
        if profile and profile.consents.get("review_history", False):
            output_fn(agent.review(task.task_id))
        else:
            output_fn("执行状态已保存。历史回顾授权未开启，可通过 --profile 管理。")


if __name__ == "__main__":
    main()
