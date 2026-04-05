# BTC Options Monitor

实时监控 BTC 期权隐含波动率（IV）与已实现波动率（RV），支持 Deribit 和 OKX 交易所。

## 功能

- **IV/RV 对比**: 实时计算 7/14/30 天 RV，对比期权 IV，识别高估/低估
- **波动率微笑**: 可视化不同行权价的 IV 分布
- **期限结构**: 展示不同到期日的 ATM IV 曲线
- **波动率制度检测**: 基于 Deribit DVOL 指数自动识别 LOW/NORMAL/HIGH/CRISIS 四种市场状态
- **策略推荐**: 根据当前制度和 IV Rank 推荐期权策略
- **多维度告警**:
  - IV/RV 比值异常（高估/低估）
  - IV 短期剧烈波动（spike 检测）
  - 跨交易所 IV 价差套利机会
  - 波动率制度切换（如 NORMAL → HIGH）
- **Telegram 通知**: 可选推送告警到 Telegram Bot
- **SQLite 存储**: 持久化 ticker、OHLC、DVOL、制度历史

## 安装

```bash
# 克隆仓库
git clone <repo-url>
cd btc-options-monitor

# 安装依赖
pip install -r requirements.txt
```

## 使用

```bash
# 启动 TUI
python -m src.main

# 或直接运行
python src/main.py
```

📖 **详细使用说明请查看 [USAGE.md](USAGE.md)**

## 配置

编辑 `config.yaml`:

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
risk_free_rate: 0.05

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

## 快捷键

| 按键 | 功能 |
|------|------|
| F1 | IV/RV 对比面板 |
| F2 | 波动率微笑 |
| F3 | 期限结构 |
| F4 | 告警日志 |
| F5 | 波动率制度 |
| F6 | 策略推荐 |
| Q | 退出 |

## 架构

```
src/
├── models.py              # 数据模型（OptionTicker, AlertEvent, Regime 等）
├── storage/
│   └── db.py             # SQLite 异步存储
├── analytics/
│   ├── iv_calculator.py  # Black-Scholes IV 计算
│   ├── rv_calculator.py  # 已实现波动率（Yang-Zhang, Parkinson）
│   ├── scorer.py         # IV/RV 偏离度评分
│   ├── alerts.py         # 告警引擎
│   ├── regime_detector.py  # 波动率制度检测
│   └── strategy_advisor.py # 策略推荐
├── exchanges/
│   ├── base.py           # 交易所基类
│   ├── deribit.py        # Deribit WebSocket 适配器
│   └── okx.py            # OKX WebSocket 适配器
├── notifications/
│   └── telegram.py       # Telegram 通知
├── ui/
│   ├── dashboard.py      # IV/RV 对比面板
│   ├── vol_smile.py      # 波动率微笑图表
│   ├── term_structure.py # 期限结构图表
│   ├── alert_log.py      # 告警日志面板
│   ├── regime_panel.py   # 制度显示面板
│   └── strategy_panel.py # 策略推荐面板
├── app.py                # Textual 主应用
└── main.py               # CLI 入口
```

## 测试

```bash
# 运行所有测试
pytest tests -v

# 运行特定测试
pytest tests/test_alerts.py -v
pytest tests/test_regime_detector.py -v

# 查看覆盖率
pytest tests --cov=src --cov-report=html
```

## 依赖

- Python 3.10+
- textual: TUI 框架
- textual-plotext: 终端图表
- websockets: WebSocket 客户端
- aiosqlite: 异步 SQLite
- scipy: 数值计算（IV 求解）
- numpy: 数组运算
- pyyaml: 配置解析
- httpx: HTTP 客户端（Telegram）

## License

MIT
