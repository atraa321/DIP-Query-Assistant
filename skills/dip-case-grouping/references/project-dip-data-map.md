# 本项目DIP数据映射

本文件描述当前项目里 DIP 分组核算所依赖的数据文件、代码入口与结果表。用户要求“查现有 skill 和项目规则”时，应优先参考这里。

## 1. 基础文件位置

项目根目录下的 `数据仓库/` 已包含 DIP 相关种子文件：

- `数据仓库/平顶山2025年DIP2.0分组目录库.xlsx`
- `数据仓库/ICD10国临版2.0对照医保版2.0.xlsx`
- `数据仓库/ICD9国临版3.0对照医保版2.0.xlsx`

用途对应如下：

- ICD10 对照表：主诊断国临版 -> 医保版
- ICD9 对照表：主手术/操作国临版 -> 医保版
- DIP 目录库：病种组合、病种类型、分值，以及目录附带说明

## 2. 现有后端实现入口

核心入口文件：

- `backend/app/services/dip_rebuild_service.py`
- `backend/app/services/dip_service.py`
- `backend/app/repositories/dip_repository.py`
- `backend/app/schemas/dip.py`

优先复用这些服务，不要另起炉灶定义一套新的状态字段。

## 3. 当前重算逻辑摘要

`DipRebuildService` 当前做了这些事：

1. 检查 Excel 种子文件是否存在
2. 将 3 份基础文件加载到种子表
3. 读取 `dwd_case` 和 `dws_case_fee_summary`
4. 先将主诊断、主手术转换到医保版编码
   如果未能通过 ICD10/ICD9 对照表转成医保码，不应直接拿原始临床码参与正式入组
   ICD9 中像 `6.31 -> 06.3100`、`4.43 -> 04.4300` 这类前导零差异，可在对照表范围内归一化后再入组
5. 在 `seed_dip_directory` 中按优先级匹配
6. 生成病例级结果
7. 根据点值计算预计结算与结余
8. 聚合到医院、科室、病组三层指标表

## 4. 当前匹配优先级

当前项目应按以下新口径执行，而不是继续沿用旧的 `main_diag / icd3 partial` 降级顺序：

1. 将主诊断统一到医保版后，截取前 5 位（保留小数点）作为核心病种诊断键
2. 将主诊断前三位作为综合病种诊断键
3. 先判断治疗方式属性：
   `BSZL` 保守治疗、`ZDXCZ` 诊断性操作、`ZLXCZ` 治疗性操作、`SS` 手术
4. 任何病例只要存在 `诊断前 5 位 + 操作编码` 的核心精确行，先命中核心病种
5. 若无精确核心行，`SS` 病例再按 `诊断前三位 + SS` 命中综合病种
6. 若无精确核心行，`ZDXCZ`、`ZLXCZ` 再按 `诊断前三位 + 类型` 命中综合病种
7. 无操作编码病例先按 `诊断前 5 位` 尝试命中核心病种中的诊断直匹配行
8. 若无操作病例未命中核心病种，再按 `诊断前三位 + BSZL` 命中综合病种

命中状态：

- `matched`：精确命中
- `unmatched`：未命中

说明：

- 新口径下，综合病种属于正式入组，不再作为 `partial` 处理
- 历史数据里如果出现 `partial`，应理解为旧版 `ICD3` 降级命中结果

多候选时，当前实现优先：

1. `核心病种`
2. 分值更高
3. 编码顺序更靠前

## 5. 当前主要输入表

### 病例与费用

- `dwd_case`
  - `case_id`
  - `record_month`
  - `discharge_dept_name`
  - `main_diagnosis_code`
  - `diagnosis_icd3`
  - `main_diagnosis_name`
  - `main_operation_code`
  - `main_operation_name`
  - `stay_days`

- `dws_case_fee_summary`
  - `case_id`
  - `total_fee`

### 点值

- `sys_dip_point_value`
  - `stat_month`
  - `point_value`
  - `status`

## 6. 当前种子表

- `seed_icd10_dip_mapping`
- `seed_icd9_dip_mapping`
- `seed_dip_directory`

其中 `seed_dip_directory` 会承载：

- `dip_group_code`
- `group_type`
- `main_diag_code`
- `main_operation_code`
- `other_operation_code`
- `score_value`
- `weight_score`
- `dip_avg_fee`
- `avg_ipt_days`
- `remark`

`seed_icd9_dip_mapping` 当前只存储医保版手术编码与医保版手术名称：

- `dip_code`
- `dip_name`

其中 `医保2.0手术名称` 列实际混合了承载手术、诊断性操作、治疗性操作三类对象。
项目当前会基于已有编码和名称做临时归类；若后续建立独立“操作属性映射表”，应优先切换到显式映射，不再依赖名称/编码段推断。

## 6.1 本地目录库的病种类型特殊值

本地 `平顶山2025年DIP2.0分组目录库.xlsx` 的 `病种类型（1.核心病种；2.综合病种）` 列，实测出现的是：

- `1`：核心病种
- `0`：综合病种

也就是说，这份地方目录库没有完全沿用列名里写的 `2=综合病种` 表达。

使用该目录时要先做本地化归一化，不要机械按列名把综合病种只识别为 `2`。

## 7. 当前结果表

### 明细层

- `dwd_case_dip_match`
  - 匹配前后编码
  - DIP 组别
  - 匹配规则
  - 未命中原因

- `dws_dip_case_result`
  - `score_value`
  - `point_value`
  - `estimated_settlement_amount`
  - `total_fee`
  - `balance_amount`
  - `profit_flag`
  - `match_status`
  - `calc_mode`

### 汇总层

- `ads_dip_monthly_hospital_metrics`
- `ads_dip_monthly_dept_metrics`
- `ads_dip_monthly_group_metrics`

## 8. 当前口径边界

已经实现：

- 编码映射
- 核心病种 + 综合病种分层入组
- 点值乘分值试算
- 科室/病组/月度聚合
- 亏损/结余标记

尚未完整实现或未在当前代码中显式体现：

- 自费/特定自付/起付线/报销比例分解
- 病案质量指数调节金
- 二次入院/低标入院/超长住院/死亡风险调校
- 专家评议扣减费用
- 独立的 `SS / ZDXCZ / ZLXCZ / BSZL` 操作属性基础映射表

所以当前结果更适合表述为：

- `DIP经营核算结果`
- `DIP试算结果`
- `DIP主目录分组结果`

除非用户明确说明当地结算口径已被完整建模，否则不要直接称为“正式医保清算结果”。
