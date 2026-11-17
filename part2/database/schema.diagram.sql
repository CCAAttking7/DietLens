-- 中文ER展示投影，只用于drawDB导入；不是迁移脚本。

CREATE TABLE "用户处理控制" (
  "所属用户" TEXT NOT NULL,
  "托管身份主体" TEXT,
  "处理状态" TEXT NOT NULL,
  "授权修订标记" BIGINT NOT NULL,
  "用户数据修订" BIGINT NOT NULL,
  "当前档案修订" BIGINT,
  "主动删除请求时间" TIMESTAMPTZ,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户"),
  UNIQUE ("托管身份主体")
);

CREATE TABLE "档案确认版本" (
  "所属用户" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "已确认字段" JSONB NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "修订号")
);

CREATE TABLE "临时图片" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "本机受控文件键" TEXT,
  "材料用途" TEXT NOT NULL,
  "内容摘要" TEXT NOT NULL,
  "图片过期时间" TIMESTAMPTZ NOT NULL,
  "图片处理状态" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "用途授权修订" (
  "所属用户" TEXT NOT NULL,
  "用途" TEXT NOT NULL,
  "范围键" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "外传图片标识" TEXT,
  "允许使用" SMALLINT NOT NULL,
  "接收方" TEXT,
  "授权修订标记" BIGINT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "用途", "范围键", "修订号")
);

CREATE TABLE "临时任务会话" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "任务类型" TEXT NOT NULL,
  "任务状态" TEXT NOT NULL,
  "草稿修订" BIGINT NOT NULL,
  "未确认草稿" JSONB NOT NULL,
  "绑定授权修订" BIGINT NOT NULL,
  "任务过期时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "已确认情境" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "档案修订" BIGINT NOT NULL,
  "情境指纹" TEXT NOT NULL,
  "已确认情境内容" JSONB NOT NULL,
  "当时授权修订" BIGINT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "证据来源" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "来源类型" TEXT NOT NULL,
  "出处或自述说明" TEXT NOT NULL,
  "商品或菜单规格" TEXT,
  "材料时间" TIMESTAMPTZ,
  "取得时间" TIMESTAMPTZ NOT NULL,
  "原图片标识" TEXT,
  "材料摘要" TEXT,
  "核对依据" TEXT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "食品证据版本" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "上一证据版本" TEXT,
  "食品名称" TEXT NOT NULL,
  "当前规格" TEXT,
  "配方覆盖" TEXT NOT NULL,
  "核对时间" TIMESTAMPTZ,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  "营养基准量状态" TEXT NOT NULL,
  "营养基准量定点值" BIGINT,
  "营养基准量单位" TEXT,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "食品逐字段事实" (
  "所属用户" TEXT NOT NULL,
  "食品证据标识" TEXT NOT NULL,
  "字段键" TEXT NOT NULL,
  "字段状态" TEXT NOT NULL,
  "值类型" TEXT NOT NULL,
  "数值定点值" BIGINT,
  "文字值" TEXT,
  "字段单位" TEXT,
  "原始候选值" TEXT,
  "核对时间" TIMESTAMPTZ,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "食品证据标识", "字段键")
);

CREATE TABLE "字段来源关联" (
  "所属用户" TEXT NOT NULL,
  "食品证据标识" TEXT NOT NULL,
  "字段键" TEXT NOT NULL,
  "来源标识" TEXT NOT NULL,
  "来源角色" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "食品证据标识", "字段键", "来源标识")
);

CREATE TABLE "约束评估" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "情境标识" TEXT NOT NULL,
  "食品证据标识" TEXT,
  "规则版本" TEXT NOT NULL,
  "评估结论" TEXT NOT NULL,
  "原因与受影响操作" JSONB NOT NULL,
  "评估时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "标准食材" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "标准名称" TEXT NOT NULL,
  "外部编码" TEXT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "计划身份" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "当前确认修订" BIGINT NOT NULL,
  "并发版本" BIGINT NOT NULL,
  "身份状态" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "计划确认版本" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "计划模式" TEXT NOT NULL,
  "开始日期" DATE NOT NULL,
  "结束日期" DATE NOT NULL,
  "计划天数" BIGINT NOT NULL,
  "情境标识" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识", "修订号")
);

