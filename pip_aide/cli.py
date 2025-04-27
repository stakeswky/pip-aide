import sys
import os
import re
import signal
import time
import threading
import locale
import uuid
import requests
import argparse
import configparser
import subprocess
import shlex
import logging
from urllib.parse import urlparse, urlunparse
from urllib.error import URLError
from http.client import HTTPException

default_messages = {
    'en': {
        'usage': "Usage: pip-aide install <package_name> [other pip options]",
        'info': 'Info',
        'language_info': 'Language setting',
        'timeout_info': 'Timeout setting',
        'autoconfirm_enabled': 'Auto-confirm mode is ENABLED.',
        'autoconfirm_disabled': 'Auto-confirm mode is DISABLED.',
        'analytics_on': 'Anonymous usage statistics enabled.',
        'analytics_off': 'Anonymous usage statistics disabled.',
        'analytics_ask': 'Will ask about sending anonymous usage statistics.',
        'install_success': "\n[pip-aide] Installation successful!",
        'install_fail': "\n[pip-aide] Installation failed.",
        'ai_suggestion_is': "[pip-aide] AI Suggestion:\n{suggestion}",
        'ai_uncertain': "[pip-aide] AI is uncertain or provided no suitable pip command fix.",
        'ai_call_fail': "[pip-aide Error] Failed to call AI API: {e}",
        'get_ai_suggestion_fail': "[pip-aide] Could not get valid suggestion from AI.",
        'filter_start': "Filtering suggested commands for safety...",
        'filter_checking': "Checking: '{cmd}'",
        'filter_rejected_disallowed': "    Rejected: Contains disallowed substring ({subs}).",
        'filter_accepted': "Accepted: Matches safe pattern '{pattern}'.",
        'filter_rejected_no_match': "[pip-aide Warning] Suggested command rejected: Does not match allowed patterns.",
        'filter_no_safe_commands': "[pip-aide Error] No safe commands found in the suggestion.",
        'parse_safe_commands_fail': "[pip-aide Error] Failed to parse safe commands from AI suggestion.",
        'proposing_command': "[pip-aide] Proposed fix command: {cmd}",
        'confirm_prompt': "Execute this command? [y/N]: ",
        'executing_command': "[pip-aide Info] Executing command...",
        'command_success': "Command '{cmd}' executed successfully.",
        'command_fail': "[pip-aide Error] Command '{cmd}' failed with code {code}.",
        'fix_not_applied': "[pip-aide] Fix was not applied (failed, skipped, or no safe commands). Stopping.",
        'fix_attempted_retrying': "[pip-aide] Fix attempted. Retrying installation...",
        'invalid_lang_warning': "Invalid language '{specified}' specified or detected. Defaulting to 'en'.",
        'invalid_timeout_warning': "Invalid timeout value '{specified}'. Using default 30 seconds.",
        'no_suggestion': "[pip-aide] No suggestion provided by AI.",
        'skipping_execution_user': "[pip-aide] Skipping execution due to user input.",
        'confirm': 'Confirm',
        'fix_attempted': '[pip-aide] Fix commands attempted.',
        'fix_not_applied_or_failed': '[pip-aide] Fix commands were not applied (either skipped by user or failed).',
        'fixed_file_created': '[pip-aide] Created fixed requirements file: {filename}',
        'network_error': "[pip-aide Error] Network error when connecting to AI service: {error}",
        'server_error': "[pip-aide Error] Server error from AI service: {status_code}",
        'json_error': "[pip-aide Error] Failed to parse AI service response: {error}",
        'invalid_server_url': "[pip-aide Error] Invalid server URL: {url}",
        'retrying_ai_connection': "[pip-aide] Retrying AI connection attempt {attempt}/{max_retries}...",
        'ai_service_unavailable': "[pip-aide Error] AI service unavailable at {url}. Please check the server URL and try again.",
        'missing_package_name': "[pip-aide Error] No package name or options provided. Please specify a package to install.",
    },
    'zh': {
        'usage': "用法: pip-aide install <包名> [其他 pip 选项]",
        'info': '信息',
        'language_info': '语言设置',
        'timeout_info': '超时设置',
        'autoconfirm_enabled': '自动确认模式已启用。',
        'autoconfirm_disabled': '自动确认模式已禁用。',
        'analytics_on': '匿名使用统计已启用。',
        'analytics_off': '匿名使用统计已禁用。',
        'analytics_ask': '将询问是否发送匿名使用统计。',
        'install_success': '[pip-aide] 安装成功。',
        'install_fail': '[pip-aide] 安装失败。',
        'proposing_command': '[pip-aide] 建议的修复命令：{cmd}',
        'confirm_prompt': '执行此命令? [y/N]: ',
        'skipping_execution_user': '[pip-aide] 用户选择跳过执行。',
        'executing_command': '[pip-aide 信息] 正在执行命令...',
        'command_success': '[pip-aide] 命令执行成功。',
        'command_fail': '[pip-aide 错误] 命令执行失败，代码 {code}。',
        'cmd_success': '命令执行成功。',
        'cmd_fail': '命令执行失败，代码 {code}。',
        'cmd_exception': '命令执行异常：{error}',
        'filter_start': '正在过滤建议的命令以确保安全...',
        'filter_checking': '正在检查：{cmd}',
        'filter_accepted': '已接受：匹配安全模式 {pattern}。',
        'filter_rejected_disallowed': '拒绝：包含不安全片段：{subs}',
        'filter_rejected_no_match': '拒绝：不匹配允许的命令模式。',
        'filter_no_safe_commands': '未找到任何安全的修复命令。',
        'parse_safe_commands_fail': '[pip-aide] 未能解析出安全的修复命令。',
        'fix_attempted': '[pip-aide] 已尝试执行修复命令。',
        'fix_not_applied_or_failed': '[pip-aide] 未应用修复命令（用户跳过或执行失败）。',
        'fixed_file_created': '[pip-aide] 已创建修复后的需求文件：{filename}',
        'no_suggestion': '[pip-aide] AI 未提供建议。',
        'warning': '警告',
        'generate_fixed_file_fail': '生成修复后 requirements 文件失败: {error}',
        'network_error': "[pip-aide 错误] 连接 AI 服务时发生网络错误: {error}",
        'server_error': "[pip-aide 错误] AI 服务返回服务器错误: {status_code}",
        'json_error': "[pip-aide 错误] 无法解析 AI 服务响应: {error}",
        'invalid_server_url': "[pip-aide 错误] 无效的服务器 URL: {url}",
        'retrying_ai_connection': "[pip-aide] 正在重试 AI 连接，第 {attempt}/{max_retries} 次...",
        'ai_service_unavailable': "[pip-aide 错误] AI 服务不可用：{url}。请检查服务器 URL 并重试。",
        'missing_package_name': "[pip-aide 错误] 未提供包名或选项。请指定一个包来安装。",
    }
}

