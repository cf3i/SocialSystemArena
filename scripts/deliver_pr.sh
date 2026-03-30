#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"
shift || true

REPO=""
BASE=""
TITLE=""
BODY_FILE=""
MERGE_METHOD="squash"
AUTO_FALLBACK=true

usage() {
    cat <<'EOF'
用法：
  bash scripts/deliver_pr.sh ensure [--repo <owner/repo>] [--base <branch>] [--title <title>] [--body-file <path>]
  bash scripts/deliver_pr.sh merge [--repo <owner/repo>] [--merge-method <merge|squash|rebase>] [--no-auto]

子命令：
  ensure    推送当前分支，并创建或复用对应 PR
  merge     合并当前分支对应的 PR；若直接 merge 失败，默认尝试启用 auto-merge

选项：
  --repo <owner/repo>         显式指定 GitHub 仓库；默认从 origin 推断
  --base <branch>             PR base 分支；默认从 origin/HEAD 推断，缺失时回退到 main
  --title <title>             PR 标题；默认取最近一个非 stage commit subject
  --body-file <path>          PR body 文件；默认自动生成一个最小正文
  --merge-method <method>     merge 方法：merge / squash / rebase（默认：squash）
  --no-auto                   merge 子命令禁用 auto-merge fallback
  -h, --help                  显示帮助
EOF
}

error() {
    echo "ERROR: $*" >&2
}

require_command() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        error "未找到必需命令：$cmd"
        exit 1
    fi
}

current_branch() {
    git symbolic-ref --quiet --short HEAD 2>/dev/null || {
        error "当前不在可识别分支上，无法执行 PR 交付。"
        exit 1
    }
}

infer_repo_from_origin() {
    local remote_url
    remote_url="$(git remote get-url origin 2>/dev/null || true)"

    case "$remote_url" in
        git@github.com:*.git)
            printf '%s\n' "${remote_url#git@github.com:}" | sed 's/\.git$//'
            ;;
        git@github.com:*)
            printf '%s\n' "${remote_url#git@github.com:}"
            ;;
        https://github.com/*.git)
            printf '%s\n' "${remote_url#https://github.com/}" | sed 's/\.git$//'
            ;;
        https://github.com/*)
            printf '%s\n' "${remote_url#https://github.com/}"
            ;;
        *)
            return 1
            ;;
    esac
}

resolve_repo() {
    if [[ -n "$REPO" ]]; then
        printf '%s\n' "$REPO"
        return
    fi

    if REPO="$(infer_repo_from_origin)"; then
        printf '%s\n' "$REPO"
        return
    fi

    error "无法从 origin 推断 GitHub 仓库，请使用 --repo <owner/repo>。"
    exit 1
}

default_base_branch() {
    local origin_head
    origin_head="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
    if [[ -n "$origin_head" ]]; then
        printf '%s\n' "${origin_head#origin/}"
    else
        printf 'main\n'
    fi
}

default_pr_title() {
    local title
    title="$(git log --format=%s --invert-grep --grep '^chore(stage):' -n 1 2>/dev/null || true)"
    if [[ -n "$title" ]]; then
        printf '%s\n' "$title"
    else
        current_branch
    fi
}