CREATE TABLE "计划餐次" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "计划标识" TEXT NOT NULL,
  "计划修订" BIGINT NOT NULL,
  "餐次日期" DATE NOT NULL,
  "规范餐次" TEXT NOT NULL,
  "准备人数" BIGINT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识"),
  UNIQUE ("所属用户", "计划标识", "计划修订", "餐次日期", "规范餐次"),
  UNIQUE ("所属用户", "对象标识", "餐次日期", "规范餐次")
);

CREATE TABLE "计划食物" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "计划餐次标识" TEXT NOT NULL,
  "食物名称" TEXT NOT NULL,
  "食品证据标识" TEXT,
  "约束评估标识" TEXT,
  "数量基准" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "计划份量状态" TEXT NOT NULL,
  "计划份量定点值" BIGINT,
  "计划份量单位" TEXT,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "食材需求" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "计划食物标识" TEXT NOT NULL,
  "食材标识" TEXT NOT NULL,
  "数量基准" TEXT NOT NULL,
  "配方来源" TEXT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "食材用量状态" TEXT NOT NULL,
  "食材用量定点值" BIGINT,
  "食材用量单位" TEXT,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "当前槽位归属" (
  "所属用户" TEXT NOT NULL,
  "餐次日期" DATE NOT NULL,
  "规范餐次" TEXT NOT NULL,
  "当前计划餐次标识" TEXT NOT NULL,
  "槽位并发版本" BIGINT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "餐次日期", "规范餐次")
);

CREATE TABLE "库存身份" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "标准食材标识" TEXT NOT NULL,
  "核对口径单位" TEXT NOT NULL,
  "当前库存修订" BIGINT NOT NULL,
  "并发版本" BIGINT NOT NULL,
  "身份状态" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识"),
  UNIQUE ("所属用户", "标准食材标识", "核对口径单位")
);

CREATE TABLE "库存核对版本" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "库存量状态" TEXT NOT NULL,
  "库存定点值" BIGINT,
  "库存核对时间" TIMESTAMPTZ NOT NULL,
  "变更原因" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识", "修订号")
);

CREATE TABLE "准备采购清单" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "来源计划标识" TEXT NOT NULL,
  "来源计划修订" BIGINT NOT NULL,
  "并发版本" BIGINT NOT NULL,
  "清单状态" TEXT NOT NULL,
  "库存核对截点" BIGINT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "清单条目" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "清单标识" TEXT NOT NULL,
  "标准食材标识" TEXT NOT NULL,
  "汇总口径单位" TEXT NOT NULL,
  "另有未知需求" SMALLINT NOT NULL,
  "已知需求小计" BIGINT NOT NULL,
  "库存量状态" TEXT NOT NULL,
  "核对库存定点值" BIGINT,
  "差额状态" TEXT NOT NULL,
  "采购差额定点值" BIGINT,
  "采购自述状态" TEXT NOT NULL,
  "准备自述状态" TEXT NOT NULL,
  "所用库存身份" TEXT,
  "所用库存修订" BIGINT,
  "人工调整原因" TEXT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识"),
  UNIQUE ("所属用户", "清单标识", "标准食材标识", "汇总口径单位")
);

CREATE TABLE "清单需求来源" (
  "所属用户" TEXT NOT NULL,
  "清单条目标识" TEXT NOT NULL,
  "食材需求标识" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "清单条目标识", "食材需求标识")
);

CREATE TABLE "个人用餐身份" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "当前餐食修订" BIGINT NOT NULL,
  "并发版本" BIGINT NOT NULL,
  "身份状态" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "个人用餐版本" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "业务用餐日期" DATE NOT NULL,
  "规范餐次" TEXT NOT NULL,
  "实际时点" TIMESTAMPTZ,
  "用户自述" TEXT,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识", "修订号")
);

CREATE TABLE "个人实际食物" (
  "所属用户" TEXT NOT NULL,
  "用餐身份" TEXT NOT NULL,
  "用餐修订" BIGINT NOT NULL,
  "条目标识" TEXT NOT NULL,
  "实际食物名称" TEXT NOT NULL,
  "食品证据标识" TEXT,
  "计划食物出处" TEXT,
  "录入来源" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "个人实际份量状态" TEXT NOT NULL,
  "个人实际份量定点值" BIGINT,
  "个人实际份量单位" TEXT,
  PRIMARY KEY ("所属用户", "用餐身份", "用餐修订", "条目标识")
);

