# BTC Options Monitor 使用指南

## 快速开始

### 1. 安装

```bash
# 克隆仓库
git clone https://github.com/wubin19920612/quant_1.git
cd btc-options-monitor

# 安装依赖
pip install -r requirements.txt

# 开发环境（可选）
pip install -r requirements-dev.txt
```

### 2. 配置

复制配置模板并编辑：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：

```yaml
exchanges:
  deribit:
    enabled: true
    ws_url: "wss://www.deribit.com/ws/api/v2"
  okx:
    enabled: true
    ws_url: "wss://ws.okx.com:8443/ws/v5/public"

symbol: BTC
refresh_interval: 2  # UI 刷新间隔（秒）

rv_windows: [7, 14, 30]  # RV 计算窗口（天）
risk_free_rate: 0.05     # 无风险利率

regime:
  lookback_days: 90      # 制度检测回溯天数
  low_z: -1.0            # 低波动阈值（Z-score）
  high_z: 1.0            # 高波动阈值
  crisis_z: 2.0          # 危机阈值
  history_limit: 1000    # DVOL 历史记录上限

alerts:
  iv_rv_ratio_high: 1.5       # IV/RV 高估阈值
  iv_rv_ratio_low: 0.5        # IV/RV 低估阈值
  iv_spike_pct: 0.20          # IV spike 触发阈值（20%）
  iv_spike_window_min: 30     # spike 检测窗口（分钟）
  cross_exchange_iv_diff: 0.05  # 跨交易所 IV 差异阈值
  cooldown_min: 5             # 告警冷却时间（分钟）
  telegram:
    enabled: false
    bot_token: ""             # Telegram Bot Token
    chat_id: ""               # Telegram Chat ID
```

### 3. 启动

```bash
# 方式 1：使用模块方式
python -m src.main

# 方式 2：直接运行
python src/main.py

# 方式 3：使用安装的命令（需先 pip install -e .）
btc-monitor
```

## 界面说明

### 主界面布局

启动后会看到终端 TUI 界面，包含以下面板：

