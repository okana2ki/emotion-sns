import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import requests
import time
from google import genai
from google.genai import types
import traceback
import os

# ページ設定
st.set_page_config(page_title="感情分析SNS", page_icon="🎓", layout="wide")

# カスタムCSS（スマホ対応・日本語表示）
st.markdown("""
<style>
/* 入力欄のプレースホルダーとヘルプテキストを日本語化 */
.stTextInput > div > div > div > input::placeholder {
    color: #999;
}

.stTextArea > div > div > div > textarea::placeholder {
    color: #999;
}

/* スマホでのテキスト表示改善 */
.post-card {
    border-left: 5px solid var(--border-color);
    padding: 15px;
    margin: 10px 0;
    background-color: #f8f9fa;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    word-wrap: break-word;
    overflow-wrap: break-word;
    line-height: 1.6;
}

.post-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    flex-wrap: wrap;
}

.post-user {
    font-weight: bold;
    font-size: 14px;
    color: #333;
}

.post-time {
    font-size: 12px;
    color: #666;
    white-space: nowrap;
}

.post-emotion {
    font-weight: bold;
    margin: 8px 0;
    font-size: 16px;
}

.post-text {
    font-size: 15px;
    margin-top: 10px;
    line-height: 1.5;
    color: #333;
    white-space: pre-wrap;
    word-break: break-word;
}

.post-analysis {
    margin-top: 8px;
    font-size: 12px;
    color: #666;
    line-height: 1.4;
}

/* スマホでのボタン改善 */
@media (max-width: 768px) {
    .stButton > button {
        width: 100%;
        padding: 12px;
        font-size: 16px;
    }
    
    .post-card {
        margin: 8px 0;
        padding: 12px;
    }
    
    .post-text {
        font-size: 14px;
    }
}

/* Plotlyグラフのツールバー簡略化 */
.modebar {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# 日本語化用のJS（入力欄のプレースホルダー対応）
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    // 入力欄のヘルプテキストを日本語化
    setTimeout(function() {
        const inputs = document.querySelectorAll('input[type="text"], textarea');
        inputs.forEach(input => {
            if (input.placeholder && input.placeholder.includes('Press')) {
                if (input.tagName === 'INPUT') {
                    input.placeholder = 'タップして入力してください';
                } else if (input.tagName === 'TEXTAREA') {
                    input.placeholder = 'タップして感想を入力してください';
                }
            }
        });
    }, 1000);
});
</script>
""", unsafe_allow_html=True)

# セッション状態の初期化
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()
if 'is_posting' not in st.session_state:
    st.session_state.is_posting = False
if 'show_success' not in st.session_state:
    st.session_state.show_success = False
if 'auto_update_enabled' not in st.session_state:
    st.session_state.auto_update_enabled = True
if 'gemini_debug' not in st.session_state:
    st.session_state.gemini_debug = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False

# デバッグモード切り替え（問題解決後は無効化）
DEBUG_MODE = st.secrets.get("debug_mode", False)  # 元に戻す

# Gemini API設定（新SDK対応）
@st.cache_resource
def setup_gemini():
    """新SDK（google-genai）を使ったGemini APIの設定"""
    api_key = st.secrets.get("gemini_api_key", "")
    
    if not api_key:
        if DEBUG_MODE:
            st.error("🚨 Gemini API keyが設定されていません。secrets.tomlに'gemini_api_key'を追加してください。")
        return None, "API key not found", None
    
    try:
        # 環境変数にAPI keyを設定（新SDKの要件）
        os.environ['GEMINI_API_KEY'] = api_key
        
        # 新SDKでクライアントを作成
        client = genai.Client()
        
        # 推奨モデルでAPI接続テスト
        try:
            test_response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents="テスト接続"
            )
            return client, "gemini-2.5-flash-lite: API connection successful", "gemini-2.5-flash-lite"
        except Exception as primary_error:
            if DEBUG_MODE:
                st.warning(f"⚠️ gemini-2.5-flash-lite が利用できません: {primary_error}")
            
            # フォールバックモデル（gemini-2.0-flash-lite）
            try:
                test_response = client.models.generate_content(
                    model="gemini-2.0-flash-lite", 
                    contents="テスト接続"
                )
                return client, "gemini-2.0-flash-lite: Using fallback model", "gemini-2.0-flash-lite"
            except Exception as fallback_error:
                if DEBUG_MODE:
                    st.error(f"❌ フォールバックモデルも利用できません: {fallback_error}")
                return None, f"Both models failed: {primary_error}, {fallback_error}", None
            
    except Exception as e:
        error_msg = f"Gemini client setup error: {str(e)}"
        if DEBUG_MODE:
            st.error(f"🚨 Gemini クライアント設定エラー: {error_msg}")
            st.code(traceback.format_exc())
        return None, error_msg, None

