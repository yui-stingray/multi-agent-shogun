#!/usr/bin/python3
"""
Staff Router - タスクとスタッフの適合度スコア計算・自動割り当て（修正版）
Alexの拡張属性管理（Bearer Token認証）を参考にしたYAML管理
"""

import sys
import os
import yaml  # 標準yamlモジュール（LibYAML）
import json
from pathlib import Path
from datetime import datetime

# 設定
SCRIPT_DIR = Path(__file__).parent
STAFF_CONFIG = SCRIPT_DIR / "../config/staff.yaml"
LOG_DIR = SCRIPT_DIR / "../logs"

# ロギング設定
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "staff_router.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_staff_config_yaml():
    """スタッフ設定ファイルを読み込む（YAML形式、標準yamlモジュール使用）"""
    try:
        with open(STAFF_CONFIG, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"エラー: 設定ファイルが見つかりません: {STAFF_CONFIG}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"エラー: YAML解析失敗: {e}")
        return {}

def analyze_task_advanced(task_description):
    """詳細なタスク解析（キーワードの重み付けを含む）"""
    keywords_with_weights = {
        # コード生成系（高優先度）
        'code-gen': ['コード', 'プログラム', 'API', 'エンドポイント', '関数', 'クラス', '実装', '開発', 'コンポーネント', 'ライブラリ'],
        # 分析・調査系（中優先度）
        'analysis': ['分析', '調査', 'リサーチ', 'レポート', 'データ', '統計', '調査'],
        # 文章作成系（中優先度）
        'writing': ['文章', 'ブログ', 'ドキュメント', '要約', 'ライティング', '投稿', '記述'],
        # デバッグ系（高優先度）
        'debugging': ['デバッグ', 'バグ', 'エラー', '問題', '修正', 'トラブル', 'デバック'],
        # アーキテクチャ設計系（中優先度）
        'architecture': ['アーキテクチャ', '設計', '構成', 'パターン', 'アンテナ'],
        # 戦略・意思決定系（高優先度）
        'leadership': ['戦略', '意思決定', 'レビュー', 'マネジメント', 'プランニング', '決定'],
    }
    
    task = task_description.lower()
    found_keywords = []
    
    # キーワード抽出（重み付き）
    for category, words in keywords_with_weights.items():
        for word in words:
            if word in task:
                weight = len(words)  # キーワード数に応じて重みを調整
                found_keywords.append(f"{category}:{weight}")
                break
    
    logger.info(f"解析キーワード: {found_keywords}")
    return found_keywords

def calculate_staff_score_advanced(staff, task_keywords):
    """詳細なスコア計算（役割 + スキル + モデル）"""
    score = 0
    role_score = 0
    skill_score = 0
    
    # ステータスチェック
    if staff.get('status') != 'active':
        logger.info(f"[SKIP] {staff.get('id', 'unknown')}: paused (ステータス: {staff.get('status')})")
        return 0
    
    # 役割スコア（洗練済）
    role_scores = {
        'engineer': 3,
        'senior-engineer': 5,
        'junior-engineer': 2,
        'architect': 5,
        'analyst': 2,
        'cto': 5,
        'manager': 4,
        'reviewer': 3,
    }
    
    role = staff.get('role', '')
    role_score = role_scores.get(role, 0)
    score += role_score
    
    # スキルスコア（キーワードマッチング）
    skills = staff.get('skills', [])
    
    # skillsが文字列の場合はリストに変換
    if isinstance(skills, str):
        skills = [skill.strip() for skill in skills.split(' ')] if skills else []
    
    for keyword in task_keywords:
        category, weight = keyword.split(':')
        weight = int(weight)  # 整数に変換
        
        # スキル名にキーワードが含まれているかチェック
        for skill_name in skills:
            skill_lower = skill_name.lower()
            keyword_lower = category.lower()
            
            # 直接マッチまたはあいまいマッチ
            if keyword_lower in skill_lower:
                score += weight
                skill_score += weight
                logger.info(f"[MATCH] {staff.get('id', 'unknown')}: {keyword} (スキル: {skill_name}, +{weight})")
                break
    
    # モデル能力による加算
    model = staff.get('model', '')
    if 'opus' in model or 'claude-3.7' in model or 'claude-4.5' in model:
        score += 2  # 最強モデル
    elif 'sonnet' in model or 'claude-3.5-sonnet' in model or 'claude-haiku' in model:
        score += 1  # 中堅モデル
    
    # 簡素なデバッグ出力
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"[SCORE] {staff.get('id', 'unknown')}: role={role_score}, skills={skill_score}, model={score - role_score - skill_score}, total={score}")
    
    return score