CREATE TABLE "微行动提案" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "情境标识" TEXT NOT NULL,
  "行动维度" TEXT NOT NULL,
  "行动线索" TEXT NOT NULL,
  "具体行为" TEXT NOT NULL,
  "努力量" TEXT NOT NULL,
  "行动依据" TEXT NOT NULL,
  "被替代提案标识" TEXT,
  "关联计划餐次" TEXT,
  "当前窗口修订" BIGINT,
  "当前执行修订" BIGINT,
  "并发版本" BIGINT NOT NULL,
  "身份状态" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  "关联实际用餐标识" TEXT,
  "关联实际用餐修订号" BIGINT,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "行动最终决策" (
  "所属用户" TEXT NOT NULL,
  "行动标识" TEXT NOT NULL,
  "用户决策" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "行动标识")
);

CREATE TABLE "行动窗口修订" (
  "所属用户" TEXT NOT NULL,
  "行动标识" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "窗口开始" TIMESTAMPTZ NOT NULL,
  "窗口结束" TIMESTAMPTZ NOT NULL,
  "业务时区" TEXT NOT NULL,
  "确认或修正原因" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "行动标识", "修订号")
);

CREATE TABLE "执行自述修订" (
  "所属用户" TEXT NOT NULL,
  "行动标识" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "有效自述状态" TEXT NOT NULL,
  "实际执行日期" DATE,
  "报告时间" TIMESTAMPTZ NOT NULL,
  "执行自述备注" TEXT,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "行动标识", "修订号")
);

CREATE TABLE "提醒与回应历史" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "行动标识" TEXT NOT NULL,
  "计划提醒时间" TIMESTAMPTZ NOT NULL,
  "实际提醒时间" TIMESTAMPTZ,
  "回应时间" TIMESTAMPTZ,
  "发送结果" TEXT NOT NULL,
  "发送授权修订" BIGINT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "交互与提醒状态" (
  "所属用户" TEXT NOT NULL,
  "并发版本" BIGINT NOT NULL,
  "连续未响应数" BIGINT NOT NULL,
  "静默截止" TIMESTAMPTZ,
  "陪伴开启" SMALLINT NOT NULL,
  "图鉴开启" SMALLINT NOT NULL,
  "校准开启" SMALLINT NOT NULL,
  "内环规则版本" TEXT NOT NULL,
  "内环参数及原因" JSONB NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户")
);

CREATE TABLE "内环决策记录" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "情境标识" TEXT NOT NULL,
  "行动标识" TEXT,
  "交互类型" TEXT NOT NULL,
  "排序规则版本" TEXT NOT NULL,
  "依据及参数" JSONB NOT NULL,
  "情境冷却截止" TIMESTAMPTZ,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "偏好与情境候选" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "候选类型" TEXT NOT NULL,
  "待核对内容" JSONB NOT NULL,
  "核对状态" TEXT NOT NULL,
  "来源授权修订" BIGINT NOT NULL,
  "证据开始日期" DATE NOT NULL,
  "证据结束日期" DATE NOT NULL,
  "核对时间" TIMESTAMPTZ,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "学习证据引用" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "候选标识" TEXT NOT NULL,
  "来源行动" TEXT,
  "来源执行修订" BIGINT,
  "来源用餐" TEXT,
  "来源用餐修订" BIGINT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "稳定偏好修订" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "已确认候选" TEXT NOT NULL,
  "条件方向与适用范围" JSONB NOT NULL,
  "规则状态" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识", "修订号")
);

CREATE TABLE "校准回答修订" (
  "所属用户" TEXT NOT NULL,
  "题目标识" TEXT NOT NULL,
  "题目版本" TEXT NOT NULL,
  "修订号" BIGINT NOT NULL,
  "确认回答" JSONB,
  "回答状态" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "题目标识", "修订号")
);

CREATE TABLE "预期餐次版本" (
  "所属用户" TEXT NOT NULL,
  "自然周起始" DATE NOT NULL,
  "修订号" BIGINT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "自然周起始", "修订号")
);

CREATE TABLE "预期餐次槽位" (
  "所属用户" TEXT NOT NULL,
  "自然周起始" DATE NOT NULL,
  "预期餐次修订" BIGINT NOT NULL,
  "餐次日期" DATE NOT NULL,
  "规范餐次" TEXT NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "自然周起始", "预期餐次修订", "餐次日期", "规范餐次")
);

