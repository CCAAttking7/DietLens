workspace "DietLens系统架构" "第二轮第三阶段候选架构；中文视图，设计不部署" {
    model {
        user = person "成年用户" "管理本人饮食目标、计划、实际餐食及微行动"
        modelProvider = softwareSystem "外部模型服务" "按授权理解输入与组织候选，不拥有业务写权限"
        foodSources = softwareSystem "食品参考来源" "公开食品资料、当前标签及本地食物编码；完整性分别核对"
        identityProvider = softwareSystem "托管身份服务" "验证访问令牌，仅托管模式使用"
        dietlens = softwareSystem "DietLens饮食工作台" "连接饮食选择、未来准备、个人实际记录及微习惯反馈" {
            web = container "网页工作台" "对话入口、结构化核对、确认、版本差异与恢复" "React / TypeScript"
            api = container "后端应用" "一个可部署进程内划分领域模块，统一可信命令和授权查询" "Python / FastAPI" {
                boundary = component "请求与身份模块" "解析请求，验证主体与归属，映射错误与响应" "请求作用域"
                commands = component "命令与任务模块" "确认绑定、恢复、幂等、版本、短事务及任务进度" "受控编排"
                profile = component "档案与授权模块" "确认档案、用途授权、校准及当前处理控制" "确定性规则"
                food = component "食品证据模块" "来源、逐字段核对、单位、菜单和硬约束评估" "确定性规则"
                planning = component "计划与准备模块" "选定餐次、人数、多食材、清单与手动库存" "确定性规则"
                meals = component "实际餐食模块" "一次个人用餐内的食物条目、份量及有效修订" "确定性规则"
                actions = component "微行动模块" "提案、采纳窗口、执行修订、提醒与偏好候选" "确定性规则"
                review = component "回顾查询模块" "执行周、结束队列、餐次覆盖和可追溯观察" "授权只读聚合"
                executor = component "外部工具执行模块" "输入输出契约、白名单、预算、超时和只读重试" "可替换适配器"
                persistence = component "存储与事务模块" "用户域处理控制、条件版本更新、事件及回执" "数据库适配器"
                maintenance = component "期限与数据控制模块" "删除、过期、派生失效与最小化审计" "同包维护入口"
            }
            db = container "权威业务库" "一次部署择一保存确认事实、版本、任务、事件及回执" "本地SQLite或托管PostgreSQL"
        }
        user -> web "描述、核对、确认与查看"
        web -> boundary "业务请求及访问令牌" "HTTP / HTTPS"
        boundary -> commands "已认证的确认命令"
        boundary -> review "已认证的期间查询"
        boundary -> profile "档案及当前授权查询"
        boundary -> food "授权食品查询"
        boundary -> identityProvider "核验托管访问令牌" "HTTPS"
        commands -> profile "检查当前用途授权和档案版本"
        commands -> food "取得并复核候选证据"
        commands -> planning "计划、清单、库存业务命令"
        commands -> meals "个人餐食确认与修正"
        commands -> actions "微行动采纳、窗口和执行反馈"
        commands -> persistence "一次命令的提交、回滚及回执"
        food -> executor "已授权的食品资料检索"
        commands -> executor "可选结构化理解及候选整理"
        executor -> modelProvider "最小必要输入，返回候选" "HTTPS"
        executor -> foodSources "带来源的只读资料" "HTTPS / 本地索引"
        profile -> persistence "档案及用途授权事实"
        food -> persistence "证据和核对版本"
        planning -> persistence "计划、当前槽位、清单与库存"
        meals -> persistence "用餐、食物条目与修订"
        actions -> persistence "行动、窗口、执行和派生证据引用"
        review -> profile "当前历史分析授权"
        review -> persistence "同一授权范围的有效版本快照"
        maintenance -> profile "撤回和删除后的处理范围"
        maintenance -> persistence "期限清理及派生结果失效"
        persistence -> db "有界查询及原子写入" "参数化数据库访问"
        deploymentEnvironment "本地演示" {
            deploymentNode "演示电脑" "单机演示，不作为多用户托管配置" "Windows" {
                deploymentNode "浏览器" "访问本地网页" {
                    containerInstance web
                }
                deploymentNode "应用运行环境" "前端开发服务及一个后端进程" "Node.js / Python" {
                    containerInstance api
                }
                deploymentNode "本机数据文件" "本地独立数据集，文件不放共享网络盘" "SQLite / WAL" {
                    containerInstance db
                }
            }
        }
        deploymentEnvironment "目标托管" {
            deploymentNode "用户设备" "浏览器和当前登录会话" {
                containerInstance web
            }
            deploymentNode "应用主机" "加密入口提供静态网页并转发请求；首轮单实例" "Linux / HTTPS" {
                deploymentNode "应用进程" "服务端凭据、维护入口及有界请求处理" "Python / FastAPI" {
                    containerInstance api
                }
            }
            deploymentNode "托管数据库节点" "唯一生产权威库及期限明确的备份" "PostgreSQL" {
                containerInstance db
            }
        }
    }
    views {
        systemContext dietlens "A01-context" {
            title "A01 系统上下文：饮食管理与微习惯支持"
            include *
            autoLayout lr
        }
        container dietlens "A02-containers" {
            title "A02 运行单元：网页、单体后端和唯一权威库"
            include *
            autoLayout tb
        }
        component api "A03-modules" {
            title "A03 后端模块与数据责任"
            include *
            autoLayout tb
        }
        deployment dietlens "本地演示" "A04-local" {
            title "A04 本地演示部署"
            include *
            autoLayout tb
        }
        deployment dietlens "目标托管" "A05-hosted" {
            title "A05 目标托管部署"
            include *
            autoLayout tb
        }
        terminology {
            person "用户"
            softwareSystem "软件系统"
            container "运行单元"
            component "模块"
            deploymentNode "部署节点"
            infrastructureNode "基础设施"
            relationship "关系"
        }
        styles {
            element "Element" {
                color #24231f
                background #edf3ed
                stroke #486958
                fontSize 22
            }
            element "Person" {
                shape Person
                background #f3e1d9
            }
            element "Deployment Node" {
                background #fcfbf7
            }
            relationship "Relationship" {
                color #486958
                fontSize 18
            }
        }
    }
}