def get_matching_staff_info(staff_data, best_staff_id):
    """マッチしたスタッフの情報を取得"""
    staff = staff_data.get('staff', {}).get(best_staff_id, {})
    
    return {
        'id': best_staff_id,
        'name': staff.get('name', best_staff_id),
        'provider': staff.get('provider', best_staff_id),
        'role': staff.get('role', best_staff_id),
        'model': staff.get('model', best_staff_id),
        'bio': staff.get('bio', best_staff_id),
    }

def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: ./staff_router.py [オプション] タスク説明")
        print("\nオプション:")
        print("  -p, --priority PRIORITY    タスク優先度 (high|medium|low) [デフォルト: medium]")
        print("  -s, --staff ID            強制的に特定のスタッフに割り当てる")
        print("  -v, --verbose              詳細出力を有効にする")
        print("  -h, --help                 このヘルプを表示")
        print("\n例:")
        print("  ./staff_router.py \"Reactコンポーネントを作って\"")
        print("  ./staff_router.py --priority high --force-staff claude-opus \"APIエンドポイントを設計して\"")
        sys.exit(1)
    
    # コマンドライン引数の解析
    task_description = ' '.join(sys.argv[1:])
    task_priority = "medium"
    force_staff = ""
    verbose = False
    
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        
        if arg in ['-p', '--priority']:
            if i + 1 < len(sys.argv):
                task_priority = sys.argv[i + 1]
        
        elif arg in ['-s', '--staff']:
            if i + 1 < len(sys.argv):
                force_staff = sys.argv[i + 1]
        
        elif arg in ['-v', '--verbose']:
            verbose = True
    
    # タスク解析
    logger.info(f"タスクを分析中: {task_description}")
    task_keywords = analyze_task_advanced(task_description)
    
    if verbose:
        print(f"\n[解析] キーワード: {', '.join(task_keywords)}\n")
    
    # スタッフ設定の読み込み（YAML形式、標準yamlモジュール使用）
    staff_data = load_staff_config_yaml()
    
    if 'staff' not in staff_data:
        logger.error("エラー: スタッフデータが見つかりません")
        sys.exit(1)
    
    staff_list = staff_data['staff']
    
    # 最適なスタッフを選択
    best_staff = None
    best_score = -1
    best_reason = ""
    
    if force_staff:
        # 強制的に指定されたスタッフを使用
        if force_staff in staff_list:
            best_staff = force_staff
            best_score = calculate_staff_score_advanced(
                staff_list[force_staff], 
                task_keywords
            )
            best_reason = "強制指定"
            logger.info(f"[FORCE] {best_staff}に強制割り当て: スコア{best_score}")
    else:
        # 全スタッフのスコア計算
        for staff_id, staff in staff_list.items():
            score = calculate_staff_score_advanced(staff, task_keywords)
            
            if score > best_score:
                best_score = score
                best_staff = staff_id
                best_reason = "スコアが最も高い"
            
            if verbose:
                logger.info(f"[スキャン] {staff_id}: {score}点")
    
    # 結果表示
    print("\n" + "="*50)
    print(f"タスク: {task_description}")
    print(f"優先度: {task_priority}")
    print("="*50 + "\n")
    
    if best_staff:
        staff_info = get_matching_staff_info(staff_data, best_staff)
        
        print("✅ 自動ルーティング結果:")
        print(f"   割り当て: {staff_info['name']} ({best_staff})")
        print(f"   プロバイダー: {staff_info['provider']}")
        print(f"   役割: {staff_info['role']}")
        print(f"   モデル: {staff_info['model']}")
        print(f"   スコア: {best_score}")
        print(f"   理由: {best_reason}")
        print(f"   説明: {staff_info['bio']}")
        print("\n" + "="*50)
        
        # ログ記録
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'task': task_description,
            'priority': task_priority,
            'assigned_to': best_staff,
            'score': best_score,
            'reason': best_reason
        }
        
        # ログファイルに追加
        log_file = LOG_DIR / "tasks.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        logger.info(f"ログを記録: {log_file}")
        
    else:
        print("❌ マッチするスタッフがいません")
        print("   すべてのスタッフがpaused状態か、タスクの要件に合致しない可能性があります")
        print("\n" + "="*50)
        
        print("現在のスタッフ:")
        for staff_id, staff in staff_list.items():
            status = staff.get('status', 'unknown')
            name = staff.get('name', staff_id)
            
            if status == 'active':
                print(f"   ✓ {name} ({staff_id}) - {status}")
            elif status == 'paused':
                print(f"   ⊘ {name} ({staff_id}) - {status}")
            else:
                print(f"   ? {name} ({staff_id}) - {status}")
        
        sys.exit(1)

if __name__ == '__main__':
    main()
