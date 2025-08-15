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

# メインアプリ
            return False
        except:
            return False
    else:
        st.session_state.posts = []
        if 'confirm_clear' in st.session_state:
            del st.session_state['confirm_clear']
        return True
st.title("🎓 オープンキャンパス感想SNS")
st.markdown("**今日のオープンキャンパスはいかがでしたか？AI（Gemini 2.5）が高精度に感想を分析します！**")

# Gemini設定とデバッグ情報
client, setup_status, current_model = setup_gemini()

# 接続状況とリアルタイム更新状態
col_status1, col_status2, col_status3 = st.columns(3)
with col_status1:
    if GAS_URL:
        st.success("🌐 全参加者で共有中")
    else:
        st.warning("💻 ローカルモード")

with col_status2:
    if client:
        # 正確なモデル表示
        if current_model == "gemini-2.5-flash-lite":
            st.success("🤖 AI分析：Gemini 2.5")
        elif current_model == "gemini-2.0-flash-lite":
            st.success("🤖 AI分析：Gemini 2.0")
        else:
            st.success("🤖 AI分析：稼働中")
    else:
        st.error("⚠️ 基本分析モード")

with col_status3:
    now = datetime.now()
    time_since_update = (now - st.session_state.last_update).total_seconds()
    if st.session_state.auto_update_enabled and time_since_update < 30:
        st.info(f"🔄 最新更新: {int(time_since_update)}秒前")
    else:
        st.info("⏸️ 更新停止中")