CONFIG_LOCATIONS = [
    os.path.expanduser('~/.config/pip-aide/pip-aide.conf'),
    os.path.expanduser('~/.config/pip/pip.conf'),
    os.path.expanduser('~/.pip/pip.conf'),
    os.path.join(os.getcwd(), 'pip.conf'),
]

DEFAULT_CONFIG = {
    'server_url': 'https://api.pip-aide.com',
    'auto_confirm': 'false',
    'analytics': 'ask',
    'lang': '',
    'loglevel': 'INFO',
    'timeout': '30',
}

ALLOWED_COMMAND_PATTERNS = [
    r"^pip\s+install($|\s+.*)",
    r"^pip\s+uninstall($|\s+.*)",
    r"^python\s+-m\s+pip\s+install($|\s+.*)",
]
DISALLOWED_SUBSTRINGS = ["sudo", "rm ", "mv ", "dd ", "|", ";", "&&", ">", "<"]

def setup_logger(level_name):
    """设置日志记录器，根据给定的级别名称配置日志级别"""
    log_level = getattr(logging, level_name.upper(), logging.INFO)
    
    # 创建日志记录器
    logger = logging.getLogger('pip-aide')
    logger.setLevel(log_level)
    
    # 如果已经有处理器，不再添加新的
    if logger.handlers:
        return logger
        
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 创建格式化器
    formatter = logging.Formatter('[pip-aide %(levelname)s] %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    
    return logger

# 全局日志记录器，初始化为 INFO 级别，将在 main 函数中更新
logger = setup_logger('INFO')

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    config.read_dict({'pip-aide': DEFAULT_CONFIG})
    
    for path in CONFIG_LOCATIONS:
        if os.path.exists(path):
            try:
                config.read(path)
                logger.debug(f"Config loaded from {path}")
            except configparser.Error as e:
                logger.warning(f"Failed to parse config file {path}: {e}")
    
    return config['pip-aide']

CONFIG = load_config()

def get_setting(key, env_var=None, cli_value=None, default=None):
    """
    获取设置值，遵循优先级：命令行 > 环境变量 > 配置文件 > 默认值
    """
    if cli_value is not None:
        if isinstance(cli_value, bool):
            return str(cli_value).lower()
        return cli_value
        
    if env_var and os.environ.get(env_var) is not None:
        logger.debug(f"Using environment variable {env_var} for {key}")
        return os.environ[env_var]
        
    value = CONFIG.get(key, default if default is not None else '')
    logger.debug(f"Setting {key} = {value}")
    return value

def get_message(key, lang=None, **kwargs):
    """获取指定语言的消息，并用关键字参数进行格式化"""
    if lang is None or lang not in ['en', 'zh']:
        lang = 'en'
        
    message_template = default_messages.get(lang, default_messages['en']).get(key, default_messages['en'].get(key, key))
    try:
        return message_template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing key in format string: {e}")
        return message_template

def get_machine_id():
    """获取唯一的机器标识"""
    try:
        mac = uuid.getnode()
        if (mac >> 40) % 2:
            return str(uuid.uuid1())
        else:
            return hex(mac)
    except Exception as e:
        logger.debug(f"Error getting machine ID, using fallback: {e}")
        return str(uuid.uuid1())

def run_command(command_args, timeout=600):
    """执行命令并返回退出码、标准输出和标准错误"""
    command_str = ' '.join(command_args)
    logger.debug(f"Executing command: {command_str}")
    
    try:
        proc = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            logger.debug(f"Command exit code: {proc.returncode}")
            return proc.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout} seconds: {command_str}")
            proc.kill()
            stdout, stderr = proc.communicate()
            return proc.returncode, stdout, stderr
    except FileNotFoundError:
        logger.error(f"Command not found: {command_args[0]}")
        return 127, '', f"Command not found: {command_args[0]}"
    except PermissionError:
        logger.error(f"Permission denied when executing: {command_str}")
        return 126, '', f"Permission denied: {command_str}"
    except Exception as e:
        logger.error(f"Failed to execute command: {command_str}: {e}")
        return 1, '', str(e)