```
┌─────────────────────────────────────────────────────────┐
│  BTC Options Monitor                                    │
├─────────────────────────────────────────────────────────┤
│  [F1] IV/RV 对比  [F2] 波动率微笑  [F3] 期限结构      │
│  [F4] 告警日志    [F5] 波动率制度  [F6] 策略推荐      │
│  [Q] 退出                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  当前面板内容区域                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 快捷键

| 按键 | 功能 | 说明 |
|------|------|------|
| **F1** | IV/RV 对比面板 | 显示所有期权的 IV 与 RV 对比数据 |
| **F2** | 波动率微笑 | 可视化不同行权价的 IV 分布曲线 |
| **F3** | 期限结构 | 展示不同到期日的 ATM IV 曲线 |
| **F4** | 告警日志 | 查看历史告警记录 |
| **F5** | 波动率制度 | 显示当前市场波动率状态 |
| **F6** | 策略推荐 | 基于当前制度推荐期权策略 |
| **Q** | 退出程序 | 安全关闭所有连接并退出 |

## 功能详解

### 1. IV/RV 对比面板（F1）

显示实时期权数据表格：

| 列名 | 说明 |
|------|------|
| Exchange | 交易所（Deribit/OKX） |
| Expiry | 到期日 |
| Strike | 行权价 |
| Type | 期权类型（Call/Put） |
| IV | 隐含波动率（%） |
| RV 7d/14d/30d | 7/14/30 天已实现波动率（%） |
| Ratio | IV/RV 比值 |
| Signal | 交易信号（STRONG_BUY/WEAK_BUY/NEUTRAL/WEAK_SELL/STRONG_SELL） |

**使用场景**：
- 快速识别 IV 高估/低估的期权
- 对比不同到期日和行权价的 IV 水平
- 发现跨交易所套利机会

### 2. 波动率微笑（F2）

绘制 IV 随行权价变化的曲线图。

**特征**：
- **正常微笑**：两端 IV 高于 ATM
- **偏斜**：Put 端 IV 显著高于 Call 端（市场恐慌）
- **平坦**：IV 分布均匀（市场平静）

**使用场景**：
- 识别市场情绪（恐慌/贪婪）
- 选择合适的行权价进行期权交易
- 发现定价异常的期权

### 3. 期限结构（F3）

展示 ATM IV 随到期时间的变化。

**形态**：
- **正向**：远期 IV > 近期 IV（正常状态）
- **倒挂**：近期 IV > 远期 IV（市场紧张）
- **驼峰**：中期 IV 最高（特定事件预期）

**使用场景**：
- 判断市场对未来波动率的预期
- 选择合适的到期日
- 日历价差策略选择

### 4. 告警日志（F4）

实时显示触发的告警事件：

**告警类型**：
- **IV/RV 比值异常**：IV 显著高于或低于 RV
- **IV Spike**：IV 短期内剧烈上涨（>20%）
- **跨交易所价差**：Deribit 与 OKX 的 IV 差异超过阈值
- **制度切换**：波动率制度发生变化

**字段说明**：
- **时间**：告警触发时间
- **级别**：high/medium/low
- **规则**：触发的告警规则
- **标的**：期权合约名称
- **消息**：详细描述

### 5. 波动率制度（F5）

显示当前市场波动率状态：

**四种制度**：
- **LOW**：低波动（DVOL Z-score < -1.0）
  - 市场平静，适合卖出期权
- **NORMAL**：正常波动（-1.0 ≤ Z-score ≤ 1.0）
  - 常规交易环境
- **HIGH**：高波动（1.0 < Z-score ≤ 2.0）
  - 市场活跃，波动加大
- **CRISIS**：危机模式（Z-score > 2.0）
  - 极端波动，风险管理优先

**显示内容**：
- 当前制度状态
- DVOL 当前值
- DVOL 90 天均值和标准差
- Z-score 值
- 制度持续时间

### 6. 策略推荐（F6）

基于当前制度和 IV Rank 推荐期权策略。

**策略矩阵**：

| 制度 | IV Rank | 推荐策略 | 说明 |
|------|---------|----------|------|
| LOW | 低 | 卖出跨式/宽跨式 | 赚取时间价值 |
| LOW | 高 | 卖出垂直价差 | 控制风险的卖方策略 |
| NORMAL | 低 | 买入跨式 | 等待波动率上升 |
| NORMAL | 中 | 铁鹰式 | 区间震荡策略 |
| NORMAL | 高 | 卖出跨式 | IV 回归均值 |
| HIGH | 低 | 买入跨式/宽跨式 | 捕捉大幅波动 |
| HIGH | 高 | 观望 | 等待 IV 回落 |
| CRISIS | 任意 | 保护性策略 | 买入 Put 保护 |

**显示内容**：
- 当前制度
- IV Rank 百分位
- 推荐策略列表
- 每个策略的适用条件和风险提示

## 高级配置

### Telegram 通知

1. 创建 Telegram Bot：
   - 在 Telegram 中搜索 @BotFather
   - 发送 `/newbot` 创建新 bot
   - 获取 Bot Token

2. 获取 Chat ID：
   - 在 Telegram 中搜索 @userinfobot
   - 发送任意消息获取你的 Chat ID

3. 配置 `config.yaml`：
```yaml
alerts:
  telegram:
    enabled: true
    bot_token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    chat_id: "123456789"
```

### 调整告警阈值

根据交易风格调整告警灵敏度：

```yaml
alerts:
  # 保守型：更宽松的阈值，减少噪音
  iv_rv_ratio_high: 2.0
  iv_rv_ratio_low: 0.4
  iv_spike_pct: 0.30

  # 激进型：更严格的阈值，捕捉更多机会
  iv_rv_ratio_high: 1.3
  iv_rv_ratio_low: 0.6
  iv_spike_pct: 0.15