# レート制限情報の表示
if client:
    if current_model == "gemini-2.5-flash-lite":
        st.info("📊 **Gemini 2.5 Flash-Lite**: 15RPM, 250,000TPM - オープンキャンパス最適化")
    elif current_model == "gemini-2.0-flash-lite":
        st.warning("📊 **Gemini 2.0 Flash-Lite**: 30RPM, 1,000,000TPM - フォールバックモード")

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
        help="📱 タップして感想を入力してください。施設、授業、学生、進路など、どんなことでもOKです！",
        disabled=st.session_state.is_posting,
        key="message_input"
    )
    
    # 入力チェック
    input_valid = nickname and message and len(message.strip()) > 5
    
    # 感情分析ボタン（明示的な分析開始）
    col_analyze, col_reset = st.columns([3, 1])
    
    with col_analyze:
        analyze_button = st.button(
            "🧠 AI感情分析を開始", 
            type="secondary", 
            use_container_width=True,
            disabled=not input_valid or st.session_state.is_posting
        )
    
    with col_reset:
        if st.button("🔄", help="分析結果をリセット", disabled=st.session_state.is_posting):
            st.session_state.analysis_result = None
            st.session_state.analysis_done = False
            st.rerun()
    
    # 入力不備の案内
    if not input_valid:
        if not nickname:
            st.warning("📝 ニックネームを入力してください")
        elif not message:
            st.warning("📝 感想を入力してください")
        elif len(message.strip()) <= 5:
            st.warning("📝 感想をもう少し詳しく書いてください（5文字以上）")
    
    # 感情分析実行
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
        
        st.rerun()
    
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
            # 正確なモデル表示の修正
            if client and "フォールバック" not in reason:
                if current_model == "gemini-2.5-flash-lite":
                    st.success("Gemini 2.5")
                elif current_model == "gemini-2.0-flash-lite":
                    st.success("Gemini 2.0")
                else:
                    st.success("Gemini AI")
            else:
                st.warning("基本分析")
        
        if reason:
            # フォールバック使用時は警告色で表示
            if "フォールバック" in reason:
                st.warning(f"💭 分析理由: {reason}")
            else:
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
            <div style="margin-top: 10px; font-size: 16px;">{message}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 投稿ボタン（分析後のみ表示）
        if st.button("🚀 感想を投稿する！", type="primary", use_container_width=True, disabled=st.session_state.is_posting):
            st.session_state.is_posting = True
            
            with st.spinner("📤 投稿中... しばらくお待ちください"):
                success = save_post(nickname, message, score, emotion, reason, keywords, color)
            
            if success:
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
                
                st.rerun()
            else:
                st.error("❌ 投稿に失敗しました。もう一度お試しください。")
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
    - 施設、授業、学生、進路について書いてみてください
    """)

# 右側：投稿一覧
with right_col:
    st.subheader("🌟 みんなの感想")
    
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
        
        # 投稿一覧（最新10件）- スマホ対応改善
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
        
        for i, post in enumerate(recent_posts):
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
                analysis_info += f"<div class='post-analysis'>💭 {post['reason']}</div>"
            if post.get('keywords') and len(post['keywords']) > 0:
                keywords_str = ', '.join(post['keywords'][:3])
                analysis_info += f"<div class='post-analysis'>🔍 {keywords_str}</div>"
            
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
            
            # スマホ対応のグラフ設定
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
            
            # スマホ対応レイアウト
            fig.update_layout(
                title='参加者の満足度スコア推移（AI分析）',
                height=400,
                yaxis_title="満足度スコア",
                xaxis_title="投稿順",
                showlegend=False,
                # スマホでの操作を改善
                dragmode='pan',  # デフォルトをパンモードに
                scrollZoom=True,  # スクロールズーム有効
                doubleClick='reset',  # ダブルクリックでリセット
                # ツールバーを簡略化
                modebar=dict(
                    remove=['select2d', 'lasso2d', 'autoScale2d', 'resetScale2d'],
                    orientation='v'
                ),
                # スマホ用マージン調整
                margin=dict(l=50, r=20, t=50, b=50)
            )
            
            # Y軸の範囲を固定（0-100）
            fig.update_yaxes(range=[0, 100])
            
            st.plotly_chart(fig, use_container_width=True, config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
                'toImageButtonOptions': {'format': 'png', 'filename': 'satisfaction_trend'}
            })
            
            # 感情の分布（簡単操作）
            st.markdown("### 🎭 満足度分布")
            emotion_counts = df['emotion'].value_counts()
            
            fig2 = go.Figure(data=[go.Pie(
                labels=emotion_counts.index,
                values=emotion_counts.values,
                hole=0.3,  # ドーナツ型にして見やすく
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
                'displayModeBar': False,  # 円グラフは操作不要なのでツールバー非表示
                'displaylogo': False
            })
            
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
        st.info("まだ感想がありません。左側から感想を投稿してみてください！")
        
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

# 自動更新処理（非ブロッキング）
if st.session_state.auto_update_enabled:
    time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()
    if time_since_update >= 30:
        load_posts.clear()
        st.session_state.last_update = datetime.now()
        st.info("🔄 新しい感想をチェック中...")
        time.sleep(1)
        st.rerun()

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    🎓 オープンキャンパス感想SNS | AI感情分析 powered by Gemini 2.5<br>
    <small>💡 200名規模対応・レート制限最適化済み</small><br>
    <small>📱 スマホ完全対応・高校生向けUI</small><br>
    <small>画面が固まる場合は、サイドバーで「自動更新」をオフにしてください</small><br>
    ご参加いただき、ありがとうございました！
</div>
""", unsafe_allow_html=True)import streamlit as st
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
st.set_page_config(page_title="オープンキャンパス感想SNS", page_icon="🎓", layout="wide")

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

# デバッグモード切り替え
DEBUG_MODE = st.secrets.get("debug_mode", False)

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

@st.cache_data(ttl=30)
def load_posts():
    """投稿を読み込み（キャッシュ付き）"""
    if not GAS_URL:
        return st.session_state.get('posts', [])
    
    try:
        response = requests.get(GAS_URL, timeout=5)
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
    """投稿を保存（非同期対応）"""
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
            response = requests.post(GAS_URL, json=post_data, timeout=5)
            success = response.status_code == 200
            if success:
                load_posts.clear()
            return success
        except:
            return False
    else:
        if 'posts' not in st.session_state:
            st.session_state.posts = []
        post_data['time'] = datetime.now()
        st.session_state.posts.append(post_data)
        return True

def clear_all