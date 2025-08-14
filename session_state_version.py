import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json

# TextBlobのセットアップ
try:
    from textblob import TextBlob
    try:
        import nltk
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            import ssl
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                pass
            else:
                ssl._create_default_https_context = _create_unverified_https_context
            nltk.download('punkt', quiet=True)
            nltk.download('brown', quiet=True)
        except:
            pass
except ImportError:
    st.error("TextBlobが利用できません。")
    st.stop()

# ページ設定
st.set_page_config(page_title="感情分析SNS", page_icon="🎭", layout="wide")

# Session Stateでデータを管理
if 'posts' not in st.session_state:
    st.session_state.posts = []

def add_post(user_name, text, sentiment_score, emotion, color):
    """新しい投稿を追加"""
    new_post = {
        'user': user_name,
        'text': text,
        'sentiment': sentiment_score,
        'emotion': emotion,
        'time': datetime.now(),
        'color': color,
        'id': len(st.session_state.posts) + 1
    }
    st.session_state.posts.append(new_post)
    return True

def export_data():
    """データをJSON形式でエクスポート"""
    if st.session_state.posts:
        # datetimeを文字列に変換
        export_data = []
        for post in st.session_state.posts:
            post_copy = post.copy()
            post_copy['time'] = post['time'].isoformat()
            export_data.append(post_copy)
        
        return json.dumps(export_data, ensure_ascii=False, indent=2)
    return None

def export_csv():
    """データをCSV形式でエクスポート"""
    if st.session_state.posts:
        df = pd.DataFrame(st.session_state.posts)
        return df.to_csv(index=False, encoding='utf-8')
    return None

def analyze_sentiment(text):
    """感情分析を実行"""
    try:
        blob = TextBlob(text)
        sentiment_polarity = blob.sentiment.polarity
    except:
        sentiment_polarity = 0
    
    # 日本語キーワード補正
    positive_words = ['楽しい', '嬉しい', '最高', '良い', 'すごい', 'がんばる', '頑張る', '感動', '素晴らしい', 'ありがとう', '大好き', '幸せ']
    negative_words = ['悲しい', '辛い', '大変', '不安', '心配', '疲れた', 'つまらない', '嫌', '困った', 'ダメ']
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    keyword_adjustment = (positive_count - negative_count) * 0.3
    sentiment_polarity = max(-1, min(1, sentiment_polarity + keyword_adjustment))
    
    return sentiment_polarity

# メインタイトル
st.title("🎭 リアルタイム感情分析SNS")
st.markdown("**AIが投稿の感情を瞬時に分析 - セッション内でデータ保存！**")

# データエクスポート機能
with st.sidebar:
    st.markdown("## 📥 データエクスポート")
    
    if st.session_state.posts:
        st.markdown(f"現在の投稿数: **{len(st.session_state.posts)}件**")
        
        # JSONダウンロード
        json_data = export_data()
        if json_data:
            st.download_button(
                label="📄 JSONでダウンロード",
                data=json_data,
                file_name=f"emotion_posts_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )
        
        # CSVダウンロード
        csv_data = export_csv()
        if csv_data:
            st.download_button(
                label="📊 CSVでダウンロード",
                data=csv_data,
                file_name=f"emotion_posts_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        # データクリア
        if st.button("🗑️ 全データをクリア", type="secondary"):
            st.session_state.posts = []
            st.success("全データをクリアしました！")
            st.rerun()
    
    else:
        st.info("まだ投稿がありません。")

# レイアウト: 2列構成
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 投稿エリア")
    
    user_name = st.text_input("ニックネーム", placeholder="未来の○○大生", key="username")
    
    user_input = st.text_area(
        "今の気持ちを投稿してください",
        placeholder="例: 今日のオープンキャンパス楽しい！",
        height=100,
        key="post_input"
    )
    
    if user_input and user_name:
        sentiment_polarity = analyze_sentiment(user_input)
        sentiment_score = (sentiment_polarity + 1) * 50
        
        # 感情判定
        if sentiment_score > 65:
            emotion = "😊 とてもポジティブ"
            color = "#28a745"
        elif sentiment_score > 55:
            emotion = "🙂 ポジティブ"
            color = "#17a2b8"
        elif sentiment_score > 45:
            emotion = "😐 ニュートラル"
            color = "#6c757d"
        elif sentiment_score > 35:
            emotion = "😞 ネガティブ"
            color = "#fd7e14"
        else:
            emotion = "😢 とてもネガティブ"
            color = "#dc3545"
        
        st.markdown("### 🤖 AI分析結果")
        
        st.metric(
            label="感情スコア",
            value=f"{sentiment_score:.1f}点",
            delta=f"{emotion}",
        )
        
        st.markdown(f"""
        <div style="background-color: {color}; height: 20px; border-radius: 10px; width: {sentiment_score}%; margin: 10px 0;">
            <div style="color: white; text-align: center; line-height: 20px; font-weight: bold;">
                {sentiment_score:.1f}点
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 投稿する", type="primary"):
            if add_post(user_name, user_input, sentiment_score, emotion, color):
                st.success("投稿完了！")
                st.rerun()

with col2:
    st.subheader("🌟 投稿タイムライン")
    
    if st.button("🔄 最新を取得"):
        st.rerun()
    
    all_posts = st.session_state.posts
    
    if all_posts:
        # 統計情報
        total_posts = len(all_posts)
        avg_sentiment = sum(post['sentiment'] for post in all_posts) / total_posts
        
        st.markdown("### 📊 統計")
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("総投稿数", f"{total_posts}件")
        with metric_col2:
            st.metric("平均感情", f"{avg_sentiment:.1f}点")
        with metric_col3:
            positive_ratio = len([p for p in all_posts if p['sentiment'] > 55]) / total_posts * 100
            st.metric("ポジティブ率", f"{positive_ratio:.0f}%")
        
        # タイムライン表示
        st.markdown("### 💬 最新の投稿")
        display_posts = sorted(all_posts, key=lambda x: x['time'], reverse=True)[:8]
        
        for post in display_posts:
            time_ago = datetime.now() - post['time']
            if time_ago.total_seconds() < 60:
                time_str = f"{int(time_ago.total_seconds())}秒前"
            elif time_ago.total_seconds() < 3600:
                time_str = f"{int(time_ago.total_seconds() / 60)}分前"
            else:
                time_str = post['time'].strftime('%H:%M')
            
            st.markdown(f"""
            <div style="
                border-left: 4px solid {post['color']}; 
                padding: 12px; 
                margin: 8px 0; 
                background-color: #f8f9fa;
                border-radius: 8px;
            ">
                <div style="display: flex; justify-content: space-between;">
                    <strong>👤 {post['user']}</strong> 
                    <small>⏰ {time_str}</small>
                </div>
                <div style="color: {post['color']}; font-weight: bold; margin: 5px 0;">
                    {post['emotion']} ({post['sentiment']:.1f}点)
                </div>
                <div style="margin-top: 8px;">
                    📝 {post['text']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # グラフ表示
        if len(all_posts) > 1:
            st.markdown("### 📈 感情の推移")
            df = pd.DataFrame(all_posts)
            df['投稿順序'] = range(1, len(df) + 1)
            
            fig = px.line(
                df, 
                x='投稿順序', 
                y='sentiment',
                title='感情スコア変化',
                markers=True,
                hover_data=['user', 'text']
            )
            fig.update_layout(height=300)
            fig.add_hline(y=50, line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("まだ投稿がありません。左側から投稿してみてください！")