def analyze_sentiment_with_llm(text, client, model_name="gemini-2.5-flash-lite"):
    """新SDK（google-genai）を使った高精度感情分析"""
    if not client:
        if DEBUG_MODE:
            st.warning("⚠️ Gemini client is None, using fallback analysis")
        return simple_sentiment_analysis_fallback(text)
    
    try:
        # システム指示（オープンキャンパス特化）
        system_instruction = """
あなたはオープンキャンパスの感想分析専門AIです。
高校生の感想文を分析して、感情スコアと詳細な感情状態を正確に判定してください。
オープンキャンパス特有の要素（施設見学、模擬授業、学生との交流、進路への影響など）を重視して分析してください。
出力は必ずJSON形式で行い、追加の説明は含めないでください。
"""
        
        # プロンプト
        prompt = f"""
以下のオープンキャンパスに関する感想文を分析してください。

【感想文】
{text}

【出力形式】
以下のJSON形式のみで回答してください：
{{
    "score": [0-100の整数スコア],
    "emotion": "[感情表現]",
    "reason": "[判定理由の簡潔な説明]",
    "keywords": ["抽出されたポジティブ/ネガティブキーワード"]
}}

【スコア基準】
- 90-100: 非常にポジティブ（入学への強い意欲、深い感動）
- 70-89: ポジティブ（満足、興味、好印象）
- 50-69: やや良好（普通に良い、まずまず）
- 30-49: 中立・混在（迷い、どちらでもない）
- 10-29: やや不満（期待外れ、不安）
- 0-9: 非常にネガティブ（強い不満、失望）

【感情表現例】
- 😍 大感動: 90-100点
- 😊 とても満足: 75-89点
- 🙂 満足: 60-74点
- 😐 普通: 45-59点
- 😞 やや不満: 25-44点
- 😢 不満: 0-24点
"""
        
        if DEBUG_MODE:
            st.info(f"🔍 Gemini APIにリクエスト送信中... (モデル: {model_name})")
        
        # 新SDKでAPIリクエスト
        response = client.models.generate_content(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            ),
            contents=prompt
        )
        
        if DEBUG_MODE:
            st.success("✅ Gemini APIから応答受信")
            with st.expander("📄 Gemini生レスポンス"):
                st.code(response.text)
        
        # JSONパースを試行
        try:
            response_text = response.text.strip()
            
            # ```json を除去する処理
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
            
            if DEBUG_MODE:
                st.info("🔧 JSON抽出結果:")
                st.code(response_text)
            
            result = json.loads(response_text)
            
            # 結果の検証
            required_keys = ['score', 'emotion']
            for key in required_keys:
                if key not in result:
                    raise KeyError(f"Required key '{key}' not found in response")
            
            final_result = {
                'score': int(result.get('score', 50)),
                'emotion': result.get('emotion', '😐 普通'),
                'reason': result.get('reason', f'Gemini {model_name} による詳細分析'),
                'keywords': result.get('keywords', [])
            }
            
            if DEBUG_MODE:
                st.success("✅ JSON解析成功")
                st.json(final_result)
            
            return final_result
            
        except (json.JSONDecodeError, ValueError, KeyError) as parse_error:
            if DEBUG_MODE:
                st.warning(f"⚠️ JSON解析エラー: {parse_error}")
                st.info("🔄 フォールバック解析を実行中...")
            return parse_llm_response_fallback(response.text, text, model_name)
            
    except Exception as e:
        error_msg = f"LLM analysis error: {str(e)}"
        if DEBUG_MODE:
            st.error(f"❌ Gemini API エラー: {error_msg}")
            st.code(traceback.format_exc())
        
        # レート制限エラーの場合は特別な処理
        if "429" in str(e) or "quota" in str(e).lower():
            if DEBUG_MODE:
                st.error("🚨 レート制限に達しました。フォールバック分析を使用します。")
            # フォールバックモデルを試行
            if model_name == "gemini-2.5-flash-lite":
                return analyze_sentiment_with_llm(text, client, "gemini-2.0-flash-lite")
        
        return simple_sentiment_analysis_fallback(text)

