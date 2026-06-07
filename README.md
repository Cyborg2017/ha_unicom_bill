# 中国联通话费查询 (ha_unicom_bill)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/hlhk2017/homeassistant-unicom_bill_info.svg)](https://GitHub.com/hlhk2017/homeassistant-unicom_bill_info/releases/)
[![License](https://img.shields.io/github/license/hlhk2017/homeassistant-unicom_bill_info.svg)](LICENSE)

Home Assistant 自定义集成，用于查询中国联通话费、流量、语音等信息。

## ✨ 特性

- 📊 **16个传感器**：全面覆盖语音、短信、流量、余额信息
- 🔄 **自动更新**：可配置刷新间隔（1-60分钟）
- 🔐 **自动认证**：自动获取 ticket 和 Cookie，无需手动配置
- 🎨 **UI配置**：通过 Home Assistant 界面轻松配置
- 📱 **微信小程序**：基于联通微信小程序 API
- 🏗️ **模块化设计**：清晰的代码架构，易于维护和扩展

## 📦 安装

### 方法1: HACS（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 进入 HACS → 集成 → 点击右上角三个点 → 自定义仓库
3. 添加仓库：`https://github.com/hlhk2017/homeassistant-unicom_bill_info`
4. 分类选择：`Integration`
5. 点击"添加"
6. 搜索"中国联通话费查询"并安装
7. 重启 Home Assistant

### 方法2: 手动安装

1. 下载或克隆本仓库
2. 复制 `custom_components/ha_unicom_bill` 文件夹到 HA 的 `custom_components` 目录
3. 重启 Home Assistant
4. 在集成页面搜索"中国联通话费查询"并添加

## ⚙️ 配置

### 获取 OpenID

OpenID 是微信用户的唯一标识，需要从联通小程序中获取：

#### 方法1: 微信开发者工具

1. 下载并安装[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 导入联通小程序（AppID: wx56af9763578b9a93）
3. 打开调试器 → Network 面板
4. 打开小程序，找到 `getTicket` 请求
5. 查看请求体（Request Payload）
6. 复制 `openId` 字段的值

#### 方法2: 抓包工具（Charles/Fiddler）

1. 安装 Charles 或 Fiddler
2. 配置手机代理，使流量经过电脑
3. 安装并信任证书
4. 打开联通小程序
5. 捕获 HTTPS 请求
6. 找到 `https://mina.10010.com/wxapplet/weixinNew/getTicket` 请求
7. 从请求体中提取 `openId`

### 配置步骤

1. 进入 Home Assistant → 设置 → 设备与服务
2. 点击右下角"添加集成"
3. 搜索"中国联通话费查询"
4. 填写配置表单：

| 字段 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| 名称 | 设备显示名称 | 是 | 联通数据 |
| OpenID | 从抓包获取的 OpenID | 是 | - |
| 刷新间隔 | 数据更新频率（分钟） | 是 | 15 |
| 创建独立传感器 | 是否创建详细传感器 | 否 | 否 |

5. 点击"提交"完成配置

## 📊 可用传感器

### 基础传感器（始终创建）

| 实体ID | 名称 | 单位 | 说明 |
|--------|------|------|------|
| `sensor.{name}_voice_usage` | 语音用量 | 分钟 | 已使用的语音时长 |
| `sensor.{name}_sms_usage` | 短信用量 | 条 | 已发送的短信数量 |
| `sensor.{name}_data_usage` | 流量用量 | GB/MB | 已使用的流量 |
| `sensor.{name}_balance` | 余额 | 元 | 当前可用余额 |

### 详细传感器（可选）

启用"创建独立传感器"后额外创建：

#### 语音传感器
- `sensor.{name}_voice_total` - 语音总量（分钟）
- `sensor.{name}_voice_available` - 语音可用（分钟）
- `sensor.{name}_voice_ratio` - 语音使用比例（%）

#### 短信传感器
- `sensor.{name}_sms_total` - 短信总量（条）
- `sensor.{name}_sms_available` - 短信可用（条）

#### 流量传感器
- `sensor.{name}_data_total` - 流量总量（GB/MB）
- `sensor.{name}_data_available` - 流量可用（GB/MB）
- `sensor.{name}_data_exceed` - 流量超出（GB/MB）
- `sensor.{name}_data_ratio` - 流量使用比例（%）

#### 账户传感器
- `sensor.{name}_real_fee` - 实时话费（元）
- `sensor.{name}_can_use_value` - 可用赠款（元）
- `sensor.{name}_credit_value` - 信用额度（元）
- `sensor.{name}_total_owed` - 总欠费（元）

## 🔧 高级配置

### 修改刷新间隔

1. 进入 设置 → 设备与服务
2. 找到"中国联通话费查询"集成
3. 点击"配置"
4. 修改"刷新间隔"
5. 保存

### 启用/禁用详细传感器

1. 删除现有集成实例
2. 重新添加集成
3. 勾选"创建独立传感器"

## 🐛 故障排除

### OpenID 过期

**症状**：日志显示 `Authentication error` 或返回错误码 1001

**解决**：
1. 重新抓包获取新的 OpenID
2. 在集成选项中更新 OpenID

### 部分传感器显示 unknown

**原因**：
- 某些套餐可能没有短信功能
- 概览接口不提供完整数据

**解决**：
- 检查用量详情接口是否返回数据
- 确认套餐类型支持相应功能

### 数据不更新

**检查**：
1. 查看 Home Assistant 日志
2. 确认网络连接正常
3. 检查刷新间隔设置

**解决**：
```yaml
# 启用调试日志
logger:
  default: info
  logs:
    custom_components.ha_unicom_bill: debug
```

## 📝 开发说明

### 项目结构

```
ha_unicom_bill/
├── __init__.py          # 集成入口
├── api.py              # API 客户端
├── config_flow.py      # 配置流程
├── const.py            # 常量定义
├── coordinator.py      # 数据协调器
├── manifest.json       # 集成元数据
├── sensor.py           # 传感器实体
└── translations/
    └── zh-Hans.json   # 中文翻译
```

### 添加新传感器

1. 在 `const.py` 中定义传感器常量
2. 在 `sensor.py` 中创建传感器类，继承 `UnicomBaseSensor`
3. 实现 `native_value` 属性
4. 在 `async_setup_entry` 中注册传感器

### API 端点

| API | 说明 |
|-----|------|
| `/weixinNew/getTicket` | 获取临时 ticket |
| `/wx/serviceEntrance` | 获取 microHall Cookie |
| `/weixinNew/sspbigball` | 获取概览数据 |
| `/balancenew/accountBalancenew.htm` | 获取余额详情 |
| `/queryOcsPackageFlowLeftContentRevisedInJune` | 获取用量详情 |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

- Bug 报告：[Issues](https://github.com/hlhk2017/homeassistant-unicom_bill_info/issues)
- 功能建议：[Discussions](https://github.com/hlhk2017/homeassistant-unicom_bill_info/discussions)

## 📄 许可证

本项目采用 GPL-3.0 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 参考项目：[ha_hfwater](https://github.com/Cyborg2017/ha_hfwater)
- 原始版本：homeassistant-unicom_bill_info v1.x
- Home Assistant 社区

## 📞 联系方式

- GitHub: [@hlhk2017](https://github.com/hlhk2017)
- 项目主页: https://github.com/hlhk2017/homeassistant-unicom_bill_info

---

**版本**: 2.0.0  
**最后更新**: 2026-06-06  
**兼容版本**: Home Assistant 2023.1.0+
