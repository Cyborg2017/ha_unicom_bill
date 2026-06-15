# 中国联通话费查询 (ha_unicom_bill)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/Cyborg2017/ha_unicom_bill.svg)](https://GitHub.com/Cyborg2017/ha_unicom_bill/releases/)
[![License](https://img.shields.io/github/license/Cyborg2017/ha_unicom_bill.svg)](LICENSE)

Home Assistant 自定义集成，用于查询中国联通话费、流量、语音等信息。

![集成列表](images/1.png)

## ✨ 特性

- 📊 **27个传感器**：全面覆盖语音、短信、流量（通用/专属/其他分类）、余额信息
- 🔄 **自动更新**：可配置刷新间隔（1-60分钟）
- 🔐 **自动认证**：自动获取 ticket 和 Cookie，无需手动配置
- 🎨 **自定义卡片**：内置 Lovelace 自定义卡片，开箱即用
- 📱 **微信小程序**：基于联通微信小程序 API
- 🏗️ **模块化设计**：清晰的代码架构，易于维护和扩展

## 📦 安装

### 方法1: HACS（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 进入 HACS → 集成 → 点击右上角三个点 → 自定义仓库
3. 添加仓库：`https://github.com/Cyborg2017/ha_unicom_bill`
4. 分类选择：`Integration`
5. 点击"添加"
6. 搜索"China Unicom Bill"并安装
7. 重启 Home Assistant

### 方法2: 手动安装

1. 下载或克隆本仓库
2. 复制 `custom_components/ha_unicom_bill` 文件夹到 HA 的 `custom_components` 目录
3. 重启 Home Assistant
4. 在集成页面搜索"China Unicom Bill"并添加

## ⚙️ 配置

### 获取 OpenID

OpenID 是微信用户的唯一标识，需要从联通小程序中获取：

1. 安装抓包工具（Charles/Fiddler/Reqable）
2. 安装并信任证书
3. 打开【中国联通营业厅】小程序
4. 捕获 HTTPS 请求
5. 找到 `https://mina.10010.com/wxapplet/weixinNew/getTicket` 请求
6. 从请求体中提取 `openId`

### 配置步骤

![配置界面](images/2.png)

1. 进入 Home Assistant → 设置 → 设备与服务
2. 点击右下角"添加集成"
3. 搜索"China Unicom Bill"
4. 填写配置表单：

| 字段 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| OpenID | 从抓包获取的 OpenID | 是 | - |
| 刷新间隔 | 数据更新频率（分钟） | 是 | 15 |
| 创建独立传感器 | 是否创建详细传感器 | 否 | 否 |

5. 点击"提交"完成配置

> **提示**: 手机号码将由系统自动从 API 获取，无需手动配置。

## 📊 可用传感器

![设备信息与传感器](images/3.png)

### 基础传感器（始终创建）

| 翻译键 | 名称 | 单位 | 说明 |
|--------|------|------|------|
| `voice_usage` | 已用语音 | 分钟 | 已使用的语音时长 |
| `sms_usage` | 已用短信 | 条 | 已发送的短信数量 |
| `data_usage` | 已用流量(合计) | GB | 已使用的流量（排除无限流量包） |
| `balance` | 账户余额 | 元 | 当前可用余额 |

**实体 ID 示例**: 
- 未配置手机号：`sensor.ha_unicom_bill_voice_usage`
- API 获取到完整号码后：
  - 设备名称：`手机号码 （例如：12345678900）`
  - 实体 ID：`sensor.unicom_12345678900_voice_usage`

> **提示**: 
> - 系统会自动从 API 获取**完整手机号码**
> - 设备名称直接显示手机号码：`例如：12345678900`
> - 实体 ID 使用手机号码：`例如：sensor.unicom_12345678900_voice_usage`

### 详细传感器（可选）

启用"创建独立传感器"后额外创建：

#### 语音传感器
- `voice_total` - 语音总量（分钟）
- `voice_available` - 剩余语音（分钟）
- `voice_ratio` - 语音使用比例（%）

#### 短信传感器
- `sms_total` - 短信总量（条）
- `sms_available` - 剩余短信（条）
- `sms_ratio` - 短信使用比例（%）

#### 流量传感器（合计）

所有流量类型的汇总数据：

- `data_total` - 流量总量(合计)（GB）
- `data_available` - 剩余流量(合计)（GB）
- `data_exceed` - 超支流量（GB）
- `data_ratio` - 流量使用比例（%）
- `data_carried_over` - 上月转接流量（GB）

#### 流量传感器（按类型分类）

按联通流量类型 (flowType) 分别统计：

| 类型 | flowType | 说明 |
|------|----------|------|
| 通用 | 1 | 通用流量包 |
| 专属 | 2 | 专属/App 定向流量（自动排除无限流量包） |
| 其他 | 3 | 区域/公免等其它流量 |

**通用流量**
- `data_total_general` - 流量总量(通用)（GB）
- `data_available_general` - 剩余流量(通用)（GB）
- `data_usage_general` - 已用流量(通用)（GB）

**专属流量（App/定向流量）**
- `data_total_exclusive` - 流量总量(专属)（GB）
- `data_available_exclusive` - 剩余流量(专属)（GB）
- `data_usage_exclusive` - 已用流量(专属)（GB）

**其他流量（区域/公免等）**
- `data_total_other` - 流量总量(其他)（GB）
- `data_available_other` - 剩余流量(其他)（GB）
- `data_usage_other` - 已用流量(其他)（GB）

#### 账户传感器
- `real_fee` - 本月话费（元）
- `can_use_value` - 上月结余话费（元）
- `total_owed` - 账户欠费（元）

## 🃏 自定义 Lovelace 卡片

本集成内置了自定义 Lovelace 卡片 (`ha-unicom-card`)，安装后**自动注册**，无需手动添加 JS 资源。

### 效果预览

![自定义卡片 - 主视图](images/5.png)

![自定义卡片 - 详情面板](images/6.png)

### 使用方式

在 Dashboard 中手动添加卡片，类型选择 **"自定义: China Unicom Card"**：

```yaml
type: custom:ha-unicom-card
title: 中国联通
device_id: xxxxxxxx                    # 集成设备 ID（必填）
balance_warning_below: 20              # 余额预警阈值（元），低于此值显示警告
usage_warning_percent: 80              # 流量使用率警告阈值（%）
usage_danger_percent: 95               # 使用率危险阈值（%）
show_details: true                     # 是否拓展显示详情面板
```

![卡片可视化编辑器配置](images/7.png)

> 卡片会在 HA 启动时自动注册前端资源并持久化到 Lovelace storage，升级集成版本后资源 URL 会自动更新。

## 🔧 高级配置

### 修改配置

![选项配置](images/4.png)

1. 进入 设置 → 设备与服务
2. 找到"China Unicom Bill"集成
3. 点击"配置"
4. 可以修改：
   - OpenID（如果过期需要更新）
   - 刷新间隔（1-60 分钟）
   - 是否创建详细传感器
5. 保存

### 调试日志

在 `configuration.yaml` 中启用调试日志：

```yaml
logger:
  default: info
  logs:
    custom_components.ha_unicom_bill: debug
```

## 🐛 故障排除

### OpenID 过期

**症状**：日志显示 `Authentication error` 或返回错误码 1001

**解决**：
- 重新抓包获取并输入新的 OpenID

### 数据不更新

**检查**：
1. 查看 Home Assistant 日志
2. 确认网络连接正常
3. 检查刷新间隔设置

## 📝 开发说明

### 项目结构

```
ha_unicom_bill/
├── __init__.py         # 集成入口 & 前端卡片注册
├── api.py              # API 客户端
├── config_flow.py      # 配置流程
├── const.py            # 常量定义
├── coordinator.py      # 数据协调器
├── manifest.json       # 集成元数据
├── sensor.py           # 传感器实体
├── www/                # 前端资源（自定义 Lovelace 卡片）
│   ├── ha-unicom-card.js
│   └── logo.png
└── translations/
    └── zh-Hans.json    # 中文翻译
```

### 添加新传感器

1. 在 `const.py` 中定义传感器常量
2. 在 `sensor.py` 中创建传感器类，继承 `UnicomBaseSensor`
3. 实现 `native_value` 属性
4. 在 `async_setup_entry` 中注册传感器

### API 端点

| API | 说明 |
|-----|------|
| `/weixinNew/getTicket` | 获取 ticket |
| `/wx/serviceEntrance` | 获取 microHall Cookie |
| `/weixinNew/sspbigball` | 获取概览数据 |
| `/balancenew/accountBalancenew.htm` | 获取余额详情 |
| `/queryOcsPackageFlowLeftContentRevisedInJune` | 获取用量详情 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

- Bug 报告：[Issues](https://github.com/Cyborg2017/ha_unicom_bill/issues)
- 功能建议：[Discussions](https://github.com/Cyborg2017/ha_unicom_bill/discussions)

## 📄 许可

本项目采用 GPL-3.0 许可 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 参考项目：[homeassistant-unicom_bill_info](https://github.com/hlhk2017/homeassistant-unicom_bill_info)
- 原始版本：homeassistant-unicom_bill_info v1.0.8
- Home Assistant 社区