def parse_llm_response_fallback(response_text, original_text, model_name):
    """LLM応答のパースに失敗した場合のフォールバック"""
    try:
        import re
        
        if DEBUG_MODE:
            st.info("🔧 テキスト解析フォールバック実行中...")
        
        # スコアを正規表現で抽出
        score_patterns = [
            r'(?:score|スコア)[":：]\s*(\d+)',
            r'(\d{1,3})\s*点',
            r'(\d{1,3})\s*pts?'
        ]
        
        score = 50  # デフォルト
        for pattern in score_patterns:
            score_match = re.search(pattern, response_text, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                break
        
        # 感情表現を抽出
        emotion_patterns = [
            r'[😍😊🙂😐😞😢][^0-9\n]*',
            r'(大感動|とても満足|満足|普通|やや不満|不満)',
            r'emotion[":：]\s*"([^"]*)"'
        ]
        
        emotion = "😐 普通"
        for pattern in emotion_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                emotion = match.group(0).strip()
                break
        
        # スコアに基づく感情補正
        if score >= 90:
            emotion = "😍 大感動"
        elif score >= 75:
            emotion = "😊 とても満足"
        elif score >= 60:
            emotion = "🙂 満足"
        elif score >= 45:
            emotion = "😐 普通"
        elif score >= 25:
            emotion = "😞 やや不満"
        else:
            emotion = "😢 不満"
        
        result = {
            'score': max(0, min(100, score)),
            'emotion': emotion,
            'reason': f'Gemini {model_name} の部分解析',
            'keywords': []
        }
        
        if DEBUG_MODE:
            st.success("✅ テキスト解析フォールバック成功")
            st.json(result)
        
        return result
        
    except Exception as e:
        if DEBUG_MODE:
            st.error(f"❌ テキスト解析フォールバックエラー: {e}")
        return simple_sentiment_analysis_fallback(original_text)

def simple_sentiment_analysis_fallback(text):
    """フォールバック用のシンプル分析"""
    if DEBUG_MODE:
        st.warning("⚠️ キーワードベース分析にフォールバック")
    
    positive_words = [
        '楽しい', '嬉しい', '最高', '良い', 'すごい', 'がんばる', '頑張る', 
        '感動', '素晴らしい', 'ありがとう', '大好き', '幸せ', 'やったー',
        '成功', '合格', '勝利', '達成', '完璧', '満足', 'ワクワク',
        '興味深い', '面白い', '魅力的', '素敵', 'かっこいい', '美しい',
        '充実', '発見', '学べる', '勉強になる', '将来', '夢', '希望',
        '入学したい', '通いたい', '憧れ', '目標', 'やる気', 'モチベーション'
    ]
    
    negative_words = [
        '悲しい', '辛い', '大変', '不安', '心配', '疲れた', 'つまらない', 
        '嫌', '困った', 'ダメ', '失敗', '最悪', 'むかつく', 'イライラ',
        '落ち込む', 'がっかり', '残念', '苦しい', '難しい', '分からない',
        '迷う', '悩む', '微妙'
    ]
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    if positive_count > negative_count:
        score = 50 + (positive_count * 10)
    elif negative_count > positive_count:
        score = 50 - (negative_count * 10)
    else:
        score = 50
    
    score = max(0, min(100, score))
    
    if score >= 75:
        emotion = "😊 とても満足"
    elif score >= 60:
        emotion = "🙂 満足"
    elif score >= 40:
        emotion = "😐 普通"
    elif score >= 25:
        emotion = "😞 やや不満"
    else:
        emotion = "😢 不満"
    
    return {
        'score': score,
        'emotion': emotion,
        'reason': 'キーワードベース分析（フォールバック）',
        'keywords': []
    }

# Google Apps Script URL
GAS_URL = st.secrets.get("gas_url", "")

@st.cache_data(ttl=10, show_spinner=False)
def load_posts():
    """投稿を読み込み（キャッシュ付き）"""
    if not GAS_URL:
        return st.session_state.get('posts', [])
    
    try:
        response = requests.get(GAS_URL, timeout=3)
        if response.status_code == 200:
            posts = response.json()
            for post in posts:
                if post.get('time'):
                    try:
                        if isinstance(post['time'], str):
                            time_str = post['time'].replace('Z', '')
                            if '.' in time_str:
                                # 元の投稿時刻を保持
                                post['time'] = datetime.fromisoformat(time_str.split('.')[0])
                            else:
                                post['time'] = datetime.fromisoformat(time_str)
                        # datetimeオブジェクトの場合はそのまま保持
                        elif isinstance(post['time'], datetime):
                            pass  # 変更せずそのまま使用
                    except Exception as time_error:
                        st.warning(f"時刻変換エラー: {time_error} - {post.get('time')}")
                        # エラー時のみ現在時刻を設定
                        post['time'] = datetime.now()
                else:
                    # timeフィールドが存在しない場合のみ現在時刻
                    post['time'] = datetime.now()
            
            # セッション状態にもバックアップ保存
            st.session_state.posts_backup = posts
            return posts
        return st.session_state.get('posts_backup', [])
    except Exception as load_error:
        st.error(f"データ読み込みエラー: {load_error}")
        return st.session_state.get('posts_backup', [])

def save_post(nickname, text, score, emotion, reason, keywords, color):
    """投稿を保存（重複防止・エラーハンドリング強化・モデル情報追加）"""
    # 重複チェック用のハッシュ生成
    import hashlib
    post_hash = hashlib.md5(f"{nickname}{text}{score}".encode()).hexdigest()
    
    # セッション状態に投稿履歴を保存
    if 'post_hashes' not in st.session_state:
        st.session_state.post_hashes = set()
    
    # 重複チェック
    if post_hash in st.session_state.post_hashes:
        st.warning("⚠️ 同じ内容の投稿が既に存在します")
        return False
    
    # モデル情報を取得
    model_info = st.session_state.get('temp_model_info', 'AI分析')
    
    post_data = {
        'user': nickname,
        'text': text,
        'sentiment': score,
        'emotion': emotion,
        'reason': reason,
        'keywords': keywords,
        'model_used': model_info,  # モデル情報を明示的に保存
        'time': datetime.now().isoformat(),
        'color': color,
        'hash': post_hash
    }
    
    if GAS_URL:
        # リトライ機能付きで投稿
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(GAS_URL, json=post_data, timeout=10)
                if response.status_code == 200:
                    # 成功時にハッシュを記録
                    st.session_state.post_hashes.add(post_hash)
                    load_posts.clear()
                    return True
                elif attempt < max_retries - 1:
                    st.warning(f"⏳ 投稿試行中... ({attempt + 1}/{max_retries})")
                    time.sleep(1)  # 1秒待機してリトライ
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    st.warning(f"⏳ 接続中... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    st.error(f"❌ ネットワークエラー: {e}")
        
        return False
    else:
        # ローカル保存
        if 'posts' not in st.session_state:
            st.session_state.posts = []
        post_data['time'] = datetime.now()
        st.session_state.posts.append(post_data)
        st.session_state.post_hashes.add(post_hash)
        return True

def clear_all_posts():
    """すべての投稿をクリア"""
    if GAS_URL:
        try:
            clear_url = GAS_URL + "?action=clear"
            response = requests.get(clear_url, timeout=10)
            
            if response.status_code == 200:
                if 'posts' in st.session_state:
                    del st.session_state['posts']
                if 'confirm_clear' in st.session_state:
                    del st.session_state['confirm_clear']
                load_posts.clear()
                return True
            return False
        except:
            return False
    else:
        st.session_state.posts = []
        if 'confirm_clear' in st.session_state:
            del st.session_state['confirm_clear']
        return True

# メインアプリ
st.title("🎓 感情分析SNS")
st.markdown("**今日のオープンキャンパスはいかがでしたか？AI（Gemini 2.5）が高精度に感想を分析します！**")

# Gemini設定とデバッグ情報
client, setup_status, current_model = setup_gemini()

# 接続状況とリアルタイム更新状態
col_status1, col_status2 = st.columns(2)
with col_status1:
    if GAS_URL:
        st.success("🌐 全参加者で共有中")
    else:
        st.warning("💻 この端末のみ（テストモード）")

with col_status2:
    # スマホ向け手動更新ボタン（メイン画面に配置）
    if st.button("🔄 最新の感想を更新", help="最新の感想を今すぐ確認", key="main_refresh"):
        load_posts.clear()
        st.session_state.last_update = datetime.now()
        # rerunを削除してメッセージのみ表示
        st.success("✅ 更新しました！")

# 成功メッセージの表示（投稿後）
if st.session_state.show_success:
    st.success("✅ 感想を投稿しました！他の参加者にも共有されています 🎉")
    st.balloons()
    st.session_state.show_success = False

# サイドバー
with st.sidebar:
    st.markdown("## 🎯 オープンキャンパス感想SNS")
    if current_model:
        st.markdown(f"**AI powered by {current_model}**")
    else:
        st.markdown("**基本分析モード**")
    
    # 自動更新制御
    st.markdown("## 🔄 更新設定")
    auto_update = st.toggle("自動更新を有効にする", value=st.session_state.auto_update_enabled)
    if auto_update != st.session_state.auto_update_enabled:
        st.session_state.auto_update_enabled = auto_update
        if auto_update:
            st.success("✅ 自動更新を開始しました")
        else:
            st.info("⏸️ 自動更新を停止しました")
    
    # 手動更新ボタン
    if st.button("🔄 今すぐ更新", use_container_width=True):
        load_posts.clear()
        st.session_state.last_update = datetime.now()
        st.rerun()
    
    st.markdown("## 📊 現在の状況")
    posts = load_posts()
    total_posts = len(posts)
    st.metric("参加者の感想", f"{total_posts}件")
    
    if posts:
        avg_score = sum(p['sentiment'] for p in posts) / total_posts
        st.metric("平均満足度", f"{avg_score:.1f}点")
        
        positive_count = len([p for p in posts if p['sentiment'] >= 60])
        st.metric("満足した人", f"{positive_count}人")
    
    st.markdown("---")
    st.markdown("## 💡 投稿のヒント")
    st.markdown("""
    - 🏫 **施設について**：教室、図書館、食堂など
    - 👨‍🏫 **授業や説明**：模擬授業、学科説明
    - 👥 **学生スタッフ**：案内してくれた先輩
    - 🎯 **進路について**：将来の目標や不安
    - 😊 **全体的な印象**：今日の感想
    """)

# 左右のレイアウト
left_col, right_col = st.columns([1, 1])

# 左側：投稿エリア
with left_col:
    st.subheader("📝 感想を投稿しよう！")
    
    # 投稿中の状態制御
    if st.session_state.is_posting:
        st.warning("⏳ 投稿処理中です... しばらくお待ちください")
        st.session_state.is_posting = False
    
    # ニックネーム入力（日本語プレースホルダー）
    nickname = st.text_input(
        "ニックネーム（必須）", 
        placeholder="例：未来の○○大生、理系男子、文学少女など",
        help="📱 タップして入力してください。個人が特定されないニックネームにしてください。",
        disabled=st.session_state.is_posting,
        key="nickname_input"
    )
    
    # 感想入力（日本語プレースホルダー・スマホ対応）
    message = st.text_area(
        "オープンキャンパスの感想をお聞かせください（必須）",
        placeholder="例：模擬授業がとても分かりやすくて、この大学で学びたいと思いました！学生スタッフの皆さんも親切で、キャンパスの雰囲気が素敵でした。",
        height=120,
        help="📱 スマホの方：入力後は画面の他の場所をタップしてください。施設、授業、学生、進路など、どんなことでもOKです！",
        disabled=st.session_state.is_posting,
        key="message_input"
    )
    
    # 入力チェック（厳密な文字数チェック）
    input_valid = nickname and message and len(message.strip()) > 5
    char_count = len(message.strip()) if message else 0
    
    # 入力状態の即座フィードバック（入力欄直下に配置・rerun削除）
    feedback_placeholder = st.empty()
    if not input_valid:
        if not nickname:
            feedback_placeholder.warning("📝 ニックネームを入力してください")
        elif not message:
            feedback_placeholder.warning("📝 感想を入力してください")
        elif char_count <= 5:
            feedback_placeholder.warning(f"📝 感想をもう少し詳しく書いてください（現在{char_count}文字、6文字以上必要）")
    else:
        feedback_placeholder.success(f"✅ 入力完了（{char_count}文字）- AI分析の準備ができました！")
    
    # 感情分析ボタン（明示的な分析開始）
    col_analyze, col_reanalyze = st.columns([3, 1])
    
    with col_analyze:
        analyze_button = st.button(
            "🧠 AI感情分析を開始", 
            type="secondary", 
            use_container_width=True,
            disabled=not input_valid or st.session_state.is_posting
        )
    
    with col_reanalyze:
        # 再分析ボタンは入力が有効で、かつ分析済みの場合のみ有効
        reanalyze_enabled = input_valid and st.session_state.analysis_done and not st.session_state.is_posting
        if st.button("🔄 再分析", help="もう一度AI分析を実行", disabled=not reanalyze_enabled):
            # 既存の分析結果をクリアして再分析（rerunを削除）
            with st.spinner("🤖 再分析中..."):
                analysis_result = analyze_sentiment_with_llm(message, client, current_model)
                st.session_state.analysis_result = analysis_result
                st.session_state.analysis_done = True
                st.success("🔄 再分析完了！結果を確認してください")
    
    # 入力状態の表示を削除（上に移動済み）
    
    # 感情分析実行（rerun削除）
    if analyze_button and input_valid:
        # 分析処理をプログレスバー付きで実行
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("🤖 AIが感想を分析中...")
        progress_bar.progress(30)
        
        # 分析実行
        analysis_result = analyze_sentiment_with_llm(message, client, current_model)
        progress_bar.progress(80)
        
        # セッション状態に保存
        st.session_state.analysis_result = analysis_result
        st.session_state.analysis_done = True
        
        progress_bar.progress(100)
        status_text.text("✅ 分析完了！")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        # rerunを削除してページ更新を回避
    
    # 分析結果の表示
    if st.session_state.analysis_done and st.session_state.analysis_result:
        analysis_result = st.session_state.analysis_result
        score = analysis_result['score']
        emotion = analysis_result['emotion']
        reason = analysis_result.get('reason', '')
        keywords = analysis_result.get('keywords', [])
        
        # 色の決定
        if score >= 75:
            color = "#28a745"
        elif score >= 60:
            color = "#17a2b8"
        elif score >= 40:
            color = "#6c757d"
        elif score >= 25:
            color = "#fd7e14"
        else:
            color = "#dc3545"
        
        # AI分析結果表示
        st.markdown("### 🧠 AI感情分析結果")
        
        col_score, col_model = st.columns([2, 1])
        with col_score:
            st.metric("満足度スコア", f"{score}点", emotion)
        with col_model:
            # 使用モデルを表示（高校生にも分かりやすく・詳細表示）
            if client and "フォールバック" not in reason:
                if current_model == "gemini-2.5-flash-lite":
                    st.success("🤖 Gemini 2.5")
                elif current_model == "gemini-2.0-flash-lite":
                    st.info("🤖 Gemini 2.0")
                else:
                    st.success("🤖 Gemini AI")
            else:
                st.warning("⚙️ 基本分析")
        
        if reason:
            # フォールバック使用時は警告色で表示
            if "フォールバック" in reason:
                st.warning(f"💭 分析理由: {reason}")
            else:
                st.info(f"💭 分析理由: {reason}")
        
        if keywords:
            st.markdown(f"**🔍 キーワード:** {', '.join(keywords)}")
        
        # AIモデル情報の保存（reasonとは別フィールド）
        ai_model_info = ""
        if client and "フォールバック" not in reason:
            if current_model == "gemini-2.5-flash-lite":
                ai_model_info = "🤖 Gemini 2.5で分析"
                # 投稿データにモデル情報を追加
                st.session_state.temp_model_info = "Gemini 2.5"
            elif current_model == "gemini-2.0-flash-lite":
                ai_model_info = "🤖 Gemini 2.0で分析"
                st.session_state.temp_model_info = "Gemini 2.0"
            else:
                ai_model_info = "🤖 Gemini AIで分析"
                st.session_state.temp_model_info = "Gemini AI"
        else:
            ai_model_info = "⚙️ 基本分析で処理"
            st.session_state.temp_model_info = "基本分析"
        
        st.markdown(f"""
        <div class="post-card" style="--border-color: {color};">
            <div class="post-header">
                <span class="post-user">👤 {nickname}</span>
                <span class="post-time">⏰ 分析完了</span>
            </div>
            <div class="post-emotion" style="color: {color};">
                {emotion} ({score}点)
            </div>
            <div class="post-text">
                💬 {message}
            </div>
            <div class='post-analysis'>{ai_model_info}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 投稿ボタン（分析後のみ表示・重複防止強化）
        if st.button("🚀 感想を投稿する！", type="primary", use_container_width=True, disabled=st.session_state.is_posting):
            st.session_state.is_posting = True
            
            # 投稿処理の詳細表示
            with st.spinner("📤 投稿処理中... しばらくお待ちください"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🔗 サーバーに接続中...")
                progress_bar.progress(25)
                time.sleep(0.5)
                
                status_text.text("📤 データを送信中...")
                progress_bar.progress(50)
                
                success = save_post(nickname, message, score, emotion, reason, keywords, color)
                progress_bar.progress(75)
                
                if success:
                    status_text.text("✅ 投稿完了！")
                    progress_bar.progress(100)
                    time.sleep(1)
                    
                    # 投稿成功後、フォームをクリア
                    st.session_state.analysis_result = None
                    st.session_state.analysis_done = False
                    st.session_state.show_success = True
                    st.session_state.is_posting = False
                    
                    # セッション状態をクリアして入力欄をリセット
                    if "nickname_input" in st.session_state:
                        del st.session_state["nickname_input"]
                    if "message_input" in st.session_state:
                        del st.session_state["message_input"]
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    # rerunを削除して、代わりに成功メッセージのみ表示
                    st.session_state.show_success = True
                    st.balloons()
                    
                    # フォームクリアのみ実行（rerun削除）
                    st.session_state.analysis_result = None
                    st.session_state.analysis_done = False
                    st.session_state.is_posting = False
                    
                    # 入力欄クリア
                    if "nickname_input" in st.session_state:
                        del st.session_state["nickname_input"]
                    if "message_input" in st.session_state:
                        del st.session_state["message_input"]
                else:
                    progress_bar.empty()
                    status_text.empty()
                    st.error("❌ 投稿に失敗しました。ネットワーク接続を確認して、もう一度お試しください。")
                    st.session_state.is_posting = False
    
    # 使い方ガイド
    st.markdown("---")
    st.markdown("### 📱 使い方ガイド")
    st.markdown("""
    **📝 手順**
    1. ニックネームを入力
    2. 感想を詳しく入力（5文字以上）
    3. 「🧠 AI感情分析を開始」ボタンをタップ
    4. 分析結果を確認
    5. 「🚀 感想を投稿する！」ボタンで投稿
    
    **💡 コツ**
    - 感想は具体的に書くほど分析精度が向上します
    - 模擬授業、学科説明、データサイエンス体験コーナー、学生スタッフ、施設などについて書いてみてください
    """)

# 右側：投稿一覧
with right_col:
    # ヘッダーに手動更新ボタンを配置
    col_title, col_refresh = st.columns([3, 1])
    with col_title:
        st.subheader("🌟 みんなの感想")
    with col_refresh:
        if st.button("🔄 更新", help="最新の感想を取得", key="posts_refresh"):
            load_posts.clear()
            st.session_state.last_update = datetime.now()
            # rerunを削除
            st.success("✅ 更新完了")
    
    if posts:
        # 統計
        avg_score = sum(p['sentiment'] for p in posts) / total_posts
        satisfied_count = len([p for p in posts if p['sentiment'] >= 60])
        
        st.markdown("### 📊 参加者の声")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総感想数", f"{total_posts}件")
        with col2:
            st.metric("平均満足度", f"{avg_score:.1f}点")
        with col3:
            satisfaction_rate = (satisfied_count / total_posts) * 100
            st.metric("満足率", f"{satisfaction_rate:.0f}%")
        
        # 投稿一覧（最新10件）- 新しいものを上に表示
        st.markdown("### 💬 最新の感想（新しい順）")
        
        # 時刻でソート
        for post in posts:
            if not isinstance(post.get('time'), datetime):
                try:
                    if isinstance(post.get('time'), str):
                        time_str = post['time'].replace('Z', '')
                        if '.' in time_str:
                            post['time'] = datetime.fromisoformat(time_str.split('.')[0])
                        else:
                            post['time'] = datetime.fromisoformat(time_str)
                    else:
                        post['time'] = datetime.now()
                except:
                    post['time'] = datetime.now()
        
        # 新しい順にソート（降順）- 正確なソート
        try:
            recent_posts = sorted(
                posts, 
                key=lambda x: x.get('time', datetime.min) if isinstance(x.get('time'), datetime) else datetime.min, 
                reverse=True
            )[:10]
        except Exception as sort_error:
            # ソートエラー時はそのまま使用
            recent_posts = posts[:10]
        
        # 現在時刻を一度だけ取得
        current_time = datetime.now()
        
        for i, post in enumerate(recent_posts):
            post_time = post.get('time')
            
            # 時刻データの正規化
            if isinstance(post_time, str):
                try:
                    time_str = post_time.replace('Z', '')
                    if '.' in time_str:
                        post_time = datetime.fromisoformat(time_str.split('.')[0])
                    else:
                        post_time = datetime.fromisoformat(time_str)
                except:
                    post_time = datetime.now()
            elif not isinstance(post_time, datetime):
                post_time = datetime.now()
            
            # 時間差計算（固定時刻を使用）
            diff = current_time - post_time
            
            # より正確な時間表示
            total_seconds = max(0, int(diff.total_seconds()))  # 負の値を防ぐ
            if total_seconds < 60:
                time_str = f"{total_seconds}秒前"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                time_str = f"{minutes}分前"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                time_str = f"{hours}時間前"
            else:
                time_str = post_time.strftime('%m/%d %H:%M')
            
            # 分析理由やキーワード、使用モデルの表示（改善版）
            analysis_info = ""
            if post.get('reason'):
                analysis_info += f"<div class='post-analysis'>💭 {post['reason']}</div>"
            if post.get('keywords') and len(post['keywords']) > 0:
                keywords_str = ', '.join(post['keywords'][:3])
                analysis_info += f"<div class='post-analysis'>🔍 {keywords_str}</div>"
            
            # 使用AIモデルの表示（model_usedフィールドを優先使用）
            if post.get('model_used'):
                # 新しいmodel_usedフィールドがある場合
                model_used = post['model_used']
                if model_used == "Gemini 2.5":
                    analysis_info += f"<div class='post-analysis'>🤖 Gemini 2.5で分析</div>"
                elif model_used == "Gemini 2.0":
                    analysis_info += f"<div class='post-analysis'>🤖 Gemini 2.0で分析</div>"
                elif model_used == "Gemini AI":
                    analysis_info += f"<div class='post-analysis'>🤖 Gemini AIで分析</div>"
                elif model_used == "基本分析":
                    analysis_info += f"<div class='post-analysis'>⚙️ 基本分析で処理</div>"
                else:
                    analysis_info += f"<div class='post-analysis'>🤖 {model_used}で分析</div>"
            elif post.get('reason'):
                # 古い投稿でmodel_usedがない場合、reasonから推測
                reason_text = post['reason']
                
                # reasonからの推測（フォールバック）
                if "gemini" in reason_text.lower() and "フォールバック" not in reason_text:
                    analysis_info += f"<div class='post-analysis'>🤖 Gemini AIで分析</div>"
                elif "フォールバック" in reason_text or "キーワードベース" in reason_text:
                    analysis_info += f"<div class='post-analysis'>⚙️ 基本分析で処理</div>"
                else:
                    analysis_info += f"<div class='post-analysis'>🤖 AI分析</div>"
            else:
                # reasonもない古い投稿
                analysis_info += f"<div class='post-analysis'>🤖 AI分析（詳細不明）</div>"
            
            # スマホ対応投稿表示（HTMLの改善）
            st.markdown(f"""
            <div class="post-card" style="--border-color: {post['color']};">
                <div class="post-header">
                    <span class="post-user">👤 {post['user']}</span>
                    <span class="post-time">⏰ {time_str}</span>
                </div>
                <div class="post-emotion" style="color: {post['color']};">
                    {post['emotion']} ({post['sentiment']}点)
                </div>
                <div class="post-text">
                    💬 {post['text']}
                </div>
                {analysis_info}
            </div>
            """, unsafe_allow_html=True)
        
        # グラフ表示（スマホ対応・操作説明付き）
        if len(posts) > 2:
            st.markdown("### 📈 満足度の推移")
            
            # グラフ操作説明
            with st.expander("📱 グラフの操作方法"):
                st.markdown("""
                **スマホでの操作**
                - **ピンチイン/アウト**: グラフを拡大・縮小
                - **スワイプ**: グラフを左右にスクロール
                - **ダブルタップ**: 元の表示に戻る
                
                **パソコンでの操作**
                - **マウスホイール**: 拡大・縮小
                - **ドラッグ**: グラフを移動
                - **ダブルクリック**: 元の表示に戻る
                """)
            
            df = pd.DataFrame(posts)
            df = df.sort_values('time')
            df['感想順'] = range(1, len(df) + 1)
            
            # スマホ対応のグラフ設定（エラー修正）
            try:
                fig = go.Figure()
                
                # 満足度ラインの追加
                fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                             annotation_text="普通(50点)", annotation_position="bottom right")
                fig.add_hline(y=60, line_dash="dot", line_color="green", 
                             annotation_text="満足ライン(60点)", annotation_position="top right")
                
                # メインデータの追加
                fig.add_trace(go.Scatter(
                    x=df['感想順'],
                    y=df['sentiment'],
                    mode='lines+markers',
                    name='満足度スコア',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8, color='#1f77b4'),
                    hovertemplate='<b>%{customdata[0]}</b><br>' +
                                 '満足度: %{y}点<br>' +
                                 '感想: %{customdata[1]}<extra></extra>',
                    customdata=df[['user', 'text']].values
                ))
                
                # スマホ対応レイアウト（エラー対策）
                fig.update_layout(
                    title='参加者の満足度スコア推移（AI分析）',
                    height=400,
                    yaxis_title="満足度スコア",
                    xaxis_title="投稿順",
                    showlegend=False,
                    dragmode='pan',
                    margin=dict(l=50, r=20, t=50, b=50)
                )
                
                # Y軸の範囲を固定（0-100）
                fig.update_yaxes(range=[0, 100])
                
                st.plotly_chart(fig, use_container_width=True, config={
                    'displayModeBar': False,  # ツールバーを非表示にしてエラー回避
                    'displaylogo': False
                })
                
            except Exception as plot_error:
                st.error(f"グラフ表示エラー: {plot_error}")
                # 代替として簡単な統計を表示
                st.markdown("### 📊 満足度データ")
                st.line_chart(df.set_index('感想順')['sentiment'])
            
            # 感情の分布（簡単操作・エラー対策）
            st.markdown("### 🎭 満足度分布")
            emotion_counts = df['emotion'].value_counts()
            
            try:
                fig2 = go.Figure(data=[go.Pie(
                    labels=emotion_counts.index,
                    values=emotion_counts.values,
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='outside'
                )])
                
                fig2.update_layout(
                    title="参加者の満足度分布（AI分析）",
                    height=400,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                    margin=dict(l=20, r=20, t=50, b=50)
                )
                
                st.plotly_chart(fig2, use_container_width=True, config={
                    'displayModeBar': False,
                    'displaylogo': False
                })
                
            except Exception as pie_error:
                st.error(f"円グラフ表示エラー: {pie_error}")
                # 代替として棒グラフを表示
                st.bar_chart(emotion_counts)
            
            # 簡単な統計情報
            st.markdown("### 📈 かんたん統計")
            col_stats1, col_stats2 = st.columns(2)
            with col_stats1:
                st.info(f"**最高スコア**: {df['sentiment'].max()}点")
                st.info(f"**最低スコア**: {df['sentiment'].min()}点")
            with col_stats2:
                st.info(f"**スコア幅**: {df['sentiment'].max() - df['sentiment'].min()}点")
                high_satisfaction = (df['sentiment'] >= 80).sum()
                st.info(f"**高満足(80点以上)**: {high_satisfaction}人")
    
    else:
        # デバイス判定に基づく案内
        st.info("💬 まだ感想がありません。最初の投稿をお待ちしています！")
        
        # デバイス別案内（レスポンシブ対応・背景色修正）
        st.markdown("""
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #ffeaa7;">
            <h4 style="color: #856404; margin-top: 0;">📱 投稿方法</h4>
            <div class="pc-only" style="display: block; color: #856404;">
                <strong>パソコンの方：</strong> 左側の「📝 感想を投稿しよう！」エリアから投稿できます
            </div>
            <div class="mobile-only" style="display: none; color: #856404;">
                <strong>スマホの方：</strong> 上にスクロールすると「📝 感想を投稿しよう！」エリアがあります
            </div>
        </div>
        
        <style>
        @media (max-width: 768px) {
            .pc-only { display: none !important; }
            .mobile-only { display: block !important; }
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        ### 🎓 オープンキャンパスへようこそ！
        
        **🤖 AI（Gemini 2.5）が感想を高精度分析します**
        
        今日の体験はいかがですか？
        - 🏫 **施設見学**の印象
        - 👨‍🏫 **模擬授業**の感想  
        - 👥 **学生との交流**について
        - 🎯 **進路への想い**
        - 😊 **全体的な感想**
        
        どんな小さなことでも大歓迎です！
        AIがあなたの感情を詳しく分析してくれます。
        """)

# 自動更新処理（非ブロッキング・rerun削除）
if st.session_state.auto_update_enabled:
    time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()
    if time_since_update >= 30:
        # 自動更新はキャッシュクリアのみで、rerunはしない
        load_posts.clear()
        st.session_state.last_update = datetime.now()

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    🎓 感情分析SNS | AI感情分析 powered by Gemini 2.5<br>
    <small>💡 200名規模対応・レート制限最適化済み</small><br>
    <small>📱 スマホ完全対応・高校生向けUI</small><br>
    <small>画面が固まる場合は、サイドバーで「自動更新」をオフにしてください</small><br>
    ご参加いただき、ありがとうございました！
</div>
""", unsafe_allow_html=True)