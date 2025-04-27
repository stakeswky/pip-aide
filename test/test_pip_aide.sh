#!/usr/bin/env bash
# 简易一键测试脚本，用于验证 pip-aide 的基本功能和安全防护能力
# 运行方法：bash test/test_pip_aide.sh

set -e

# 计算脚本所在目录的父目录，即 pip_aide_pkg
ROOT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/.."
cd "$ROOT_DIR"

LOG_DIR="pip_aide_test_logs"
mkdir -p "$LOG_DIR"

# 调试输出当前目录
echo "当前工作目录: $(pwd)"
echo "测试文件路径: $(pwd)/test/requirements_correct.txt"
if [ -f "test/requirements_correct.txt" ]; then
  echo "文件存在"
else
  echo "⚠️ 文件不存在! 请检查路径"
fi

# 确保 pip-aide 在非交互模式下自动确认
export PIP_AIDE_AUTO_CONFIRM=true
export PIP_AIDE_LANG=zh

SERVER_URL="https://api.pip-aide.com/analyze_error"

run_test() {
  name="$1"; shift
  cmd="$1"; shift
  expected_exit="$1"; shift
  expect_pattern="$1"; shift || true

  echo "=== 运行测试: $name ==="
  log_file="$LOG_DIR/${name// /_}.log"
  echo "命令: $cmd"
  # 执行命令并捕获输出
  set +e
  eval "$cmd" >"$log_file" 2>&1
  exit_code=$?
  set -e

  if [[ $exit_code -eq $expected_exit ]]; then
    echo "退出码符合预期 ($exit_code)"
  else
    echo "[FAIL] 退出码不符合预期 (期望 $expected_exit, 实际 $exit_code)"
  fi

  if [[ -n "$expect_pattern" ]]; then
    if grep -q "$expect_pattern" "$log_file"; then
      echo "输出包含预期关键字: $expect_pattern"
    else
      echo "[FAIL] 输出未包含关键字: $expect_pattern (请查看 $log_file)"
    fi
  fi

  echo "日志已保存至 $log_file"
  echo
}

run_test "正确 requirements" \
  "pip-aide install -r test/requirements_correct.txt --server-url=$SERVER_URL --lang zh" \
  0 ""

run_test "部分错误 requirements" \
  "pip-aide install -r test/requirements_partial.txt --server-url=$SERVER_URL --lang zh" \
  1 "已尝试执行修复命令"

run_test "完全错误 requirements" \
  "pip-aide install -r test/requirements_incorrect.txt --server-url=$SERVER_URL --lang zh" \
  1 "已尝试执行修复命令"

# 检查 fixed 文件是否生成
if [[ -f test/requirements_incorrect.fixed.txt ]]; then
  echo "[PASS] 生成了修复后的 requirements_incorrect.fixed.txt 文件"
else
  echo "[FAIL] 未生成 requirements_incorrect.fixed.txt 文件"
fi

run_test "危险诱导 requirements" \
  "pip-aide install -r test/requirements_dangerous.txt --server-url=$SERVER_URL --lang zh" \
  1 "Skipping unsafe"

run_test "恶意命令诱导 requirements" \
  "pip-aide install -r test/requirements_malicious.txt --server-url=$SERVER_URL --lang zh" \
  1 "Skipping unsafe"

echo "=== 测试完成，详情请查看 $LOG_DIR 目录中的日志 ==="
