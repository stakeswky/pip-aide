// pip-aide API服务 - Cloudflare Workers版本

// 环境变量配置说明：
// 在Cloudflare Workers控制台配置以下环境变量:
// API_KEY: Deepseek/OpenAI API密钥
// API_BASE: API基础URL (默认: https://api.deepseek.com/v1)
// MODEL: 模型名称 (默认: deepseek-chat)
//
// KV绑定配置说明：
// 需要在Cloudflare Workers控制台创建一个KV命名空间，如 "PIP_AIDE_LOGS"
// 然后在Worker设置中绑定到 LOGS_KV

export default {
  async fetch(request, env, ctx) {
    // 处理CORS预检请求
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    const url = new URL(request.url);
    
    // 主分析端点
    if (url.pathname === '/analyze_error' && request.method === 'POST') {
      return await handleAnalyzeRequest(request, env, ctx);
    }
    
    // 其他请求返回简单提示
    return new Response('pip-aide API service is running. Use POST /analyze_error to analyze pip errors.', {
      headers: { 'Content-Type': 'text/plain' }
    });
  }
};

// 处理CORS预检请求
function handleCORS() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400',
    },
  });
}

// 处理分析请求
async function handleAnalyzeRequest(request, env, ctx) {
  // 解析请求体
  let data;
  try {
    data = await request.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }

  // 验证请求参数
  if (!data.machine_id || !data.error_context) {
    return new Response(JSON.stringify({ error: 'Missing required fields' }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }

  const requestId = crypto.randomUUID();
  console.log(`[${requestId}] Received request for machine_id: ${data.machine_id}`);

  // 将日志存储到KV (使用"等待失败"模式)
  ctx.waitUntil(storeLog(env, data.machine_id, data.error_context, requestId));

  // 尝试分析错误并获取建议
  try {
    const suggestion = await getAISuggestion(data.error_context, requestId, env);
    console.log(`[${requestId}] Returning suggestion to client`);
    
    return new Response(JSON.stringify({ suggestion }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error) {
    console.error(`[${requestId}] Error analyzing error: ${error.message}`);
    
    return new Response(JSON.stringify({ 
      suggestion: `UNCERTAIN (Error: ${error.message})` 
    }), {
      status: 200, // 仍然返回200以便客户端能够获取错误信息
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
}

// 将日志存储到KV
async function storeLog(env, machineId, errorContext, requestId) {
  try {
    if (!env.LOGS_KV) {
      console.warn(`[${requestId}] LOGS_KV not bound, cannot store logs`);
      return;
    }

    const timestamp = new Date().toISOString();
    const logKey = `${machineId}:${timestamp}`;
    
    const logEntry = JSON.stringify({
      timestamp,
      machine_id: machineId,
      error_context: errorContext,
      request_id: requestId
    });
    
    // 存储日志到KV
    await env.LOGS_KV.put(logKey, logEntry);
    console.log(`[${requestId}] Log stored with key: ${logKey}`);
    
    // 还可以选择维护一个机器ID的索引列表，但这里简化处理
  } catch (error) {
    console.error(`[${requestId}] Failed to store log: ${error.message}`);
  }
}

// 调用AI API获取建议
async function getAISuggestion(errorContext, requestId, env) {
  const apiKey = env.API_KEY || '';
  if (!apiKey) {
    console.error(`[${requestId}] No API key configured`);
    return 'UNCERTAIN (No API key configured)';
  }

  const apiBase = env.API_BASE || 'https://api.deepseek.com/v1';
  const model = env.MODEL || 'deepseek-chat';
  
  console.log(`[${requestId}] Calling AI API: ${apiBase}/chat/completions with model ${model}`);

  const prompt = `
You are an expert Python package installation troubleshooter.
The user encountered an error trying to install a Python package using pip.
The information below includes both the error log AND system information.

${errorContext}

Please analyze this error carefully, considering the Python version, system information, and pip version.
Pay special attention to:
1. Version compatibility issues between the package and Python version
2. Architecture compatibility issues (32-bit vs 64-bit)
3. Operating system specific requirements
4. Missing system dependencies that might be indicated by the error

Focus ONLY on \`pip install ...\` commands or \`python -m pip install ...\` commands. For example, suggest:
- Upgrading pip/setuptools/wheel
- Installing specific versions compatible with the user's Python version
- Using appropriate flags (--no-cache-dir, --no-binary, etc.)
- Installing missing Python dependencies available on PyPI

Do NOT suggest system package manager commands (apt, yum, brew, etc.) or commands requiring sudo.
Do NOT suggest commands that modify files or environment variables.

Format EACH suggested command clearly on its own line, enclosed in triple backticks. Example:
\`\`\`
pip install --upgrade setuptools wheel
\`\`\`
\`\`\`
pip install some-package==1.2.3
\`\`\`

If you are absolutely certain no simple \`pip\` command can fix this (e.g., it's clearly a compiler issue needing system libraries, or a typo in a requirements file like \`requirments.txt: misspelled-package==1.0\`), respond ONLY with the word "UNCERTAIN".
`;

  try {
    const response = await fetch(`${apiBase}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model,
        messages: [
          { role: "system", content: "You are an expert Python package installation troubleshooter focused ONLY on pip command solutions." },
          { role: "user", content: prompt }
        ],
        temperature: 0.6,
        max_tokens: 150
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[${requestId}] AI API error: ${response.status} ${errorText}`);
      return `UNCERTAIN (API error ${response.status})`;
    }

    const data = await response.json();
    const suggestion = data.choices[0].message.content.trim();
    console.log(`[${requestId}] AI suggestion obtained`);
    
    return suggestion;
  } catch (error) {
    console.error(`[${requestId}] Error calling AI API: ${error.message}`);
    return `UNCERTAIN (Error: ${error.message})`;
  }
}
