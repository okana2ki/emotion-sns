import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import requests
import time

# ページ設定
st.set_page_config(page_title="みんなの感情SNS", page_icon="😊", layout="wide")

# 感情分析（シンプル版）
def simple_sentiment_analysis(text):
    """シンプルな感情分析"""
    # ポジティブな言葉
    positive_words = [
        '楽しい', '嬉しい', '最高', '良い', 'すごい', 'がんばる', '頑張る', 
        '感動', '素晴らしい', 'ありがとう', '大好き', '幸せ', 'やったー',
        '成功', '合格', '勝利', '達成', '完璧', '満足', 'ワクワク'
    ]
    
    # ネガティブな言葉  
    negative_words = [
        '悲しい', '辛い', '大変', '不安', '心配', '疲れた', 'つまらない', 
        '嫌', '困った', 'ダメ', '失敗', '最悪', 'むかつく', 'イライラ',
        '落ち込む', 'がっかり', '残念', '苦しい'
    ]
    
    # カウント
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    # スコア計算（0-100点）
    if positive_count > negative_count:
        score = 50 + (positive_count * 10)
    elif negative_count > positive_count:
        score = 50 - (negative_count * 10)
    else:
        score = 50
    
    # 範囲調整
    score = max(0, min(100, score))
    return score

# Google Apps Script URL（秘密の設定から取得）
GAS_URL = st.secrets.get("gas_url", "")

def load_posts():
    """投稿を読み込み"""
    if not GAS_URL:
        return st.session_state.get('posts', [])
    
    try:
        response = requests.get(GAS_URL, timeout=10)
        if response.status_code == 200:
            posts = response.json()
            # 時刻データを変換
            for post in posts:
                if post.get('time'):
                    try:
                        # ISO形式の文字列をdatetimeに変換
                        if isinstance(post['time'], str):
                            # 'Z'が含まれる場合は除去
                            time_str = post['time'].replace('Z', '')
                            # ミリ秒が含まれる場合の対応
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

