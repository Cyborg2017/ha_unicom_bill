# ha_unicom_bill 集成说明：API 与字段映射

> 本文记录集成实际调用的接口、字段、认证方式，以及「本月话费」传感器的取数口径。
> 所有结论均以 2026-11-08 的实际请求与响应为准。

---

## 1. 集成结构

| 模块 | 文件 | 职责 |
|---|---|---|
| 集成入口 | `__init__.py` | 创建 API 实例、自动探测手机号、启动 coordinator、注册前端卡片资源 |
| 配置流程 | `config_flow.py` | 录入 `openid` / 刷新间隔 / 是否创建详细传感器；选项变更后 `async_reload` |
| 常量 | `const.py` | 7 个 API 地址、请求头、默认值 |
| API 客户端 | `api.py` | 自动认证（ticket + Cookie）、4 类数据抓取与解析 |
| 协调器 | `coordinator.py` | `DataUpdateCoordinator`，按刷新间隔（默认 15 分钟）轮询 `fetch_all_data()` |
| 传感器 | `sensor.py` | 4 个基础传感器 + 23 个详细传感器 |
| 前端卡片 | `www/ha-unicom-card.js` | `custom:ha-unicom-card`，按实体名正则自动发现实体 |
| 翻译 | `translations/zh-Hans.json` | 27 个实体的中文名（`entity.sensor.<key>.name`） |

### 数据流

```
每 N 分钟
  └─ UnicomBillCoordinator._async_update_data()
       └─ UnicomAPI.fetch_all_data()
            ├─ 0. _auto_get_auth()        → ticket + microHall Cookie
            ├─ 1. get_overview()          → sspbigball           → data["overview"]
            ├─ 2. get_balance_detail()    → accountBalancenew    → data["balance_detail"]
            ├─ 3. get_bill_detail()       → queryDetail          → data["bill_detail"]
            └─ 4. get_usage_detail()      → queryOcsPackage...   → data["usage_details"]
  └─ 各 Sensor.native_value → description.value_fn(coordinator.data)
```

`coordinator.data` 是固定四键的 dict：

```python
{
  "overview":       {},   # sspbigball 的 data
  "balance_detail": {},   # accountBalancenew 的 data
  "bill_detail":    {},   # queryDetail 的 data
  "usage_details":  {},   # 解析后的语音 / 短信 / 流量
}
```

---

## 2. 认证链路

| 步骤 | 请求 | 说明 |
|---|---|---|
| 1 | `POST https://mina.10010.com/wxapplet/weixinNew/getTicket`<br>body `{"openId": "<openid>", "channel": "wxmini"}` | 返回 `data` 为 ticket 字符串，`code == "0000"` 成功 |
| 2 | `GET https://mxx.client.10010.com/servicebusiness/wx/serviceEntrance`<br>`?ticket=<ticket>&servicecode=YH10007&ticketChannel=XCXSYHF` | 返回 **302**，从 `Set-Cookie` 提取 `microHallUser`、`microHallAccessToken`，拼成后续请求的 `Cookie` 头 |

- ticket 有效期分钟级，因此每轮轮询都重新走一遍（`_auto_get_auth()` 是 `fetch_all_data()` 的第一步）。
- `ticketPhone` 是客户端生成值，格式 `wx<毫秒时间戳>`。
- **`servicecode` 与 `ticketChannel` 必须成对**，服务端会校验：

| servicecode | ticketChannel | 入口结果 | 跳转目标 |
|---|---|---|---|
| `YH10007` | `XCXSYHF` | 302，**下发 Cookie** | `/shengyuhuafei2/index.html`（余额页）|
| `YH10003` | `XCXLSZD` | 302，**下发 Cookie** | `/huafeiyuzhangdan2/index.html`（账单页）|
| `YH10007` | `XCXLSZD` | 302，**无 Cookie** | `errPage?errorCode=ECS000042` |
| `YH10003` | `XCXSYHF` | 302，**无 Cookie** | `errPage?errorCode=ECS000042` |

两个合法配对拿到的是同一个用户会话，调用后续接口结果一致。本项目用 `YH10007` / `XCXSYHF`（余额入口）。

- `serviceEntrance` 必须 **关闭跟随跳转**（`allow_redirects=False`），否则会跟到 `imgxx.client.10010.com` 的 H5 页，最终响应里没有 `Set-Cookie`，Cookie 取不到。

---

## 3. API 清单

