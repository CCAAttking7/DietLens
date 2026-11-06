from dietlens_mvp import DietLensAgent
from dietlens_mvp.models import Execution


agent = DietLensAgent()
agent.onboard("u-1", budget=40, allergies=["花生"], goal="减少含糖饮料", consents={"review_history": True})
task = agent.begin("u-1", "午餐", ["鸡肉饭", "花生沙拉"])
print("候选:", [(a.behavior, a.rationale) for a in task.candidates])
agent.adopt(task.task_id)
agent.report(task.task_id, Execution.COMPLETE)
print("回顾:", agent.review(task.task_id))
