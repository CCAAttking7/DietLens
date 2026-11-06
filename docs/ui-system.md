# Web UI 系统

DietLens Web 的外壳采用 [shadcndashboard/shadcndashboard](https://github.com/shadcndashboard/shadcndashboard) 的 MIT 开源 dashboard 范式：固定 rail 导航、单一主工作区、sheet/drawer 承载次级页面、紧凑状态 pill 和轻量过渡动画。我们只借用布局和交互模式，业务文案、状态和数据组件仍来自 DietLens。

- 主场景固定为“今天 / 陪伴一餐”，用户打开后只面对当前这一餐。
- 计划、食品、库存、回顾和设置从左侧 rail 打开右侧 drawer；关闭 drawer 返回主场景，不丢失当前状态。
- 主页面使用短标题、单个下一步和少量状态信息；完整说明只在确认卡或 drawer 中展开。
- 移动端将 rail 收缩为横向导航，drawer 变为全宽 sheet。
- 所有业务确认门、未知字段、来源和授权边界保持原逻辑，不由视觉层计算。