CREATE TABLE "恢复周期确认" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "并发版本" BIGINT NOT NULL,
  "确认偏离起点" TIMESTAMPTZ,
  "确认回归终点" TIMESTAMPTZ,
  "用户确认情境" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "恢复排除时段" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "恢复周期标识" TEXT NOT NULL,
  "排除开始" TIMESTAMPTZ NOT NULL,
  "排除结束" TIMESTAMPTZ NOT NULL,
  "排除原因" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识")
);

CREATE TABLE "连续周呈现修订" (
  "所属用户" TEXT NOT NULL,
  "自然周起始" DATE NOT NULL,
  "修订号" BIGINT NOT NULL,
  "呈现决定" TEXT NOT NULL,
  "用户确认依据" TEXT NOT NULL,
  "用户确认时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "自然周起始", "修订号")
);

CREATE TABLE "持久提交回执" (
  "所属用户" TEXT NOT NULL,
  "操作标识" TEXT NOT NULL,
  "规范化请求摘要" TEXT NOT NULL,
  "唯一提交标识" TEXT NOT NULL,
  "来源任务标识" TEXT,
  "提交授权修订" BIGINT NOT NULL,
  "提交数据修订" BIGINT NOT NULL,
  "结果标识与版本" JSONB NOT NULL,
  "操作令牌签发时间" TIMESTAMPTZ NOT NULL,
  "回执过期时间" TIMESTAMPTZ NOT NULL,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "操作标识"),
  UNIQUE ("所属用户", "唯一提交标识")
);

CREATE TABLE "最小化业务事件" (
  "所属用户" TEXT NOT NULL,
  "事件标识" TEXT NOT NULL,
  "提交标识" TEXT NOT NULL,
  "事件类型" TEXT NOT NULL,
  "对象类型" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "对象修订" BIGINT,
  "原因编码" TEXT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  "保留截止" TIMESTAMPTZ NOT NULL,
  "续期确认时间" TIMESTAMPTZ,
  PRIMARY KEY ("所属用户", "事件标识")
);

CREATE TABLE "导出删除清理任务" (
  "所属用户" TEXT NOT NULL,
  "对象标识" TEXT NOT NULL,
  "处理类型" TEXT NOT NULL,
  "处理进度" TEXT NOT NULL,
  "范围与断点" JSONB NOT NULL,
  "请求时间" TIMESTAMPTZ NOT NULL,
  "目标截止" TIMESTAMPTZ NOT NULL,
  "完成时间" TIMESTAMPTZ,
  "临时导出文件键" TEXT,
  "导出文件过期" TIMESTAMPTZ,
  "失败原因编码" TEXT,
  "建立时间" TIMESTAMPTZ NOT NULL,
  PRIMARY KEY ("所属用户", "对象标识")
);

ALTER TABLE "用户处理控制" ADD FOREIGN KEY ("所属用户", "当前档案修订") REFERENCES "档案确认版本" ("所属用户", "修订号");

ALTER TABLE "档案确认版本" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "临时图片" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "用途授权修订" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "用途授权修订" ADD FOREIGN KEY ("所属用户", "外传图片标识") REFERENCES "临时图片" ("所属用户", "对象标识");

ALTER TABLE "临时任务会话" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "已确认情境" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "已确认情境" ADD FOREIGN KEY ("所属用户", "档案修订") REFERENCES "档案确认版本" ("所属用户", "修订号");

ALTER TABLE "证据来源" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "证据来源" ADD FOREIGN KEY ("所属用户", "原图片标识") REFERENCES "临时图片" ("所属用户", "对象标识");

ALTER TABLE "食品证据版本" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "食品证据版本" ADD FOREIGN KEY ("所属用户", "上一证据版本") REFERENCES "食品证据版本" ("所属用户", "对象标识");

ALTER TABLE "食品逐字段事实" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "食品逐字段事实" ADD FOREIGN KEY ("所属用户", "食品证据标识") REFERENCES "食品证据版本" ("所属用户", "对象标识");

ALTER TABLE "字段来源关联" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "字段来源关联" ADD FOREIGN KEY ("所属用户", "食品证据标识", "字段键") REFERENCES "食品逐字段事实" ("所属用户", "食品证据标识", "字段键");

ALTER TABLE "字段来源关联" ADD FOREIGN KEY ("所属用户", "来源标识") REFERENCES "证据来源" ("所属用户", "对象标识");