def save_post(user_name, text, score, emotion, color):
    """投稿を保存"""
    post_data = {
        'user': user_name,
        'text': text,
        'sentiment': score,
        'emotion': emotion,
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

# メインアプリ
st.title("😊 みんなの感情SNS")

# 接続状況
if GAS_URL:
    st.success("🌐 全端末でリアルタイム共有中！")
else:
    st.warning("💻 ローカルモード（この端末のみ）")

# 自動更新
auto_update = st.checkbox("🔄 自動更新（10秒ごと）", value=True)

# 左右のレイアウト
left_col, right_col = st.columns([1, 1])

# 左側：投稿エリア
with left_col:
    st.subheader("📝 投稿しよう！")
    
    # 名前入力
    name = st.text_input("あなたの名前", placeholder="例：田中太郎")
    
    # 投稿内容
    message = st.text_area(
        "今の気持ちを書いてね",
        placeholder="例：今日のテスト、思ったより良くできた！",
        height=120
    )
    
    # リアルタイム分析
    if message and name:
        score = simple_sentiment_analysis(message)
        
        # 感情判定
        if score >= 70:
            emotion = "😊 とても元気"
            color = "#28a745"
        elif score >= 60:
            emotion = "🙂 元気"
            color = "#17a2b8"
        elif score >= 40:
            emotion = "😐 普通"
            color = "#6c757d"
        elif score >= 30:
            emotion = "😞 ちょっと落ち込み"
            color = "#fd7e14"
        else:
            emotion = "😢 落ち込み"
            color = "#dc3545"
        
        # 分析結果表示
        st.markdown("### 🤖 気持ち分析結果")
        st.metric("感情スコア", f"{score}点", emotion)
        
        # プレビュー
        st.markdown(f"""
        <div style="
            border-left: 5px solid {color}; 
            padding: 15px; 
            background-color: #f8f9fa;
            border-radius: 10px;
            margin: 10px 0;
        ">
            <strong>👤 {name}</strong><br>
            <span style="color: {color}; font-weight: bold;">{emotion} ({score}点)</span><br>
            <div style="margin-top: 10px; font-size: 16px;">💬 {message}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 投稿ボタン
        if st.button("🚀 投稿する！", type="primary", use_container_width=True):
            if save_post(name, message, score, emotion, color):
                st.success("✅ 投稿完了！みんなに共有されました 🎉")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ 投稿に失敗しました")

# 右側：投稿一覧
with right_col:
    st.subheader("🌟 みんなの投稿")
    
    # 更新ボタン
    if st.button("🔄 最新の投稿を見る"):
        st.rerun()
    
    # 投稿を取得
    posts = load_posts()
    
    if posts:
        # 統計
        total = len(posts)
        avg_score = sum(p['sentiment'] for p in posts) / total
        happy_count = len([p for p in posts if p['sentiment'] >= 60])
        
        st.markdown("### 📊 みんなの気持ち統計")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総投稿数", f"{total}件")
        with col2:
            st.metric("平均スコア", f"{avg_score:.0f}点")
        with col3:
            st.metric("元気な人", f"{happy_count}人")
        
        # 投稿一覧（最新10件）
        st.markdown("### 💬 最新の投稿")
        
        # 時刻でソートする前に、すべての時刻データを確実にdatetimeに変換
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
            # 時間表示の安全な処理
            post_time = post.get('time')
            
            # post_timeが文字列の場合はdatetimeに変換を試行
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
            
            # 投稿表示
            st.markdown(f"""
            <div style="
                border-left: 5px solid {post['color']}; 
                padding: 15px; 
                margin: 10px 0; 
                background-color: #f8f9fa;
                border-radius: 10px;
            ">
                <div style="display: flex; justify-content: space-between;">
                    <strong>👤 {post['user']}</strong>
                    <small style="color: #666;">⏰ {time_str}</small>
                </div>
                <div style="color: {post['color']}; font-weight: bold; margin: 8px 0;">
                    {post['emotion']} ({post['sentiment']}点)
                </div>
                <div style="font-size: 16px; margin-top: 10px;">
                    💬 {post['text']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # グラフ表示
        if len(posts) > 2:
            st.markdown("### 📈 気持ちの変化")
            df = pd.DataFrame(posts)
            df = df.sort_values('time')
            df['番号'] = range(1, len(df) + 1)
            
            fig = px.line(
                df, 
                x='番号', 
                y='sentiment',
                title='みんなの気持ちスコアの変化',
                markers=True
            )
            fig.update_layout(
                height=300,
                yaxis_title="気持ちスコア",
                xaxis_title="投稿順"
            )
            # 基準線を追加
            fig.add_hline(y=50, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("まだ投稿がありません。左側から投稿してみてください！")

# 自動更新
if auto_update:
    time.sleep(10)
    st.rerun()

# サイドバーで説明
with st.sidebar:
    st.markdown("## 📖 使い方")
    st.markdown("""
    1. **名前**を入力
    2. **今の気持ち**を文章で書く
    3. **AIが自動で分析**してくれる
    4. **投稿ボタン**を押す
    5. **みんなの投稿**がリアルタイムで見れる
    """)
    
    st.markdown("## 🤖 気持ち分析について")
    st.markdown("""
    **AIが文章から気持ちを分析：**
    - 😊 とても元気 (70-100点)
    - 🙂 元気 (60-69点)  
    - 😐 普通 (40-59点)
    - 😞 ちょっと落ち込み (30-39点)
    - 😢 落ち込み (0-29点)
    """)
    
    st.markdown("## 📱 対応端末")
    st.markdown("""
    - 🖥️ パソコン
    - 📱 スマホ
    - 📟 タブレット
    
    どの端末からでも同じデータが見れます！
    """)
    
    if GAS_URL:
        st.markdown("## ✅ 接続状況")
        st.success("Google Sheetsと接続中")
    else:
        st.markdown("## ⚠️ 設定が必要")
        st.warning("Google Apps ScriptのURLを設定してください")
    
    # データダウンロード
    if posts:
        st.markdown("## 📥 データダウンロード")
        export_data = json.dumps(posts, ensure_ascii=False, indent=2, default=str)
        st.download_button(
            "📄 JSONファイルをダウンロード",
            data=export_data,
            file_name=f"sns_data_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        )