def extract_commands_from_markdown(markdown_text):
    """从 Markdown 格式的文本中提取命令"""
    commands = re.findall(r"```(.*?)```", markdown_text, re.DOTALL)
    extracted_commands = []
    for block in commands:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        extracted_commands.extend(lines)
    return extracted_commands

def parse_and_filter_commands(suggestion, lang, is_requirements_file=False, original_req_file=None):
    """
    解析 AI 建议并过滤出安全的命令。
    如果 is_requirements_file 为 True，避免建议重新运行原始文件。
    """
    logger.debug("Starting command parsing and safety filtering")
    print(f"[{get_message('info', lang=lang)}] {get_message('filter_start', lang=lang)}")
    
    # 基于允许的模式和禁止的子串进行基本过滤
    lines = suggestion.strip().split('\n')
    potential_commands = []
    in_code_block = False
    for line in lines:
        if line.startswith('```'):
            in_code_block = not in_code_block
        elif in_code_block:
            potential_commands.append(line)
    
    logger.debug(f"Found {len(potential_commands)} potential commands in suggestion")
    
    safe_commands = []
    for cmd_str in potential_commands:
        try:
            command_args = shlex.split(cmd_str)
        except ValueError as e:
            logger.warning(f"Failed to parse command: {cmd_str}: {e}")
            continue
            
        # 检查禁止的子串
        disallowed_found = [sub for sub in DISALLOWED_SUBSTRINGS if sub in cmd_str]
        if disallowed_found:
            logger.warning(f"Command contains disallowed substrings: {disallowed_found}")
            print(f"  Skipping unsafe: Contains disallowed substring - {cmd_str}", file=sys.stderr)
            continue

        # 检查允许的模式
        is_allowed = False
        for pattern in ALLOWED_COMMAND_PATTERNS:
            if re.match(pattern, cmd_str, re.IGNORECASE):
                is_allowed = True
                break
        
        if not is_allowed:
            logger.warning(f"Command does not match allowed patterns: {cmd_str}")
            print(f"  Skipping unsafe: Doesn't match allowed patterns - {cmd_str}", file=sys.stderr)
            continue

        # *** 如果原始命令是 -r，则进行特定检查 ***
        if is_requirements_file and original_req_file:
            # 检查命令是否尝试重新运行可能已损坏的原始文件
            req_pattern_pip = rf"^pip\s+install\s+(-[a-zA-Z]+\s+)*-r\s+{re.escape(original_req_file)}(\s+.*)?$"
            req_pattern_python = rf"^python\s+-m\s+pip\s+install\s+(-[a-zA-Z]+\s+)*-r\s+{re.escape(original_req_file)}(\s+.*)?$"
            if re.match(req_pattern_pip, cmd_str, re.IGNORECASE) or re.match(req_pattern_python, cmd_str, re.IGNORECASE):
                logger.info(f"Skipping command that re-runs the original requirements file: {cmd_str}")
                print(f"  Skipping redundant: Attempting to re-run original requirements file - {cmd_str}", file=sys.stderr)
                continue

        # 如果所有检查都通过
        logger.info(f"Command accepted as safe: {cmd_str}")
        print(f"  Accepted: {cmd_str}")
        safe_commands.append(cmd_str)

    if not safe_commands:
        logger.warning("No safe commands found in the suggestion")
        print(get_message('filter_no_safe_commands', lang=lang))
        
    return safe_commands

