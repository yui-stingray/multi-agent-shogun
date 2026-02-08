#!/bin/bash

####################################################################################################
#
# Staff Router - タスクとスタッフの適合度スコア計算・自動割り当て（簡易版）
# Alexの拡張属性管理を参考にした基本実装
#
####################################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAFF_CONFIG="${SCRIPT_DIR}/../config/staff.yaml"

# コマンドライン引数の解析
TASK_DESCRIPTION=""
TASK_PRIORITY="medium"
FORCE_STAFF=""
VERBOSE=false

# ヘルプ表示
show_help() {
    cat << 'EOF'
使用方法: ./staff_router_simple.sh [オプション] "タスク説明"

オプション:
  -p, --priority PRIORITY    タスク優先度 (high|medium|low) [デフォルト: medium]
  -s, --staff ID            強制的に特定のスタッフに割り当てる
  -v, --verbose              詳細出力を有効にする
  -h, --help                 このヘルプを表示

例:
  ./staff_router_simple.sh "Reactコンポーネントを作って"
  ./staff_router_simple.sh --priority high --force-staff claude-opus "APIエンドポイントを設計して"
EOF
}

# 引数の解析
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--priority)
            TASK_PRIORITY="$2"
            shift 2
            ;;
        -s|--staff)
            FORCE_STAFF="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            TASK_DESCRIPTION="$*"
            break
            ;;
    esac
done

# タスクの解析（簡易版）
analyze_task() {
    local task="$1"
    local keywords=()
    
    # プログラミング関連
    if echo "$task" | grep -qi "コード\|プログラム\|API\|エンドポイント\|実装"; then
        keywords+=("code-gen")
    fi
    
    # 分析・調査関連
    if echo "$task" | grep -qi "分析\|調査\|リサーチ\|レポート"; then
        keywords+=("analysis")
    fi
    
    # 文章作成
    if echo "$task" | grep -qi "文章\|ブログ\|ドキュメント\|要約"; then
        keywords+=("writing")
    fi
    
    # デバッグ
    if echo "$task" | grep -qi "デバッグ\|バグ\|エラー\|問題\|修正"; then
        keywords+=("debugging")
    fi
    
    # アーキテクチャ
    if echo "$task" | grep -qi "アーキテクチャ\|設計\|構成"; then
        keywords+=("architecture")
    fi
    
    echo "${keywords[@]}"
}

# メイン処理
main() {
    if [ -z "$TASK_DESCRIPTION" ]; then
        echo "エラー: タスク説明が指定されていません"
        show_help
        exit 1
    fi
    
    echo "タスクを分析中..."
    task_keywords=$(analyze_task "$TASK_DESCRIPTION")
    
    if $VERBOSE; then
        echo "[解析] キーワード: ${task_keywords[@]}"
    fi
    
    # スタッフ一覧の取得（簡易版）
    local best_staff=""
    local best_score=0
    
    if [ -n "$FORCE_STAFF" ]; then
        # 強制的に指定されたスタッフを使用
        best_staff="$FORCE_STAFF"
        best_score=1
        if $VERBOSE; then
            echo "[FORCE] $best_staffに強制割り当て"
        fi
    else
        # 簡易なマッチングルジック
        if [[ " ${task_keywords[*]} " =~ "code-gen" ]]; then
            best_staff="claude-sonnet"
            best_score=1
        elif [[ " ${task_keywords[*]} " =~ "analysis" ]]; then
            best_staff="gemini-pro"
            best_score=1
        elif [[ " ${task_keywords[*]} " =~ "writing" ]]; then
            best_staff="gemini-pro"
            best_score=1
        elif [[ " ${task_keywords[*]} " =~ "debugging" ]]; then
            best_staff="claude-opus"
            best_score=3
        elif [[ " ${task_keywords[*]} " =~ "architecture" ]]; then
            best_staff="claude-opus"
            best_score=3
        fi
    fi
    
    # 結果表示
    echo ""
    echo "==========================================="
    echo "タスク: $TASK_DESCRIPTION"
    echo "優先度: $TASK_PRIORITY"
    echo "==========================================="
    echo ""
    
    if [ -n "$best_staff" ]; then
        echo "✅ 自動ルーティング結果:"
        echo "   割り当て: $best_staff"
        echo "   スコア: $best_score"
        echo ""
    else
        echo "❌ マッチするスタッフがいません"
        echo "   タスクの内容を再確認してください"
        exit 1
    fi
    
    echo "==========================================="
}

# メイン実行
main