```

### 自定义 RV 窗口

```yaml
# 短期交易者
rv_windows: [3, 7, 14]

# 长期投资者
rv_windows: [14, 30, 60]

# 多时间框架分析
rv_windows: [7, 14, 30, 60, 90]
```

## 数据存储

程序会在 `data/` 目录下创建 SQLite 数据库：

```
data/
└── monitor.db
```

**存储内容**：
- 期权 ticker 数据
- OHLC 蜡烛图数据
- DVOL 历史记录
- 波动率制度日志
- 告警事件记录

**数据保留**：
- 默认保留所有历史数据
- 可手动删除 `data/monitor.db` 重新开始

## 故障排查

### 连接失败

**问题**：无法连接到交易所 WebSocket

**解决**：
1. 检查网络连接
2. 确认交易所 API 可访问
3. 检查 `config.yaml` 中的 `ws_url` 是否正确
4. 尝试禁用其中一个交易所：
```yaml
exchanges:
  okx:
    enabled: false  # 暂时禁用 OKX
```

### 数据不更新

**问题**：界面显示但数据不刷新

**解决**：
1. 检查终端是否有错误日志
2. 确认交易所 WebSocket 连接正常
3. 尝试增加 `refresh_interval`：
```yaml
refresh_interval: 5  # 增加到 5 秒
```

### IV 计算失败

**问题**：某些期权的 IV 显示为空

**原因**：
- 期权价格过低（深度虚值）
- 到期时间过短
- 市场流动性不足

**正常现象**，不影响其他期权的监控。

### 内存占用过高

**问题**：长时间运行后内存占用增加

**解决**：
1. 限制 DVOL 历史记录：
```yaml
regime:
  history_limit: 500  # 减少到 500 条
```

2. 定期重启程序（建议每 24 小时）

## 性能优化

### 减少 CPU 占用

```yaml
# 降低刷新频率
refresh_interval: 5

# 减少 RV 窗口数量
rv_windows: [7, 30]
```

### 减少网络流量

```yaml
# 只启用一个交易所
exchanges:
  deribit:
    enabled: true
  okx:
    enabled: false
```

## 最佳实践

### 日常监控流程

1. **启动程序**：`python -m src.main`
2. **查看制度**（F5）：了解当前市场状态
3. **查看策略**（F6）：获取交易建议
4. **筛选机会**（F1）：在 IV/RV 对比表中寻找信号
5. **分析结构**（F2/F3）：确认波动率结构合理性
6. **监控告警**（F4）：关注实时告警

### 交易决策辅助

1. **卖方策略**：
   - 制度：LOW 或 NORMAL
   - IV Rank > 50%
   - IV/RV Ratio > 1.5
   - 波动率微笑正常

2. **买方策略**：
   - 制度：NORMAL 或 HIGH
   - IV Rank < 30%
   - IV/RV Ratio < 0.7
   - 期限结构倒挂

3. **套利机会**：
   - 跨交易所 IV 差异 > 5%
   - 同一到期日不同行权价 IV 异常
   - 波动率微笑出现扭曲

## 注意事项

⚠️ **重要提示**：

1. **本工具仅供参考**，不构成投资建议
2. **期权交易风险极高**，请充分了解风险后再交易
3. **数据可能延迟**，实际交易前请确认最新价格
4. **IV 计算基于 BSM 模型**，实际市场可能存在偏差
5. **策略推荐是通用建议**，需结合个人风险承受能力调整

## 技术支持

- **GitHub Issues**：https://github.com/wubin19920612/quant_1/issues
- **文档**：查看 `README.md` 了解架构细节
- **测试**：运行 `pytest tests -v` 验证功能

## 更新日志

查看 Git 提交历史：
```bash
git log --oneline
```

## 许可证

查看 `LICENSE` 文件（如有）。