def attempt_auto_fix(commands_to_try, auto_confirm, lang):
    """尝试执行安全命令，根据需要进行确认。返回 (fix_applied, [installed_specs])"""
    fix_applied_successfully = False
    successfully_installed_specs = []
    
    for cmd_str in commands_to_try:
        logger.info(f"Proposing fix command: {cmd_str}")
        print(f"[{get_message('info', lang=lang)}] {get_message('proposing_command', lang=lang, cmd=cmd_str)}")
        
        execute_command = False
        if auto_confirm:
            logger.debug("Auto-confirm enabled, executing command")
            print(get_message('executing_command', lang=lang))
            execute_command = True
        else:
            try:
                confirm = input(f"[pip-aide **{get_message('confirm', lang=lang)}**] {get_message('confirm_prompt', lang=lang)}")
                if confirm.lower() == 'y':
                    logger.debug("User confirmed command execution")
                    execute_command = True
                else:
                    logger.debug("User rejected command execution")
                    print(get_message('skipping_execution_user', lang=lang))
            except EOFError:
                logger.warning("Input stream closed, skipping command execution")
                print(get_message('skipping_execution_user', lang=lang))
                
        if execute_command:
            try:
                cmd_args = shlex.split(cmd_str)
                retcode, stdout, stderr = run_command(cmd_args)
                
                if retcode == 0:
                    logger.info(f"Command executed successfully: {cmd_str}")
                    print(get_message('command_success', lang=lang, cmd=cmd_str))
                    fix_applied_successfully = True
                    
                    # 尝试提取包名（仅处理 pip install xxx 形式，不处理复杂情况）
                    if 'install' in cmd_args:
                        idx = cmd_args.index('install')
                        if idx+1 < len(cmd_args):
                            pkg = cmd_args[idx+1]
                            if not pkg.startswith('-'):
                                logger.debug(f"Added successfully installed package: {pkg}")
                                successfully_installed_specs.append(pkg)
                else:
                    logger.error(f"Command execution failed with exit code {retcode}: {cmd_str}")
                    print(get_message('command_fail', lang=lang, cmd=cmd_str, code=retcode))
                    if stderr:
                        logger.debug(f"Command stderr: {stderr}")
                        
            except Exception as e:
                logger.error(f"Exception executing command '{cmd_str}': {e}")
                print(f"[pip-aide 错误] 命令 '{cmd_str}' 执行异常: {e}")
                
    return fix_applied_successfully, successfully_installed_specs