| # | 常量 | 方法 | URL | 认证方式 | 用途 |
|---|---|---|---|---|---|
| 1 | `API_GET_TICKET` | POST JSON | `mina.10010.com/wxapplet/weixinNew/getTicket` | openid | 换 ticket |
| 2 | `API_SERVICE_ENTRANCE` | GET | `mxx.client.10010.com/servicebusiness/wx/serviceEntrance` | ticket | 换 microHall Cookie |
| 3 | `API_SSPBIGBALL` | POST JSON | `mina.10010.com/wxapplet/weixinNew/sspbigball` | openid | 概览 |
| 4 | `API_QUERY_GOODS_LIST` | POST JSON | `mina.10010.com/wxapplet/weixinNew/queryGoodsList` | openid | 取完整手机号 `mainNumber` |
| 5 | `API_BALANCE_DETAIL` | POST Form | `mxx.client.10010.com/servicequerybusiness/balancenew/accountBalancenew.htm` | ticket + Cookie | 余额 / 实时话费 |
| 6 | `API_BILL_DETAIL` | POST Form | `m.client.10010.com/serviceimportantbusiness/phoneBillNew/queryDetail` | ticket + Cookie | 月度话费（本月话费） |
| 7 | `API_USAGE_DETAIL` | POST Form | `mxx.client.10010.com/servicequerybusiness/operationservice/queryOcsPackageFlowLeftContentRevisedInJune` | ticket + Cookie | 语音 / 短信 / 流量详单 |

四个 form 接口共用同一套表单骨架：

```
duanlianjieabc=""&channelCode=""&serviceType=""&saleChannel=""&externalSources=""
&contactCode=""&ticket=<ticket>&ticketPhone=<wx时间戳>&ticketChannel=<渠道码>&language="chinese"
+ 接口特有字段
```

- `accountBalancenew.htm` 额外：`channel=client`
- `queryDetail` 额外：`month=YYYYMM`
- 渠道码：余额/账单用 `XCXSYHF`，用量详单用 `XCXYLCXYY`

---

## 4. 字段映射（sensor key → 中文名 → jsonPath）

### 4.1 基础传感器（始终创建）

| key | 中文名 | 数据源 | jsonPath |
|---|---|---|---|
| `voice_usage` | 已用语音 (min) | usage | `$.voice.use` ← `elemType=="1"` 的 `use` 求和 |
| `sms_usage` | 已用短信 (条) | usage | `$.sms.use` ← `elemType=="2"` 的 `use` 求和 |
| `data_usage` | 已用流量(合计) GB | usage | `sum(data_items[*].use / 1024)`，仅计 `total>0` |
| `balance` | 账户余额 (CNY) | balance | `$.data.curntbalancecust` |

`balance` 的附加属性：

| 属性 | jsonPath |
|---|---|
| `available_balance` | `$.data.canusefeecustNew` → `$.data.canusefeecust` |
| `real_time_fee` | `$.data.totalrealfee` → `$.data.realfeecustnew` |
| `total_owed` | `$.data.allbowefeecust` |
| `credit_limit` | `$.data.canuselimitcust` |

### 4.2 详细传感器（`create_individual_sensors: true` 才创建）

| key | 中文名 | 数据源 | jsonPath |
|---|---|---|---|
| `real_fee` | **本月话费** | bill | `$.data.realPayFee` |
| `can_use_value` | 上月结余话费 | balance | `$.data.canusefeecustNew` → `$.data.canusefeecust` |
| `total_owed` | 账户欠费 | balance | `$.data.allbowefeecust` |
| `voice_total` / `voice_available` / `voice_ratio` | 语音总量 / 剩余 / 比例 % | usage | `$.voice.total` / `.remain` / `.usedPercent` |
| `sms_total` / `sms_available` / `sms_ratio` | 短信总量 / 剩余 / 比例 % | usage | `$.sms.total` / `.remain` / `.usedPercent` |
| `data_total` | 流量总量(合计) | usage | `sum(data_items[*].total)`，仅计 `total>0` |
| `data_available` | 剩余流量(合计) | usage | `sum(data_items[*].remain)` |
| `data_exceed` | 超支流量 | usage | `sum(data_items[*].xexceedvalue)` |
| `data_ratio` | 流量使用比例 % | usage | `sum(use) / sum(total) * 100` |
| `data_carried_over` | 上月转接流量 | usage | `sum(data_items[*].beforeTotal)` |
| `data_total_general` / `data_available_general` / `data_usage_general` | 流量(通用) 总量 / 剩余 / 已用 | usage | `flowType=="1"` |
| `data_total_exclusive` / `data_available_exclusive` / `data_usage_exclusive` | 流量(专属) | usage | `flowType=="2"` 且 `total>0` |
| `data_total_other` / `data_available_other` / `data_usage_other` | 流量(其他) | usage | `flowType=="3"` |

### 4.3 用量接口原始结构