make_default_body_file() {
    local branch="$1"
    local file
    file="$(mktemp)"
    cat >"$file" <<EOF
## Summary
- automated PR created for branch \`$branch\`

## Testing
- update this section if the repository needs richer PR notes
EOF
    printf '%s\n' "$file"
}

emit_pr_info() {
    local ref="$1"
    local repo="$2"
    local merge_commit_sha

    echo "PR_NUMBER=$(gh pr view "$ref" --repo "$repo" --json number --jq '.number')"
    echo "PR_URL=$(gh pr view "$ref" --repo "$repo" --json url --jq '.url')"
    echo "PR_STATE=$(gh pr view "$ref" --repo "$repo" --json state --jq '.state')"
    echo "PR_HEAD=$(gh pr view "$ref" --repo "$repo" --json headRefName --jq '.headRefName')"
    echo "PR_BASE=$(gh pr view "$ref" --repo "$repo" --json baseRefName --jq '.baseRefName')"
    echo "AUTO_MERGE_ENABLED=$(gh pr view "$ref" --repo "$repo" --json autoMergeRequest --jq '.autoMergeRequest != null')"
    merge_commit_sha="$(gh pr view "$ref" --repo "$repo" --json mergeCommit --jq '.mergeCommit.oid // ""' | tr -d '\n')"
    echo "MERGE_COMMIT_SHA=$merge_commit_sha"
}

ensure_branch_pushed() {
    local branch="$1"

    if git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' >/dev/null 2>&1; then
        git push
    else
        git push -u origin "$branch"
    fi
}

ensure_pr() {
    local branch repo base title body_path created_temp_body="false"

    require_command git
    require_command gh

    branch="$(current_branch)"
    repo="$(resolve_repo)"
    base="${BASE:-$(default_base_branch)}"
    title="${TITLE:-$(default_pr_title)}"

    if [[ "$branch" == "$base" ]]; then
        error "当前分支 ($branch) 与 PR base 分支相同；请先切到当前 issue 的工作分支。"
        exit 1
    fi

    ensure_branch_pushed "$branch"

    if gh pr view "$branch" --repo "$repo" --json number >/dev/null 2>&1; then
        echo "ACTION=EXISTING"
        emit_pr_info "$branch" "$repo"
        return
    fi

    body_path="$BODY_FILE"
    if [[ -z "$body_path" ]]; then
        body_path="$(make_default_body_file "$branch")"
        created_temp_body="true"
    fi

    if gh pr create \
        --repo "$repo" \
        --base "$base" \
        --head "$branch" \
        --title "$title" \
        --body-file "$body_path" >/dev/null 2>&1; then
        :
    elif gh pr view "$branch" --repo "$repo" --json number >/dev/null 2>&1; then
        :
    else
        if [[ "$created_temp_body" == "true" ]]; then
            rm -f "$body_path"
        fi
        error "创建 PR 失败。"
        exit 1
    fi

    if [[ "$created_temp_body" == "true" ]]; then
        rm -f "$body_path"
    fi

    echo "ACTION=CREATED"
    emit_pr_info "$branch" "$repo"
}

merge_pr() {
    local branch repo pr_ref direct_log auto_log

    require_command git
    require_command gh

    branch="$(current_branch)"
    repo="$(resolve_repo)"
    pr_ref="$branch"

    if ! gh pr view "$pr_ref" --repo "$repo" --json number >/dev/null 2>&1; then
        error "当前分支没有可 merge 的 PR：$branch"
        exit 1
    fi

    if [[ "$(gh pr view "$pr_ref" --repo "$repo" --json state --jq '.state')" == "MERGED" ]]; then
        echo "ACTION=ALREADY_MERGED"
        emit_pr_info "$pr_ref" "$repo"
        return
    fi

    direct_log="$(mktemp)"
    auto_log="$(mktemp)"

    if gh pr merge "$pr_ref" --repo "$repo" "--$MERGE_METHOD" >"$direct_log" 2>&1; then
        rm -f "$auto_log"
        echo "ACTION=MERGED"
        emit_pr_info "$pr_ref" "$repo"
        rm -f "$direct_log"
        return
    fi

    if [[ "$AUTO_FALLBACK" == "true" ]]; then
        if gh pr merge "$pr_ref" --repo "$repo" "--$MERGE_METHOD" --auto >"$auto_log" 2>&1; then
            rm -f "$direct_log"
            echo "ACTION=AUTO_MERGE_ENABLED"
            emit_pr_info "$pr_ref" "$repo"
            rm -f "$auto_log"
            return
        fi
    fi

    error "PR merge 失败。"
    echo "---- direct merge stderr/stdout ----" >&2
    cat "$direct_log" >&2
    if [[ "$AUTO_FALLBACK" == "true" ]]; then
        echo "---- auto-merge stderr/stdout ----" >&2
        cat "$auto_log" >&2
    fi
    rm -f "$direct_log" "$auto_log"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)
            REPO="$2"
            shift 2
            ;;
        --base)
            BASE="$2"
            shift 2
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        --body-file)
            BODY_FILE="$2"
            shift 2
            ;;
        --merge-method)
            MERGE_METHOD="$2"
            shift 2
            ;;
        --no-auto)
            AUTO_FALLBACK=false
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "未知参数：$1"
            usage
            exit 1
            ;;
    esac
done

case "$ACTION" in
    ensure)
        ensure_pr
        ;;
    merge)
        merge_pr
        ;;
    ""|-h|--help)
        usage
        exit 0
        ;;
    *)
        error "未知子命令：$ACTION"
        usage
        exit 1
        ;;
esac
