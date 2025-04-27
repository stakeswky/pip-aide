# pip-aide

AI驱动的pip安装助手，自动分析pip安装失败原因并提供安全修复建议。

## 安装
```bash
pip install pip-aide
```

## 使用方法
```bash
pip-aide install <包名> [其他pip参数]
```

## 配置

pip-aide 支持多种配置方式，优先级如下：命令行参数 > 环境变量 > 配置文件 > 默认值。

- 配置文件支持：
  - `~/.config/pip-aide/pip-aide.conf`
  - `~/.config/pip/pip.conf`
  - `~/.pip/pip.conf`
  - 项目目录下 `pip.conf`
- 支持的配置项：
  - `server_url`：AI 服务端地址
  - `auto_confirm`：自动确认修复命令（true/false）
  - `analytics`：是否参与数据分析（on/off/ask）
  - `lang`：界面语言（zh/en）
  - `loglevel`：日志级别（INFO/DEBUG等）
  - `timeout`：AI请求超时时间（秒）

**示例 pip-aide.conf：**
```ini
[pip-aide]
server_url = https://your-ai-server.com/analyze_error
auto_confirm = false
analytics = ask
lang = zh
loglevel = INFO
timeout = 30
```

## 命令行参数
可通过命令行临时覆盖配置：
```bash
pip-aide install <包名> --server-url=https://your-ai-server.com/analyze_error --auto-confirm --lang=zh
```

## 环境变量
- `PIP_AIDE_AUTO_CONFIRM=true` 启用自动确认安全修复命令（无需人工确认，适合CI/CD）
- `LANG=zh_CN.UTF-8` 强制中文提示

## 主要特性
- 支持中英文提示，自动检测系统语言
- pip 安装失败时自动调用远程AI服务，分析并返回修复建议
- 只自动执行安全的pip相关命令，不会执行危险/系统指令
- 支持自动和手动确认两种修复模式
- 记录错误日志，便于后续追踪和统计

## 服务端用法

pip-aide 的 AI 服务端基于 FastAPI 实现，部署简单。

### 运行服务端
1. 安装依赖：
```bash
pip install fastapi uvicorn pydantic python-dotenv requests
```
2. 启动服务：
```bash
python pipai_server.py
```
默认监听 0.0.0.0:8000。

### 主要环境变量
- `DEEPSEEK_API_KEY`：OpenAI/Deepseek API Key
- `OPENAI_API_BASE`：API 基础地址（可选）
- `OPENAI_MODEL`：模型名称（可选）

### 接口说明
- POST `/analyze_error`：
  - 请求体：
    ```json
    {
      "machine_id": "唯一机器标识",
      "error_context": "pip 错误日志"
    }
    ```
  - 返回：AI建议的 pip 修复命令（或 "UNCERTAIN"）

## 依赖
- requests
- setuptools
- wheel

## 贡献
欢迎提交 issue 和 PR。如有建议请联系作者：不做了睡大觉 <stakeswky@gmail.com>

## LICENSE
MIT