def get_ai_suggestion(error_context, server_url, timeout=30, retries=2, lang='en'):
    """
    请求 AI 服务器分析错误并提供修复建议
    
    Args:
        error_context: 错误信息和上下文
        server_url: AI 服务器的 URL
        timeout: 请求超时时间（秒）
        retries: 重试次数
        lang: 错误消息的语言
    
    Returns:
        str: AI 的建议，如果无法获取则返回 None
    """
    machine_id = get_machine_id()
    payload = {
        "machine_id": machine_id,
        "error_context": error_context
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # 检查服务器 URL 是否有效
    try:
        parsed_url = urlparse(server_url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            logger.error(f"Invalid server URL: {server_url}")
            print(get_message('invalid_server_url', lang=lang, url=server_url))
            return None
            
        # 确保URL包含/analyze_error端点
        path = parsed_url.path
        if not path or not path.endswith('/analyze_error'):
            # 构建新的URL，确保包含/analyze_error端点
            parts = list(parsed_url)
            if not parts[2]:  # 路径为空
                parts[2] = '/analyze_error'
            elif parts[2].endswith('/'):  # 路径以/结尾
                parts[2] = parts[2] + 'analyze_error'
            elif '/analyze_error' not in parts[2]:  # 路径不包含/analyze_error
                parts[2] = parts[2] + '/analyze_error'
            server_url = urlunparse(parts)
            logger.debug(f"Modified server URL to ensure endpoint: {server_url}")
            
    except Exception as e:
        logger.error(f"Failed to parse server URL: {e}")
        print(get_message('invalid_server_url', lang=lang, url=server_url))
        return None
    
    logger.debug(f"Requesting AI suggestion from: {server_url}")
    
    connection_error_occurred = False
    for attempt in range(retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{retries}...")
                print(get_message('retrying_ai_connection', lang=lang, attempt=attempt, max_retries=retries))
                
            response = requests.post(server_url, json=payload, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    suggestion = data.get('suggestion')
                    if suggestion:
                        if "UNCERTAIN" in suggestion:
                            logger.info("AI response indicates uncertainty")
                            print(get_message('ai_uncertain', lang=lang))
                            return None
                        print(get_message('ai_suggestion_is', lang=lang, suggestion=suggestion))
                        return suggestion
                    else:
                        logger.warning("Server response missing 'suggestion' field")
                        print(get_message('get_ai_suggestion_fail', lang=lang))
                        return None
                except ValueError as e:
                    logger.error(f"Server returned invalid JSON: {e}")
                    print(get_message('json_error', lang=lang, error=str(e)))
                    return None
            else:
                logger.error(f"Server returned non-200 status code: {response.status_code}")
                print(get_message('server_error', lang=lang, status_code=response.status_code))
                if attempt < retries:
                    continue  # 仍有重试次数，继续循环
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Request to AI server timed out after {timeout} seconds")
            print(get_message('network_error', lang=lang, error="timeout"))
            connection_error_occurred = True
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to AI server: {server_url}: {e}")
            print(get_message('network_error', lang=lang, error="connection failed"))
            connection_error_occurred = True
        except Exception as e:
            logger.error(f"Error calling AI service: {e}")
            print(get_message('ai_call_fail', lang=lang, e=str(e)))
            connection_error_occurred = True
            
        # 如果还有重试次数，则继续尝试
        if attempt < retries:
            time.sleep(1)  # 简单的退避策略
            continue
        else:
            if connection_error_occurred:
                print(get_message('ai_service_unavailable', lang=lang, url=server_url))
            return None
            
    return None

def print_help_and_exit():
    """打印帮助信息并退出"""
    print("""
pip-aide: AI-powered assistant for fixing pip install errors

Usage: pip-aide install <package_name or -r requirements.txt> [other pip options]

Options:
  --server-url URL       Specify AI server URL
  --auto-confirm         Automatically confirm suggested fix commands
  --analytics on/off/ask Control anonymous usage statistics
  --lang en/zh           Set display language
  --loglevel LEVEL       Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --timeout SECONDS      Set AI request timeout in seconds
  --help, -h             Show this help message

Example:
  pip-aide install tensorflow
  pip-aide install -r requirements.txt --server-url=http://localhost:8000/analyze_error
    """)
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(add_help=False)
    
    parser.add_argument('--server-url', help="AI server URL")
    parser.add_argument('--auto-confirm', action='store_true', help="Automatically confirm commands")
    parser.add_argument('--analytics', choices=['on', 'off', 'ask'], help="Usage analytics setting")
    parser.add_argument('--lang', help="Language (en or zh)")
    parser.add_argument('--loglevel', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                      help="Logging level")
    parser.add_argument('--timeout', help="API request timeout (seconds)")
    parser.add_argument('--help', '-h', action='store_true', help="Show help")
    
    parser.add_argument('command', nargs='?', choices=['install'], help="Currently only 'install' is supported.")
    parser.add_argument('args', nargs=argparse.REMAINDER, help="Arguments to pass to pip.")

    # 解析参数
    args, unknown = parser.parse_known_args()
    
    if args.help or not args.command:
        print_help_and_exit()

    # --- Determine final settings considering priority --- 
    # (CLI > Env Var > Config > Default)
    final_server_url = get_setting('server_url', 'PIP_AIDE_SERVER_URL', args.server_url)
    final_auto_confirm = get_setting('auto_confirm', 'PIP_AIDE_AUTO_CONFIRM', args.auto_confirm).lower() == 'true'
    final_analytics = get_setting('analytics', 'PIP_AIDE_ANALYTICS', args.analytics).lower()
    final_lang = get_setting('lang', 'PIP_AIDE_LANG', args.lang).lower()
    final_loglevel = get_setting('loglevel', 'PIP_AIDE_LOGLEVEL', args.loglevel).upper()
    final_timeout_str = get_setting('timeout', 'PIP_AIDE_TIMEOUT', args.timeout)

    # --- Validate and finalize settings --- 
    # 设置日志级别
    try:
        global logger
        logger = setup_logger(final_loglevel)
        logger.debug(f"Log level set to: {final_loglevel}")
    except (ValueError, AttributeError):
        print(f"Invalid log level: {final_loglevel}, using INFO instead")
        logger = setup_logger('INFO')

    # Language detection and validation (simplified)
    if final_lang not in ['en', 'zh']:
        detected_sys_lang = locale.getdefaultlocale()[0]
        if detected_sys_lang and detected_sys_lang.lower().startswith('zh'):
            if not final_lang: # Only default if not explicitly set wrongly
                 final_lang = 'zh'
            else:
                 logger.warning(get_message('invalid_lang_warning', lang='en').format(specified=final_lang))
                 final_lang = 'en' # Default to EN if explicitly set wrong
        else:
            if final_lang: # If lang was set but invalid and not zh
                 logger.warning(get_message('invalid_lang_warning', lang='en').format(specified=final_lang))
            final_lang = 'en' # Default to EN

    logger.info(f"{get_message('language_info', lang=final_lang)}: {final_lang}")

    # Timeout validation
    try:
        final_timeout_seconds = int(final_timeout_str)
        if final_timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
    except ValueError:
        logger.warning(get_message('invalid_timeout_warning', lang=final_lang).format(specified=final_timeout_str))
        final_timeout_seconds = 30 # Default
    logger.info(f"{get_message('timeout_info', lang=final_lang)}: {final_timeout_seconds}s")

    # Auto-confirm info
    auto_confirm_msg = get_message('autoconfirm_enabled', lang=final_lang) if final_auto_confirm else get_message('autoconfirm_disabled', lang=final_lang)
    logger.info(auto_confirm_msg)

    # Analytics (Placeholder - Add actual logic if implemented)
    if final_analytics == 'on':
        logger.info(get_message('analytics_on', lang=final_lang))
    elif final_analytics == 'off':
        logger.info(get_message('analytics_off', lang=final_lang))
    else: # ask - Placeholder for interaction
        logger.info(get_message('analytics_ask', lang=final_lang))

    # --- Execute Command --- 
    if args.command == 'install':
        # 创建要传递给pip的参数列表
        pip_args = []
        
        # 从所有参数中过滤出pip-aide特有参数
        pip_aide_params = ['--server-url', '--auto-confirm', '--analytics', '--lang', '--loglevel', '--timeout']
        
        # 处理args.args中的参数，过滤掉pip-aide特有参数
        i = 0
        while i < len(args.args):
            arg = args.args[i]
            skip = False
            
            # 检查是否是pip-aide参数
            for param in pip_aide_params:
                if arg.startswith(param + '=') or arg == param:
                    skip = True
                    # 如果参数是独立的，且有值，需要跳过下一个参数
                    if arg == param and i + 1 < len(args.args) and not args.args[i+1].startswith('-'):
                        i += 1  # 跳过下一个参数
                    break
            
            if not skip:
                pip_args.append(arg)
            
            i += 1
        
        # 修正：如果没有传入任何包名或选项，提示用户
        if not pip_args:
            print(get_message('missing_package_name', lang=final_lang))
            print_help_and_exit()
            
        # 构建并显示完整命令  
        original_command_str = ' '.join(['pip', args.command] + pip_args)
        print(f"\n[pip-aide] Running: {original_command_str}")
        
        try:
            # 执行pip安装命令
            retcode, stdout, stderr = run_command(['pip', args.command] + pip_args)

            if retcode == 0:
                print(get_message('install_success', lang=final_lang))
                sys.exit(0) # Exit successfully
            else:
                # Installation failed
                print(get_message('install_fail', lang=final_lang))
                error_output = f"Command: {original_command_str}\nExit Code: {retcode}\n\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
                print(error_output)

                # Attempt AI fix
                print(f"\n[pip-aide] Attempting AI fix...")
                suggestion = get_ai_suggestion(error_output, final_server_url, final_timeout_seconds, lang=final_lang)

                if suggestion:
                    # Check if the original command used -r
                    original_req_file = None
                    is_requirements_file = False
                    try:
                        req_idx = pip_args.index('-r')
                        if req_idx + 1 < len(pip_args):
                            original_req_file = pip_args[req_idx + 1]
                            is_requirements_file = True
                            logger.debug(f"Requirements file detected: {original_req_file}")
                    except ValueError:
                        logger.debug("No requirements file (-r) flag found in command")
                        pass # -r not found
                    
                    # Pass the flag and filename to the parser
                    safe_commands_to_try = parse_and_filter_commands(suggestion, final_lang, is_requirements_file, original_req_file)
                    
                    if safe_commands_to_try:
                        fix_applied, installed_specs = attempt_auto_fix(safe_commands_to_try, final_auto_confirm, final_lang)
                        
                        if fix_applied:
                            print(get_message('fix_attempted', lang=final_lang))
                            
                            # 如果是 requirements 文件且有修复，生成 .fixed.txt 文件
                            if is_requirements_file and original_req_file and installed_specs:
                                try:
                                    import os
                                    base, ext = os.path.splitext(original_req_file)
                                    fixed_filename = f"{base}.fixed{ext}"
                                    fixed_file_path = os.path.abspath(os.path.join(os.getcwd(), fixed_filename))
                                    fixed_content = "# Generated by pip-aide based on successful fixes\n" + "\n".join(installed_specs) + "\n"
                                    
                                    logger.debug(f"Writing fixed requirements to: {fixed_file_path}")
                                    with open(fixed_file_path, 'w', encoding='utf-8') as f:
                                        f.write(fixed_content)
                                    print(get_message('fixed_file_created', lang=final_lang).format(filename=fixed_filename))
                                except PermissionError:
                                    logger.error(f"Permission denied when writing to {fixed_filename}")
                                    print(f"[{get_message('warning', lang=final_lang)}] {get_message('generate_fixed_file_fail', lang=final_lang, error='Permission denied')}")
                                except OSError as e_fixfile:
                                    logger.error(f"OS error when writing fixed file: {e_fixfile}")
                                    print(f"[{get_message('warning', lang=final_lang)}] {get_message('generate_fixed_file_fail', lang=final_lang, error=e_fixfile)}")
                                except Exception as e_fixfile:
                                    logger.error(f"Unexpected error when writing fixed file: {e_fixfile}")
                                    print(f"[{get_message('warning', lang=final_lang)}] {get_message('generate_fixed_file_fail', lang=final_lang, error=e_fixfile)}")
                        else:
                            print(get_message('fix_not_applied_or_failed', lang=final_lang))
                    else:
                        print(get_message('parse_safe_commands_fail', lang=final_lang))
                else:
                    # 无AI建议时显示更明确的错误
                    print(get_message('no_suggestion', lang=final_lang))
                sys.exit(retcode)

        except KeyboardInterrupt:
            logger.warning("Operation interrupted by user")
            print("\n[pip-aide] Operation interrupted by user")
            sys.exit(130)  # Standard exit code for SIGINT
        except Exception as e:
            logger.error(f"An unexpected error occurred during installation attempt: {e}")
            print(f"[pip-aide Error] An unexpected error occurred during installation attempt: {e}")
            sys.exit(1) # Ensure failure exit code on unexpected error

if __name__ == "__main__":
    main()
