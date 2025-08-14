import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import requests
import time
import google.generativeai as genai

# ページ設定
st.set_page_config(page_title="オープンキャンパス感想SNS", page_icon="🎓", layout="wide")

# Gemini API設定
@st.cache_resource
def setup_gemini():
    """Gemini APIの設定"""
    api_key = st.secrets.get("gemini_api_key", "")
    if not api_key:
        st.error("🚨 Gemini API keyが設定されていません。secrets.tomlに'gemini_api_key'を追加してください。")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    return model

def analyze_sentiment_with_llm(text, model):
    """LLMを使った高精度感情分析"""
    if not model:
        # フォールバック: シンプル分析
        return simple_sentiment_analysis_fallback(text)
    
    try:
        prompt = f"""
以下のオープンキャンパスに関する感想文を分析して、感情スコアと詳細な感情状態を判定してください。

【感想文】
{text}

【出力形式】
以下のJSON形式で回答してください：
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

オープンキャンパス特有のポイント（施設、授業、学生、進路への影響など）を考慮して分析してください。
"""
        
        response = model.generate_content(prompt)
        
        # JSONパースを試行
        try:
            # レスポンステキストからJSONを抽出
            response_text = response.text.strip()
            
            # ```json を除去する処理
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
            
            result = json.loads(response_text)
            
            return {
                'score': int(result.get('score', 50)),
                'emotion': result.get('emotion', '😐 普通'),
                'reason': result.get('reason', ''),
                'keywords': result.get('keywords', [])
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            st.warning(f"⚠️ LLM応答のパースに失敗: {e}")
            # テキストから数値を抽出する簡易フォールバック
            return parse_llm_response_fallback(response.text, text)
            
    except Exception as e:
        st.warning(f"⚠️ LLM分析でエラー: {e}")
        # フォールバック分析
        return simple_sentiment_analysis_fallback(text)

def parse_llm_response_fallback(response_text, original_text):
    """LLM応答のパースに失敗した場合のフォールバック"""
    try:
        # スコアを正規表現で抽出
        import re
        score_match = re.search(r'(?:score|スコア)[":：]\s*(\d+)', response_text, re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))
        else:
            # 数字を探す
            numbers = re.findall(r'\b\d{1,3}\b', response_text)
            score = int(numbers[0]) if numbers else 50
        
        # 感情表現を抽出
        emotion_patterns = [
            r'[😍😊🙂😐😞😢][^0-9\n]*',
            r'(とても満足|満足|普通|やや不満|不満|大感動)',
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
        
        return {
            'score': max(0, min(100, score)),
            'emotion': emotion,
            'reason': 'LLMによる自動分析',
            'keywords': []
        }
        
    except Exception as e:
        return simple_sentiment_analysis_fallback(original_text)

def simple_sentiment_analysis_fallback(text):
    """フォールバック用のシンプル分析（元のロジック改良版）"""
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
    
    # 感情判定
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

def load_posts():
    """投稿を読み込み"""
    if not GAS_URL:
        return st.session_state.get('posts', [])
    
    try:
        response = requests.get(GAS_URL, timeout=10)
        if response.status_code == 200:
            posts = response.json()
            for post in posts:
                if post.get('time'):
                    try:
                        if isinstance(post['time'], str):
                            time_str = post['time'].replace('Z', '')
                            if '.' in time_str:
                                post['time'] = datetime.fromisoformat(time_str.split('.')[0])
                            else:
                                post['time'] = datetime.fromisoformat(time_str)
                        elif not isinstance(post['time'], datetime):
                            post['time'] = datetime.now()
                    except:
                        post['time'] = datetime.now()
                else:
                    post['time'] = datetime.now()
            return posts
        return []
    except:
        return st.session_state.get('posts', [])

def save_post(nickname, text, score, emotion, reason, keywords, color):
    """投稿を保存"""
    post_data = {
        'user': nickname,
        'text': text,
        'sentiment': score,
        'emotion': emotion,
        'reason': reason,
        'keywords': keywords,
        'time': datetime.now().isoformat(),
        'color': color
    }
    
    if GAS_URL:
        try:
            response = requests.post(GAS_URL, json=post_data, timeout=10)
            return response.status_code == 200
        except:
            return False
    else:
        # ローカル保存
        if 'posts' not in st.session_state:
            st.session_state.posts = []
        post_data['time'] = datetime.now()
        st.session_state.posts.append(post_data)
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
st.title("🎓 オープンキャンパス感想SNS")
st.markdown("**今日のオープンキャンパスはいかがでしたか？AI（Gemini）が高精度に感想を分析します！**")

# Gemini設定
model = setup_gemini()

# 接続状況
col_status1, col_status2 = st.columns(2)
with col_status1:
    if GAS_URL:
        st.success("🌐 全参加者でリアルタイム共有中！")
    else:
        st.warning("💻 ローカルモード（この端末のみ）")

with col_status2:
    if model:
        st.success("🤖 AI分析：Gemini 2.0 Flash 稼働中")
    else:
        st.error("⚠️ AI分析：フォールバックモード")

# 自動更新
auto_update = st.checkbox("🔄 自動更新（15秒ごと）", value=True)

# サイドバー
with st.sidebar:
    st.markdown("## 🎯 オープンキャンパス感想SNS")
    st.markdown("**AI powered by Gemini 2.0**")
    
    st.markdown("## 📊 現在の状況")
    posts = load_posts()
    total_posts = len(posts)
    st.metric("参加者の感想", f"{total_posts}件")
    
    if posts:
        avg_score = sum(p['sentiment'] for p in posts) / total_posts
        st.metric("平均満足度", f"{avg_score:.1f}点")
        
        positive_count = len([p for p in posts if p['sentiment'] >= 60])
        st.metric("満足した人", f"{positive_count}人")
        
        if model:
            st.success("🧠 高精度AI分析中")
        else:
            st.warning("⚙️ 基本分析モード")
    
    st.markdown("---")
    st.markdown("## ⚙️ 管理機能")
    
    # パスワード認証
    admin_password = st.text_input("管理者パスワード", type="password")
    
    if admin_password == st.secrets.get("admin_password", "opencampus2024"):
        st.success("✅ 管理者として認証されました")
        
        # データクリア機能
        col_clear1, col_clear2 = st.columns(2)
        
        with col_clear1:
            if st.button("🗑️ 全データを削除", type="secondary"):
                if st.session_state.get('confirm_clear', False):
                    with st.spinner("データを削除中..."):
                        if clear_all_posts():
                            st.success("✅ 全データを削除しました")
                            st.session_state.confirm_clear = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 削除に失敗しました")
                            st.session_state.confirm_clear = False
                else:
                    st.warning("⚠️ もう一度クリックで確定")
                    st.session_state.confirm_clear = True
        
        with col_clear2:
            if st.button("🔄 キャッシュクリア", type="secondary"):
                for key in list(st.session_state.keys()):
                    if key.startswith('posts') or key == 'posts':
                        del st.session_state[key]
                st.success("✅ キャッシュをクリアしました")
                st.rerun()
        
        # データエクスポート
        if posts:
            export_data = json.dumps(posts, ensure_ascii=False, indent=2, default=str)
            st.download_button(
                "📄 感想データをダウンロード",
                data=export_data,
                file_name=f"opencampus_feedback_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
    
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
    
    nickname = st.text_input(
        "ニックネーム", 
        placeholder="例：未来の○○大生、理系男子、文学少女など",
        help="個人が特定されないニックネームを入力してください"
    )
    
    message = st.text_area(
        "オープンキャンパスの感想をお聞かせください",
        placeholder="例：模擬授業がとても分かりやすくて、この大学で学びたいと思いました！学生スタッフの皆さんも親切で、キャンパスの雰囲気が素敵でした。",
        height=120,
        help="施設、授業、学生、進路など、どんなことでもOKです！"
    )
    
    # リアルタイム分析
    if message and nickname and len(message.strip()) > 5:
        with st.spinner("🤖 AIが感想を分析中..."):
            analysis_result = analyze_sentiment_with_llm(message, model)
        
        score = analysis_result['score']
        emotion = analysis_result['emotion']
        reason = analysis_result.get('reason', '')
        keywords = analysis_result.get('keywords', [])
        
        # 色の決定
        if score >= 75:
            color = "#28a745"  # 緑
        elif score >= 60:
            color = "#17a2b8"  # 青
        elif score >= 40:
            color = "#6c757d"  # グレー
        elif score >= 25:
            color = "#fd7e14"  # オレンジ
        else:
            color = "#dc3545"  # 赤
        
        # AI分析結果表示
        st.markdown("### 🧠 AI感情分析結果")
        
        col_score, col_model = st.columns([2, 1])
        with col_score:
            st.metric("満足度スコア", f"{score}点", emotion)
        with col_model:
            if model:
                st.success("Gemini 2.0")
            else:
                st.warning("基本分析")
        
        if reason:
            st.info(f"💭 分析理由: {reason}")
        
        if keywords:
            st.markdown(f"**🔍 キーワード:** {', '.join(keywords)}")
        
        # プレビュー
        st.markdown(f"""
        <div style="
            border-left: 5px solid {color}; 
            padding: 15px; 
            background-color: #f8f9fa;
            border-radius: 10px;
            margin: 10px 0;
        ">
            <strong>👤 {nickname}</strong><br>
            <span style="color: {color}; font-weight: bold;">{emotion} ({score}点)</span><br>
            <div style="margin-top: 10px; font-size: 16px;">💬 {message}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 投稿ボタン
        if st.button("🚀 感想を投稿する！", type="primary", use_container_width=True):
            if save_post(nickname, message, score, emotion, reason, keywords, color):
                st.success("✅ 感想を投稿しました！AIの分析結果も含めて共有されます 🎉")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ 投稿に失敗しました。もう一度お試しください。")

# 右側：投稿一覧
with right_col:
    st.subheader("🌟 みんなの感想")
    
    if st.button("🔄 最新の感想を見る"):
        st.rerun()
    
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
        
        # 投稿一覧（最新10件）
        st.markdown("### 💬 最新の感想")
        
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
        
        recent_posts = sorted(posts, key=lambda x: x.get('time', datetime.min), reverse=True)[:10]
        
        for post in recent_posts:
            post_time = post.get('time')
            
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
            
            # 時間差計算
            now = datetime.now()
            diff = now - post_time
            
            if diff.total_seconds() < 60:
                time_str = f"{int(diff.total_seconds())}秒前"
            elif diff.total_seconds() < 3600:
                time_str = f"{int(diff.total_seconds() / 60)}分前"
            else:
                time_str = post_time.strftime('%H:%M')
            
            # 分析理由やキーワードの表示
            analysis_info = ""
            if post.get('reason'):
                analysis_info += f"<br><small>💭 {post['reason']}</small>"
            if post.get('keywords') and len(post['keywords']) > 0:
                keywords_str = ', '.join(post['keywords'][:3])  # 最初の3つだけ
                analysis_info += f"<br><small>🔍 {keywords_str}</small>"
            
            # 投稿表示
            st.markdown(f"""
            <div style="
                border-left: 5px solid {post['color']}; 
                padding: 15px; 
                margin: 10px 0; 
                background-color: #f8f9fa;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; justify-content: space-between;">
                    <strong>👤 {post['user']}</strong>
                    <small style="color: #666;">⏰ {time_str}</small>
                </div>
                <div style="color: {post['color']}; font-weight: bold; margin: 8px 0;">
                    {post['emotion']} ({post['sentiment']}点)
                </div>
                <div style="font-size: 16px; margin-top: 10px; line-height: 1.4;">
                    💬 {post['text']}
                </div>
                {analysis_info}
            </div>
            """, unsafe_allow_html=True)
        
        # グラフ表示
        if len(posts) > 2:
            st.markdown("### 📈 満足度の推移")
            df = pd.DataFrame(posts)
            df = df.sort_values('time')
            df['感想順'] = range(1, len(df) + 1)
            
            fig = px.line(
                df, 
                x='感想順', 
                y='sentiment',
                title='参加者の満足度スコア推移（AI分析）',
                markers=True,
                hover_data=['user', 'text']
            )
            fig.update_layout(
                height=300,
                yaxis_title="満足度スコア",
                xaxis_title="投稿順"
            )
            fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="普通(50点)")
            fig.add_hline(y=60, line_dash="dot", line_color="green", annotation_text="満足ライン(60点)")
            st.plotly_chart(fig, use_container_width=True)
            
            # 感情の分布
            st.markdown("### 🎭 満足度分布")
            emotion_counts = df['emotion'].value_counts()
            fig2 = px.pie(
                values=emotion_counts.values, 
                names=emotion_counts.index,
                title="参加者の満足度分布（AI分析）"
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    else:
        st.info("まだ感想がありません。左側から感想を投稿してみてください！")
        
        st.markdown("""
        ### 🎓 オープンキャンパスへようこそ！
        
        **🤖 AI（Gemini 2.0）が感想を高精度分析します**
        
        今日の体験はいかがですか？
        - 🏫 **施設見学**の印象
        - 👨‍🏫 **模擬授業**の感想  
        - 👥 **学生との交流**について
        - 🎯 **進路への想い**
        - 😊 **全体的な感想**
        
        どんな小さなことでも大歓迎です！
        AIがあなたの感情を詳しく分析してくれます。
        """)

# 自動更新
if auto_update:
    time.sleep(15)
    st.rerun()

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    🎓 オープンキャンパス感想SNS | AI感情分析 powered by Gemini 2.0<br>
    ご参加いただき、ありがとうございました！
</div>
""", unsafe_allow_html=True)