```
{
  "unshared":  [ { "type": "...", "details": [ {elemType, addUpItemName, use, total,
                                                remain, xexceedvalue, usedPercent,
                                                endDate, beforeTotal, beforeRemain,
                                                beforeUse, flowType} ] } ],
  "shareData": { "details": [ ... 同上 ... ] },
  "resources": [ { "type": "Voice"|"smsList"|..., "userResource", "remainResource",
                   "details": [ ... 同上 ... ] } ]
}
```

- `elemType`：`"1"`=语音，`"2"`=短信，`"3"`=流量
- `flowType`：`"1"`=通用，`"2"`=专属/定向，`"3"`=其他（区域/公免）
- 流量的 `use/total/remain/beforeTotal` 单位是 **MB**，展示时 `/1024` 转 GB
- 语音 / 短信按 `elemType` 求和；求和为空时回退到组级 `userResource` / `remainResource`

### 4.4 实体命名规则

- `unique_id` = `{entry_id}_{key}`
- `entity_id` = `sensor.unicom_{手机号去*}_{key}`；无手机号时 `sensor.ha_unicom_bill_{key}`
- 设备名 = 手机号（`entry.data["phone_number"]`）
- 卡片 `ha-unicom-card.js` 用正则 + 排序表（`/本月话费|real_fee/`）自动发现实体，**实体不存在时静默不显示**

---

## 5. 「本月话费」取数口径与故障记录

### 5.1 取数口径

「本月话费」= `queryDetail` 返回的 `data.realPayFee`，即联通口径的**本月已消费**。

真实响应（手机号 178****0499，2026-11-08）：

```json
{
  "code": "0000",
  "desc": "success",
  "data": {
    "amountDue": "0.00",
    "times": "2026-11-08 15:08:58",
    "noShowData": "本号码当月无消费",
    "realPayFee": "48.00",
    "acctBill": {
      "totalPrice": "68.00",
      "allRebates": "-10.00",
      "realPayFeeP": "48.00",
      "totalRealFee": "68.00"
    },
    "userBillList": [ "..." ]
  }
}
```

对账关系：`剩余话费 26.00 = 上月结转 74.00 + 本月存入 0.00 - 本月已消费 48.00`。

### 5.2 故障原因

传感器长期 `unknown`，原因是 `serviceEntrance` 取不到 `microHallUser` Cookie：

```
aiohttp 默认 allow_redirects=True
  → serviceEntrance 返回 302
  → 自动跟到 imgxx.client.10010.com 的 H5 页
  → 最终响应头里没有 Set-Cookie
  → _micro_hall_user 为空
  → _build_cookie_header() 返回空串
  → queryDetail 无会话请求
  → code=0002「很抱歉,服务器开小差」/ code=0004「未获取到用户信息」
  → get_bill_detail() 返回 {}
  → value_fn 返回 None → 传感器 unknown
```

### 5.3 修复

`api.py::_auto_get_auth()` 中关闭跟随跳转，其余全部保持原样：

```diff
-                async with self.session.get(entrance_url) as entrance_resp:
+                async with self.session.get(
+                    entrance_url,
+                    headers={"User-Agent": WX_USER_AGENT},
+                    allow_redirects=False,      # 唯一的功能性改动
+                ) as entrance_resp:
```

### 5.4 验证

```
DEBUG serviceEntrance success, got microHall Cookie
DEBUG Bill detail fetched successfully
INFO  Data updated successfully: overview=True, usage=True, balance=True, bill=True
```

实体：

```
sensor.unicom_17854120499_real_fee = 48.00
```

---

## 6. 已知问题（未改动）

1. `api.py:get_phone_number()` 的 fallback 与 `get_usage_detail()` 是同一接口同一请求，重复调用。
2. `get_bill_detail()` / `get_usage_detail()` 异常时抛 `UnicomAPIError`，会经 `fetch_all_data` 冒泡导致**整轮更新失败、所有实体不可用**；建议单个接口失败降级为空 dict。
3. `sensor.py:_build_data_attributes()` 读取 `usage["summary"]["can_use_flow_all"]`，但解析器从未产出 `summary`，属死代码。
4. `translations/` 只有 `zh-Hans.json`，缺 `en.json`，非中文环境会显示 key 原文。
5. `__init__.py` 用 `ClientSession()` 自行创建会话，未使用 `async_get_clientsession(hass)`，卸载时也没有关闭。

---

## 7. 调试脚本

放在 `debug/`（已加入 `.gitignore`，不进版本库）：

| 脚本 | 用途 |
|---|---|
| `debug/diagnose_unicom.py` | 打全部 7 个接口，原始 JSON 落盘，并按目标数值反查字段路径 |
| `debug/probe_bill_fix.py` | 变体对照实验（域名 × ticketChannel × 入口参数），定位认证卡在哪一步 |
| `debug/probe_queryDetail.py` | `queryDetail` 的参数变体（`month` 格式、`language`、UA、Referer 等） |
