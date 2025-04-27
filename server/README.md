# pip-aide 服务端

这是pip-aide的AI分析服务端组件，用于接收pip安装错误信息并提供修复建议。

## 安装

1. 安装依赖:
```bash
pip install -r requirements.txt
```

## 配置

服务端支持以下环境变量配置:

- `DEEPSEEK_API_KEY`: Deepseek/OpenAI API密钥（必需）
- `OPENAI_API_BASE`: API基础地址（默认为 https://api.deepseek.com/v1）
- `OPENAI_MODEL`: 模型名称（默认为 deepseek-chat）

可以通过创建`.env`文件或设置系统环境变量来配置:

```
# .env 文件示例
DEEPSEEK_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

## 运行服务

```bash
python pipai_server.py
```

服务默认在 0.0.0.0:8000 端口监听，可以通过修改代码调整端口和监听地址。

## API 接口

### 分析错误并提供建议

**端点**: `/analyze_error` (POST)

**请求体**:
```json
{
  "machine_id": "唯一机器标识",
  "error_context": "pip错误日志内容"
}
```

**返回**:
```json
{
  "suggestion": "推荐的pip修复命令或'UNCERTAIN'"
}
```

## 日志

服务会自动在`pipai_logs`目录下记录请求日志，以请求的`machine_id`命名。