ALTER TABLE "约束评估" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "约束评估" ADD FOREIGN KEY ("所属用户", "情境标识") REFERENCES "已确认情境" ("所属用户", "对象标识");

ALTER TABLE "约束评估" ADD FOREIGN KEY ("所属用户", "食品证据标识") REFERENCES "食品证据版本" ("所属用户", "对象标识");

ALTER TABLE "标准食材" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "计划身份" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "计划身份" ADD FOREIGN KEY ("所属用户", "对象标识", "当前确认修订") REFERENCES "计划确认版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "计划确认版本" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "计划确认版本" ADD FOREIGN KEY ("所属用户", "对象标识") REFERENCES "计划身份" ("所属用户", "对象标识");

ALTER TABLE "计划确认版本" ADD FOREIGN KEY ("所属用户", "情境标识") REFERENCES "已确认情境" ("所属用户", "对象标识");

ALTER TABLE "计划餐次" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "计划餐次" ADD FOREIGN KEY ("所属用户", "计划标识", "计划修订") REFERENCES "计划确认版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "计划食物" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "计划食物" ADD FOREIGN KEY ("所属用户", "计划餐次标识") REFERENCES "计划餐次" ("所属用户", "对象标识");

ALTER TABLE "计划食物" ADD FOREIGN KEY ("所属用户", "食品证据标识") REFERENCES "食品证据版本" ("所属用户", "对象标识");

ALTER TABLE "计划食物" ADD FOREIGN KEY ("所属用户", "约束评估标识") REFERENCES "约束评估" ("所属用户", "对象标识");

ALTER TABLE "食材需求" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "食材需求" ADD FOREIGN KEY ("所属用户", "计划食物标识") REFERENCES "计划食物" ("所属用户", "对象标识");

ALTER TABLE "食材需求" ADD FOREIGN KEY ("所属用户", "食材标识") REFERENCES "标准食材" ("所属用户", "对象标识");

ALTER TABLE "食材需求" ADD FOREIGN KEY ("所属用户", "配方来源") REFERENCES "证据来源" ("所属用户", "对象标识");

ALTER TABLE "当前槽位归属" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "当前槽位归属" ADD FOREIGN KEY ("所属用户", "当前计划餐次标识", "餐次日期", "规范餐次") REFERENCES "计划餐次" ("所属用户", "对象标识", "餐次日期", "规范餐次");

ALTER TABLE "库存身份" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "库存身份" ADD FOREIGN KEY ("所属用户", "标准食材标识") REFERENCES "标准食材" ("所属用户", "对象标识");

ALTER TABLE "库存身份" ADD FOREIGN KEY ("所属用户", "对象标识", "当前库存修订") REFERENCES "库存核对版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "库存核对版本" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "库存核对版本" ADD FOREIGN KEY ("所属用户", "对象标识") REFERENCES "库存身份" ("所属用户", "对象标识");

ALTER TABLE "准备采购清单" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "准备采购清单" ADD FOREIGN KEY ("所属用户", "来源计划标识", "来源计划修订") REFERENCES "计划确认版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "清单条目" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "清单条目" ADD FOREIGN KEY ("所属用户", "清单标识") REFERENCES "准备采购清单" ("所属用户", "对象标识");

ALTER TABLE "清单条目" ADD FOREIGN KEY ("所属用户", "标准食材标识") REFERENCES "标准食材" ("所属用户", "对象标识");

ALTER TABLE "清单条目" ADD FOREIGN KEY ("所属用户", "所用库存身份", "所用库存修订") REFERENCES "库存核对版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "清单需求来源" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "清单需求来源" ADD FOREIGN KEY ("所属用户", "清单条目标识") REFERENCES "清单条目" ("所属用户", "对象标识");

ALTER TABLE "清单需求来源" ADD FOREIGN KEY ("所属用户", "食材需求标识") REFERENCES "食材需求" ("所属用户", "对象标识");

ALTER TABLE "个人用餐身份" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "个人用餐身份" ADD FOREIGN KEY ("所属用户", "对象标识", "当前餐食修订") REFERENCES "个人用餐版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "个人用餐版本" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "个人用餐版本" ADD FOREIGN KEY ("所属用户", "对象标识") REFERENCES "个人用餐身份" ("所属用户", "对象标识");

