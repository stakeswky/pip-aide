# Cloudflare Worker 部署指南

这个文档提供了将pip-aide服务部署到Cloudflare Workers的详细步骤，包括KV存储配置和环境变量设置。

## 准备工作

1. 注册并登录[Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 确保您有一个有效的Deepseek/OpenAI API密钥

## 部署步骤

### 1. 创建KV命名空间

1. 在Cloudflare Dashboard中点击**Workers & Pages**
2. 在侧边导航栏点击**KV**
3. 点击**创建命名空间**按钮
4. 输入命名空间名称(如`PIP_AIDE_LOGS`)并创建

### 2. 创建Worker

1. 在Workers & Pages部分点击**创建应用程序**
2. 选择**创建Worker**
3. 为Worker指定一个名称(如`pip-aide-api`)
4. 在编辑器中，删除默认代码
5. 粘贴`worker.js`的内容
6. 点击**保存并部署**

### 3. 配置Worker绑定和环境变量

1. 部署后，点击Worker名称进入详情页
2. 点击**设置**选项卡，然后选择**变量**

#### 绑定KV命名空间:

1. 在**KV命名空间绑定**部分点击**添加绑定**
2. 变量名称填写`LOGS_KV`(必须与代码中使用的名称匹配)
3. 选择之前创建的KV命名空间(如`PIP_AIDE_LOGS`)
4. 点击**添加绑定**保存

#### 配置环境变量:

1. 在**环境变量**部分点击**添加变量**
2. 添加以下变量:
   - 变量名: `API_KEY`, 值: 您的Deepseek/OpenAI API密钥
   - 变量名: `API_BASE`, 值: `https://api.deepseek.com/v1`(或您使用的其他API地址)
   - 变量名: `MODEL`, 值: `deepseek-chat`(或您想使用的其他模型)
3. 点击**保存**按钮

### 4. 设置自定义域名(可选)

如果您希望使用`api.pip-aide.com`域名:

1. 确保该域名已添加到您的Cloudflare账户
2. 在Worker详情页点击**触发器**选项卡
3. 在**自定义域**部分点击**添加自定义域**
4. 输入`api.pip-aide.com`
5. 按照向导完成DNS记录配置

## 测试部署

通过发送POST请求到您的Worker URL进行测试:

```bash
curl -X POST https://pip-aide-api.your-username.workers.dev/analyze_error \
  -H "Content-Type: application/json" \
  -d '{"machine_id":"test-machine", "error_context":"ERROR: Could not find a version that satisfies the requirement tensorflow"}'
```

如果配置了自定义域名:

```bash
curl -X POST https://api.pip-aide.com/analyze_error \
  -H "Content-Type: application/json" \
  -d '{"machine_id":"test-machine", "error_context":"ERROR: Could not find a version that satisfies the requirement tensorflow"}'
```

## 查看日志

1. 在Worker详情页点击**日志**选项卡查看请求日志
2. KV存储的日志可以通过以下方式查看:
   - 在Cloudflare Dashboard中进入**Workers & Pages** > **KV**
   - 选择您创建的命名空间
   - 使用搜索或浏览键值对

## 限制和注意事项

1. **免费计划限制**:
   - Worker: 每日10万请求
   - KV: 每日10万次读取, 1,000次写入, 1GB存储
   
2. **日志存储**:
   - 日志以`machineId:timestamp`格式存储在KV中
   - 当前实现不提供日志轮换或清理机制
   - 对于大规模部署，建议实现定期清理策略

3. **API限制**:
   - 确保您了解您所使用的AI服务的API限制和费用
   - 考虑实现额外的请求速率限制以控制API使用成本

4. **安全性**:
   - 环境变量(特别是API密钥)不会暴露给客户端
   - 考虑添加额外的认证机制以保护您的Worker端点
