import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import requests
import time

# ページ設定
st.set_page_config(page_title="オープンキャンパス感想SNS", page_icon="🎓", layout="wide")

# 感情分析（シンプル版）
def simple_sentiment_analysis(text):
    """シンプルな感情分析"""
    # ポジティブな言葉（オープンキャンパス向け）
    positive_words = [
        '楽しい', '嬉しい', '最高', '良い', 'すごい', 'がんばる', '頑張る', 
        '感動', '素晴らしい', 'ありがとう', '大好き', '幸せ', 'やったー',
        '成功', '合格', '勝利', '達成', '完璧', '満足', 'ワクワク',
        '興味深い', '面白い', '魅力的', '素敵', 'かっこいい', '美しい',
        '充実', '発見', '学べる', '勉強になる', '将来', '夢', '希望',
        '入学したい', '通いたい', '憧れ', '目標', 'やる気', 'モチベーション'
    ]
    
    # ネガティブな言葉  
    negative_words = [
        '悲しい', '辛い', '大変', '不安', '心配', '疲れた', 'つまらない', 
        '嫌', '困った', 'ダメ', '失敗', '最悪', 'むかつく', 'イライラ',
        '落ち込む', 'がっかり', '残念', '苦しい', '難しい', '分からない',
        '迷う', '悩む', '微妙'
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

def save_post(nickname, text, score, emotion, color):
    """投稿を保存"""
    post_data = {
        'user': nickname,
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

def clear_all_posts():
    """すべての投稿をクリア"""
    if GAS_URL:
        try:
            # Google Sheetsのデータを削除するための特別なリクエスト
            clear_url = GAS_URL + "?action=clear"
            response = requests.get(clear_url, timeout=10)
            
            # 成功した場合、ローカルのSession Stateもクリア
            if response.status_code == 200:
                if 'posts' in st.session_state:
                    del st.session_state['posts']
                # 確認フラグもリセット
                if 'confirm_clear' in st.session_state:
                    del st.session_state['confirm_clear']
                return True
            return False
        except:
            return False
    else:
        # ローカルデータをクリア
        st.session_state.posts = []
        if 'confirm_clear' in st.session_state:
            del st.session_state['confirm_clear']
        return True

# メインアプリ
st.title("🎓 オープンキャンパス感想SNS")
st.markdown("**今日のオープンキャンパスはいかがでしたか？AIが感想を分析して、みんなで共有しましょう！**")

# 接続状況
if GAS_URL:
    st.success("🌐 全参加者でリアルタイム共有中！")
else:
    st.warning("💻 ローカルモード（この端末のみ）")

# 自動更新
auto_update = st.checkbox("🔄 自動更新（10秒ごと）", value=True)

# 管理者用データクリア機能（サイドバーに配置）
with st.sidebar:
    st.markdown("## 🎯 オープンキャンパス感想SNS")
    st.markdown("みなさんの率直な感想をお聞かせください！")
    
    st.markdown("## 📊 現在の状況")
    posts = load_posts()
    total_posts = len(posts)
    st.metric("参加者の感想", f"{total_posts}件")
    
    if posts:
        avg_score = sum(p['sentiment'] for p in posts) / total_posts
        st.metric("平均満足度", f"{avg_score:.0f}点")
        
        positive_count = len([p for p in posts if p['sentiment'] >= 60])
        st.metric("満足した人", f"{positive_count}人")
    
    st.markdown("---")
    st.markdown("## ⚙️ 管理機能")
    st.markdown("**(スタッフ専用)**")
    
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
                            # 強制的にページを再読み込み
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
                # Session Stateを完全にクリア
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
    
    # ニックネーム入力
    nickname = st.text_input(
        "ニックネーム", 
        placeholder="例：未来の○○大生、理系男子、文学少女など",
        help="個人が特定されないニックネームを入力してください"
    )
    
    # 投稿内容
    message = st.text_area(
        "オープンキャンパスの感想をお聞かせください",
        placeholder="例：模擬授業がとても分かりやすくて、この大学で学びたいと思いました！学生スタッフの皆さんも親切で、キャンパスの雰囲気が素敵でした。",
        height=120,
        help="施設、授業、学生、進路など、どんなことでもOKです！"
    )
    
    # リアルタイム分析
    if message and nickname:
        score = simple_sentiment_analysis(message)
        
        # 感情判定（オープンキャンパス向け）
        if score >= 70:
            emotion = "😊 とても満足"
            color = "#28a745"
        elif score >= 60:
            emotion = "🙂 満足"
            color = "#17a2b8"
        elif score >= 40:
            emotion = "😐 普通"
            color = "#6c757d"
        elif score >= 30:
            emotion = "😞 少し不満"
            color = "#fd7e14"
        else:
            emotion = "😢 不満"
            color = "#dc3545"
        
        # 分析結果表示
        st.markdown("### 🤖 AI感想分析")
        st.metric("満足度スコア", f"{score}点", emotion)
        
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
            if save_post(nickname, message, score, emotion, color):
                st.success("✅ 感想を投稿しました！他の参加者にも共有されます 🎉")
                st.balloons()  # お祝いアニメーション
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ 投稿に失敗しました。もう一度お試しください。")

# 右側：投稿一覧
with right_col:
    st.subheader("🌟 みんなの感想")
    
    # 更新ボタン
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
            st.metric("平均満足度", f"{avg_score:.0f}点")
        with col3:
            satisfaction_rate = (satisfied_count / total_posts) * 100
            st.metric("満足率", f"{satisfaction_rate:.0f}%")
        
        # 投稿一覧（最新10件）
        st.markdown("### 💬 最新の感想")
        
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
                title='参加者の満足度スコア推移',
                markers=True,
                hover_data=['user', 'text']
            )
            fig.update_layout(
                height=300,
                yaxis_title="満足度スコア",
                xaxis_title="投稿順"
            )
            # 基準線を追加
            fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="普通(50点)")
            fig.add_hline(y=60, line_dash="dot", line_color="green", annotation_text="満足ライン(60点)")
            st.plotly_chart(fig, use_container_width=True)
            
            # 感想の分布
            st.markdown("### 🎭 満足度分布")
            emotion_counts = df['emotion'].value_counts()
            fig2 = px.pie(
                values=emotion_counts.values, 
                names=emotion_counts.index,
                title="参加者の満足度分布"
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    else:
        st.info("まだ感想がありません。左側から感想を投稿してみてください！")
        
        # オープンキャンパス情報
        st.markdown("""
        ### 🎓 オープンキャンパスへようこそ！
        
        今日の体験はいかがですか？
        - 🏫 **施設見学**の印象
        - 👨‍🏫 **模擬授業**の感想  
        - 👥 **学生との交流**について
        - 🎯 **進路への想い**
        - 😊 **全体的な感想**
        
        どんな小さなことでも大歓迎です！
        """)

# 自動更新
if auto_update:
    time.sleep(10)
    st.rerun()

# フッター
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    🎓 オープンキャンパス感想SNS | AIが感想を分析してリアルタイム共有<br>
    ご参加いただき、ありがとうございました！
</div>
""", unsafe_allow_html=True)