ALTER TABLE "个人实际食物" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "个人实际食物" ADD FOREIGN KEY ("所属用户", "用餐身份", "用餐修订") REFERENCES "个人用餐版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "个人实际食物" ADD FOREIGN KEY ("所属用户", "食品证据标识") REFERENCES "食品证据版本" ("所属用户", "对象标识");

ALTER TABLE "个人实际食物" ADD FOREIGN KEY ("所属用户", "计划食物出处") REFERENCES "计划食物" ("所属用户", "对象标识");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户", "关联实际用餐标识", "关联实际用餐修订号") REFERENCES "个人用餐版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户", "情境标识") REFERENCES "已确认情境" ("所属用户", "对象标识");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户", "被替代提案标识") REFERENCES "微行动提案" ("所属用户", "对象标识");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户", "关联计划餐次") REFERENCES "计划餐次" ("所属用户", "对象标识");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户", "对象标识", "当前窗口修订") REFERENCES "行动窗口修订" ("所属用户", "行动标识", "修订号");

ALTER TABLE "微行动提案" ADD FOREIGN KEY ("所属用户", "对象标识", "当前执行修订") REFERENCES "执行自述修订" ("所属用户", "行动标识", "修订号");

ALTER TABLE "行动最终决策" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "行动最终决策" ADD FOREIGN KEY ("所属用户", "行动标识") REFERENCES "微行动提案" ("所属用户", "对象标识");

ALTER TABLE "行动窗口修订" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "行动窗口修订" ADD FOREIGN KEY ("所属用户", "行动标识") REFERENCES "行动最终决策" ("所属用户", "行动标识");

ALTER TABLE "执行自述修订" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "执行自述修订" ADD FOREIGN KEY ("所属用户", "行动标识") REFERENCES "行动最终决策" ("所属用户", "行动标识");

ALTER TABLE "提醒与回应历史" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "提醒与回应历史" ADD FOREIGN KEY ("所属用户", "行动标识") REFERENCES "行动最终决策" ("所属用户", "行动标识");

ALTER TABLE "交互与提醒状态" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "内环决策记录" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "内环决策记录" ADD FOREIGN KEY ("所属用户", "情境标识") REFERENCES "已确认情境" ("所属用户", "对象标识");

ALTER TABLE "内环决策记录" ADD FOREIGN KEY ("所属用户", "行动标识") REFERENCES "微行动提案" ("所属用户", "对象标识");

ALTER TABLE "偏好与情境候选" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "学习证据引用" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "学习证据引用" ADD FOREIGN KEY ("所属用户", "候选标识") REFERENCES "偏好与情境候选" ("所属用户", "对象标识");

ALTER TABLE "学习证据引用" ADD FOREIGN KEY ("所属用户", "来源行动", "来源执行修订") REFERENCES "执行自述修订" ("所属用户", "行动标识", "修订号");

ALTER TABLE "学习证据引用" ADD FOREIGN KEY ("所属用户", "来源用餐", "来源用餐修订") REFERENCES "个人用餐版本" ("所属用户", "对象标识", "修订号");

ALTER TABLE "稳定偏好修订" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "稳定偏好修订" ADD FOREIGN KEY ("所属用户", "已确认候选") REFERENCES "偏好与情境候选" ("所属用户", "对象标识");

ALTER TABLE "校准回答修订" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "预期餐次版本" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "预期餐次槽位" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "预期餐次槽位" ADD FOREIGN KEY ("所属用户", "自然周起始", "预期餐次修订") REFERENCES "预期餐次版本" ("所属用户", "自然周起始", "修订号");

ALTER TABLE "恢复周期确认" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "恢复排除时段" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "恢复排除时段" ADD FOREIGN KEY ("所属用户", "恢复周期标识") REFERENCES "恢复周期确认" ("所属用户", "对象标识");

ALTER TABLE "连续周呈现修订" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "持久提交回执" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "持久提交回执" ADD FOREIGN KEY ("所属用户", "来源任务标识") REFERENCES "临时任务会话" ("所属用户", "对象标识");

ALTER TABLE "最小化业务事件" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");

ALTER TABLE "最小化业务事件" ADD FOREIGN KEY ("所属用户", "提交标识") REFERENCES "持久提交回执" ("所属用户", "唯一提交标识");

ALTER TABLE "导出删除清理任务" ADD FOREIGN KEY ("所属用户") REFERENCES "用户处理控制" ("所属用户");
