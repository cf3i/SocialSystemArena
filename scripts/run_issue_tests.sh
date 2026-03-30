#!/usr/bin/env bash
# 运行 issue_test/ 下的累积回归脚本。
# 默认执行全部脚本；可通过 --exclude 排除当前 issue 的脚本。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ISSUE_TEST_DIR="$ROOT_DIR/issue_test"
FAIL=0
RAN=0
declare -a EXCLUDES=()

usage() {
    cat <<'EOF'
用法：
  bash scripts/run_issue_tests.sh [--exclude issue_test/<issue_id>.sh]

选项：
  --exclude <path>   排除指定 issue test，可重复传入
  -h, --help         显示帮助
EOF
}

normalize_path() {
    local path="$1"
    path="${path#"$ROOT_DIR"/}"
    path="${path#./}"
    printf '%s\n' "$path"
}

should_skip() {
    local candidate="$1"
    local excluded=""

    if [[ "${#EXCLUDES[@]}" -eq 0 ]]; then
        return 1
    fi

    for excluded in "${EXCLUDES[@]}"; do
        if [[ "$candidate" == "$excluded" ]]; then
            return 0
        fi
    done

    return 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --exclude)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --exclude 需要一个路径参数。" >&2
                exit 1
            fi
            EXCLUDES+=("$(normalize_path "$2")")
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: 未知参数: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ ! -d "$ISSUE_TEST_DIR" ]]; then
    echo "ERROR: 未找到 issue_test/ 目录。" >&2
    exit 1
fi

echo "=== Issue Test Suite ==="
echo ""

while IFS= read -r test_path; do
    relative_path="issue_test/$(basename "$test_path")"

    if should_skip "$relative_path"; then
        echo "SKIP: $relative_path"
        continue
    fi

    RAN=1
    echo "--- Running: $relative_path ---"
    if bash "$test_path"; then
        echo "$relative_path: PASS"
    else
        echo "$relative_path: FAIL"
        FAIL=1
    fi
    echo ""
done < <(find "$ISSUE_TEST_DIR" -maxdepth 1 -type f -name '*.sh' | sort)

echo "===================="
if [[ "$RAN" -eq 0 ]]; then
    echo "ISSUE TESTS: PASS (no matching tests)"
    exit 0
fi

if [[ "$FAIL" -eq 0 ]]; then
    echo "ISSUE TESTS: PASS"
    exit 0
fi

echo "ISSUE TESTS: FAIL"
exit 1
