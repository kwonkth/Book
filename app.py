import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import markdown
import tempfile
import os

# 페이지 설정
st.set_page_config(
    page_title="고객 피드백 분석 & 개인 기록 관리",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터베이스 초기화
def init_database():
    conn = sqlite3.connect('feedback_analysis.db')
    cursor = conn.cursor()
    
    # 피드백 데이터 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            sentiment TEXT,
            keywords TEXT,
            category TEXT,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source TEXT
        )
    ''')
    
    # 개인 기록 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            rating INTEGER,
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT
        )
    ''')
    
    # 장르 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # 독후감 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100) NOT NULL,
            author VARCHAR(50) NOT NULL,
            read_date DATE NOT NULL,
            genre_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genre_id) REFERENCES genres (id)
        )
    ''')
    
    # 기본 장르 데이터 삽입
    default_genres = [
        '소설(문학 일반)', '판타지', 'SF', '미스터리/스릴러', '로맨스', 
        '에세이', '자기계발', '역사', '인문/사회', '경제/경영', 
        '과학', '철학', '예술/대중문화', '아동/청소년'
    ]
    
    for genre in default_genres:
        cursor.execute('''
            INSERT OR IGNORE INTO genres (name) VALUES (?)
        ''', (genre,))
    
    conn.commit()
    conn.close()

# 감성 분석 함수 (간단한 규칙 기반)
def analyze_sentiment(text):
    positive_words = ['좋다', '만족', '훌륭', '최고', '감사', '좋은', '훌륭한', '최고의', '추천', '완벽']
    negative_words = ['나쁘다', '불만', '문제', '최악', '실망', '나쁜', '최악의', '불만족', '문제가', '어려움']
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return '긍정'
    elif negative_count > positive_count:
        return '부정'
    else:
        return '중립'

# 키워드 추출 함수 (간단한 빈도 기반)
def extract_keywords(text, top_n=10):
    # 간단한 키워드 추출 (실제로는 더 정교한 NLP 라이브러리 사용 권장)
    words = text.split()
    word_freq = {}
    
    for word in words:
        if len(word) > 1:  # 1글자 단어 제외
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # 빈도순으로 정렬하여 상위 키워드 반환
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_n]]

# 데이터 시각화 함수
def create_sentiment_chart(data):
    sentiment_counts = data['sentiment'].value_counts()
    
    fig = px.pie(
        values=sentiment_counts.values,
        names=sentiment_counts.index,
        title="감성 분포",
        color_discrete_map={'긍정': '#2E8B57', '부정': '#DC143C', '중립': '#4682B4'}
    )
    return fig

def create_keyword_chart(keywords_data):
    if not keywords_data:
        return None
    
    # 키워드 빈도 데이터 준비
    keyword_freq = {}
    for keywords in keywords_data:
        for keyword in keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
    
    if not keyword_freq:
        return None
    
    # 상위 10개 키워드만 표시
    top_keywords = dict(sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10])
    
    fig = px.bar(
        x=list(top_keywords.values()),
        y=list(top_keywords.keys()),
        orientation='h',
        title="주요 키워드 빈도",
        color=list(top_keywords.values()),
        color_continuous_scale='viridis'
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    return fig

# 독후감 관련 함수들
def get_genres():
    """장르 목록을 가져오는 함수"""
    conn = sqlite3.connect('feedback_analysis.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM genres WHERE is_active = 1 ORDER BY name')
    genres = cursor.fetchall()
    conn.close()
    return genres

def save_book_review(title, author, read_date, genre_id, content, rating=None):
    """독후감을 저장하는 함수"""
    conn = sqlite3.connect('feedback_analysis.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO book_reviews (title, author, read_date, genre_id, content, rating)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, author, read_date, genre_id, content, rating))
        conn.commit()
        return True, "독후감이 성공적으로 저장되었습니다!"
    except Exception as e:
        return False, f"저장 중 오류가 발생했습니다: {str(e)}"
    finally:
        conn.close()

def get_book_reviews(genre_id=None, start_date=None, end_date=None, search_query=None, sort_by='date_desc'):
    """독후감 목록을 가져오는 함수"""
    conn = sqlite3.connect('feedback_analysis.db')
    
    query = '''
        SELECT br.id, br.title, br.author, br.read_date, g.name as genre_name, 
               br.content, br.rating, br.created_at
        FROM book_reviews br
        JOIN genres g ON br.genre_id = g.id
        WHERE 1=1
    '''
    params = []
    
    if genre_id:
        query += ' AND br.genre_id = ?'
        params.append(genre_id)
    
    if start_date:
        query += ' AND br.read_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND br.read_date <= ?'
        params.append(end_date)
    
    if search_query:
        query += ' AND (br.title LIKE ? OR br.author LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    if sort_by == 'date_desc':
        query += ' ORDER BY br.read_date DESC'
    elif sort_by == 'date_asc':
        query += ' ORDER BY br.read_date ASC'
    elif sort_by == 'title':
        query += ' ORDER BY br.title ASC'
    elif sort_by == 'rating_desc':
        query += ' ORDER BY br.rating DESC'
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_book_review_by_id(review_id):
    """특정 독후감을 가져오는 함수"""
    conn = sqlite3.connect('feedback_analysis.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT br.id, br.title, br.author, br.read_date, g.name as genre_name, 
               br.content, br.rating, br.created_at, br.updated_at
        FROM book_reviews br
        JOIN genres g ON br.genre_id = g.id
        WHERE br.id = ?
    ''', (review_id,))
    review = cursor.fetchone()
    conn.close()
    return review

def validate_book_review(title, author, read_date, genre_id, content):
    """독후감 유효성 검사 함수"""
    errors = []
    
    if not title or len(title.strip()) < 2 or len(title) > 100:
        errors.append("제목은 2-100자 사이여야 합니다.")
    
    if not author or len(author.strip()) < 2 or len(author) > 50:
        errors.append("저자는 2-50자 사이여야 합니다.")
    
    if not read_date:
        errors.append("읽은 날짜를 선택해주세요.")
    elif read_date > datetime.now().date():
        errors.append("읽은 날짜는 미래일 수 없습니다.")
    
    if not genre_id:
        errors.append("장르를 선택해주세요.")
    
    if not content or len(content.strip()) < 50 or len(content) > 5000:
        errors.append("독후감 본문은 50-5000자 사이여야 합니다.")
    
    return errors

def update_book_review(review_id, title, author, read_date, genre_id, content, rating=None):
    """독후감을 수정하는 함수"""
    conn = sqlite3.connect('feedback_analysis.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE book_reviews 
            SET title = ?, author = ?, read_date = ?, genre_id = ?, content = ?, rating = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, author, read_date, genre_id, content, rating, review_id))
        conn.commit()
        return True, "독후감이 성공적으로 수정되었습니다!"
    except Exception as e:
        return False, f"수정 중 오류가 발생했습니다: {str(e)}"
    finally:
        conn.close()

def delete_book_review(review_id):
    """독후감을 삭제하는 함수"""
    conn = sqlite3.connect('feedback_analysis.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM book_reviews WHERE id = ?', (review_id,))
        conn.commit()
        return True, "독후감이 성공적으로 삭제되었습니다!"
    except Exception as e:
        return False, f"삭제 중 오류가 발생했습니다: {str(e)}"
    finally:
        conn.close()

# PDF 보고서 생성 함수
def create_pdf_report(data, filename):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # 제목
    title = Paragraph("고객 피드백 분석 보고서", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # 요약 정보
    summary = f"""
    <b>분석 요약</b><br/>
    • 총 피드백 수: {len(data)}개<br/>
    • 긍정: {len(data[data['sentiment'] == '긍정'])}개<br/>
    • 부정: {len(data[data['sentiment'] == '부정'])}개<br/>
    • 중립: {len(data[data['sentiment'] == '중립'])}개<br/>
    """
    story.append(Paragraph(summary, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # 데이터 테이블
    if len(data) > 0:
        table_data = [['텍스트', '감성', '키워드']]
        for _, row in data.head(10).iterrows():  # 상위 10개만 표시
            keywords_str = ', '.join(eval(row['keywords']) if row['keywords'] else [])
            table_data.append([
                row['text'][:50] + '...' if len(row['text']) > 50 else row['text'],
                row['sentiment'],
                keywords_str[:30] + '...' if len(keywords_str) > 30 else keywords_str
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# 메인 애플리케이션
def main():
    # 데이터베이스 초기화
    init_database()
    
    # 사이드바
    st.sidebar.title("📚 독서 기록 관리")
    page = st.sidebar.selectbox(
        "페이지 선택",
        ["🏠 홈", "📝 독후감 등록", "📖 독후감 관리", "📚 개인 기록 관리", "📊 통합 대시보드", "📄 보고서 생성"]
    )
    
    if page == "🏠 홈":
        st.title("🏠 독서 기록 관리 시스템")
        st.markdown("""
        ### 환영합니다! 👋
        
        체계적인 독서 기록과 개인 데이터 관리를 위한 통합 플랫폼입니다.
        
        #### 📝 독후감 등록
        - 간편한 독후감 작성 및 저장
        - 장르별 분류 및 평점 시스템
        - 저장 후 자동으로 대시보드 이동
        
        #### 📖 독후감 관리
        - 독후감 목록 조회 및 검색
        - 수정/삭제 기능으로 사후 관리
        - 장르별, 기간별 필터링
        
        #### 📚 개인 기록 관리
        - 독서 기록, 취미 활동 등 개인 데이터 관리
        - 평점 및 카테고리별 분류
        - 개인 맞춤형 분석
        
        #### 📊 통합 대시보드
        - 독서 통계 및 트렌드 분석
        - 최근 등록 독후감 요약
        - 목표 달성률 및 성과 확인
        
        #### 📄 보고서 생성
        - PDF/Markdown 형태의 독서 보고서
        - 장르별 통계 및 인사이트 제공
        """)
        
        # 통계 정보 표시
        conn = sqlite3.connect('feedback_analysis.db')
        
        # 독후감 통계
        book_review_count = pd.read_sql_query("SELECT COUNT(*) as count FROM book_reviews", conn).iloc[0]['count']
        
        # 개인 기록 통계
        personal_count = pd.read_sql_query("SELECT COUNT(*) as count FROM personal_records", conn).iloc[0]['count']
        
        # 이번 달 독후감 수
        current_month = datetime.now().strftime('%Y-%m')
        monthly_review_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM book_reviews WHERE strftime('%Y-%m', read_date) = ?", 
            conn, params=[current_month]
        ).iloc[0]['count']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📖 총 독후감 수", book_review_count)
        with col2:
            st.metric("📅 이번 달 독후감", monthly_review_count)
        with col3:
            st.metric("📚 총 개인 기록 수", personal_count)
        
        conn.close()
    
    elif page == "📝 독후감 등록":
        st.title("📝 독후감 등록")
        
        with st.form("book_review_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("📖 책 제목", placeholder="책 제목을 입력하세요 (2-100자)", max_chars=100)
                author = st.text_input("✍️ 저자", placeholder="저자명을 입력하세요 (2-50자)", max_chars=50)
                read_date = st.date_input("📅 읽은 날짜", value=datetime.now().date(), max_value=datetime.now().date())
            
            with col2:
                genres = get_genres()
                genre_options = {genre[1]: genre[0] for genre in genres}
                selected_genre = st.selectbox("📚 장르", ["선택하세요"] + list(genre_options.keys()))
                genre_id = genre_options.get(selected_genre) if selected_genre != "선택하세요" else None
                
                rating = st.selectbox("⭐ 평점 (선택사항)", ["평점 없음", "1점", "2점", "3점", "4점", "5점"])
                rating_value = None if rating == "평점 없음" else int(rating[0])
            
            content = st.text_area(
                "📝 독후감 본문", 
                placeholder="독후감을 작성해주세요 (50-5000자)", 
                height=200,
                max_chars=5000
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                submitted = st.form_submit_button("💾 저장", type="primary")
            with col2:
                reset = st.form_submit_button("🔄 초기화")
            
            if submitted:
                # 유효성 검사
                errors = validate_book_review(title, author, read_date, genre_id, content)
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # 저장
                    success, message = save_book_review(title, author, read_date, genre_id, content, rating_value)
                    if success:
                        st.success(message)
                        st.balloons()
                        
                        # 저장 성공 후 자동으로 통합 대시보드로 이동
                        st.info("잠시 후 통합 대시보드로 이동합니다...")
                        st.session_state.redirect_to_dashboard = True
            
            if reset:
                st.rerun()
        
        # 자동 리다이렉트 처리
        if st.session_state.get('redirect_to_dashboard', False):
            st.session_state.redirect_to_dashboard = False
            st.rerun()
    
    elif page == "📚 개인 기록 관리":
        st.title("📚 개인 기록 관리")
        
        # 새 기록 추가
        st.subheader("➕ 새 기록 추가")
        
        with st.form("personal_record_form"):
            record_type = st.selectbox("기록 유형", ["독서", "취미", "운동", "학습", "기타"])
            title = st.text_input("제목")
            content = st.text_area("내용")
            rating = st.slider("평점 (1-5)", 1, 5, 3)
            category = st.text_input("카테고리 (선택사항)")
            
            submitted = st.form_submit_button("💾 저장")
            
            if submitted:
                if title and content:
                    conn = sqlite3.connect('feedback_analysis.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO personal_records (type, title, content, rating, category)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (record_type, title, content, rating, category))
                    conn.commit()
                    conn.close()
                    st.success("기록이 성공적으로 저장되었습니다!")
                else:
                    st.error("제목과 내용을 모두 입력해주세요.")
        
        # 기존 기록 조회
        st.subheader("📋 기존 기록")
        
        # 필터 옵션
        conn = sqlite3.connect('feedback_analysis.db')
        existing_records = pd.read_sql_query("SELECT * FROM personal_records ORDER BY date_created DESC", conn)
        conn.close()
        
        if len(existing_records) > 0:
            # 필터
            col1, col2 = st.columns(2)
            with col1:
                type_filter = st.selectbox("유형별 필터", ["전체"] + list(existing_records['type'].unique()))
            with col2:
                category_filter = st.selectbox("카테고리별 필터", ["전체"] + list(existing_records['category'].dropna().unique()))
            
            # 필터 적용
            filtered_records = existing_records.copy()
            if type_filter != "전체":
                filtered_records = filtered_records[filtered_records['type'] == type_filter]
            if category_filter != "전체":
                filtered_records = filtered_records[filtered_records['category'] == category_filter]
            
            # 통계 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 기록 수", len(filtered_records))
            with col2:
                avg_rating = filtered_records['rating'].mean()
                st.metric("평균 평점", f"{avg_rating:.1f}")
            with col3:
                most_common_type = filtered_records['type'].mode().iloc[0] if len(filtered_records) > 0 else "없음"
                st.metric("가장 많은 유형", most_common_type)
            
            # 시각화
            col1, col2 = st.columns(2)
            
            with col1:
                # 유형별 분포
                type_counts = filtered_records['type'].value_counts()
                fig_type = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="기록 유형별 분포"
                )
                st.plotly_chart(fig_type, use_container_width=True)
            
            with col2:
                # 평점 분포
                rating_counts = filtered_records['rating'].value_counts().sort_index()
                fig_rating = px.bar(
                    x=rating_counts.index,
                    y=rating_counts.values,
                    title="평점 분포",
                    labels={'x': '평점', 'y': '개수'}
                )
                st.plotly_chart(fig_rating, use_container_width=True)
            
            # 기록 목록
            st.subheader("📝 기록 목록")
            for _, record in filtered_records.iterrows():
                with st.expander(f"{record['title']} ({record['type']}) - ⭐{record['rating']}"):
                    st.write(f"**내용:** {record['content']}")
                    if record['category']:
                        st.write(f"**카테고리:** {record['category']}")
                    st.write(f"**작성일:** {record['date_created']}")
        else:
            st.info("저장된 기록이 없습니다. 위의 폼을 사용하여 새 기록을 추가해보세요.")
    
    elif page == "📖 독후감 관리":
        st.title("📖 독후감 관리")
        
        # 탭 생성
        tab1, tab2 = st.tabs(["📋 독후감 목록", "📊 독후감 통계"])
        
        with tab1:
            st.subheader("📋 독후감 목록")
            
            # 필터 섹션
            with st.expander("🔍 필터 및 검색", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    genres = get_genres()
                    genre_options = {genre[1]: genre[0] for genre in genres}
                    selected_genre_filter = st.selectbox("장르 필터", ["전체"] + list(genre_options.keys()))
                    genre_filter_id = genre_options.get(selected_genre_filter) if selected_genre_filter != "전체" else None
                
                with col2:
                    date_range = st.date_input(
                        "날짜 범위",
                        value=(datetime.now().date() - timedelta(days=30), datetime.now().date()),
                        max_value=datetime.now().date()
                    )
                    start_date = date_range[0] if len(date_range) > 0 else None
                    end_date = date_range[1] if len(date_range) > 1 else None
                
                with col3:
                    search_query = st.text_input("🔍 검색 (제목/저자)", placeholder="검색어를 입력하세요")
                
                col1, col2 = st.columns(2)
                with col1:
                    sort_option = st.selectbox("정렬 기준", ["읽은 날짜 (최신순)", "읽은 날짜 (오래된순)", "제목순", "평점순"])
                    sort_mapping = {
                        "읽은 날짜 (최신순)": "date_desc",
                        "읽은 날짜 (오래된순)": "date_asc", 
                        "제목순": "title",
                        "평점순": "rating_desc"
                    }
                    sort_by = sort_mapping[sort_option]
            
            # 독후감 목록 조회
            reviews_df = get_book_reviews(
                genre_id=genre_filter_id,
                start_date=start_date,
                end_date=end_date,
                search_query=search_query if search_query else None,
                sort_by=sort_by
            )
            
            if len(reviews_df) > 0:
                st.success(f"총 {len(reviews_df)}개의 독후감을 찾았습니다.")
                
                # 페이지네이션
                items_per_page = 10
                total_pages = (len(reviews_df) - 1) // items_per_page + 1
                
                if total_pages > 1:
                    page_num = st.selectbox("페이지", range(1, total_pages + 1))
                    start_idx = (page_num - 1) * items_per_page
                    end_idx = start_idx + items_per_page
                    page_df = reviews_df.iloc[start_idx:end_idx]
                else:
                    page_df = reviews_df
                
                # 독후감 목록 표시
                for _, review in page_df.iterrows():
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"### 📖 {review['title']}")
                            st.markdown(f"**저자:** {review['author']} | **장르:** {review['genre_name']} | **읽은 날짜:** {review['read_date']}")
                            if pd.notna(review['rating']):
                                stars = "⭐" * int(review['rating'])
                                st.markdown(f"**평점:** {stars} ({review['rating']}/5)")
                            
                            # 본문 요약 (100자)
                            content_preview = review['content'][:100] + "..." if len(review['content']) > 100 else review['content']
                            st.markdown(f"**독후감:** {content_preview}")
                        
                        with col2:
                            col2_1, col2_2 = st.columns(2)
                            with col2_1:
                                if st.button("📝", key=f"edit_{review['id']}", help="수정"):
                                    st.session_state.edit_review_id = review['id']
                            with col2_2:
                                if st.button("🗑️", key=f"delete_{review['id']}", help="삭제"):
                                    st.session_state.delete_review_id = review['id']
                        
                        st.divider()
                
                # 수정 모달
                if 'edit_review_id' in st.session_state:
                    review_to_edit = get_book_review_by_id(st.session_state.edit_review_id)
                    if review_to_edit:
                        with st.expander("📝 독후감 수정", expanded=True):
                            with st.form("edit_review_form"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    edit_title = st.text_input("📖 책 제목", value=review_to_edit[1], max_chars=100)
                                    edit_author = st.text_input("✍️ 저자", value=review_to_edit[2], max_chars=50)
                                    edit_read_date = st.date_input("📅 읽은 날짜", value=datetime.strptime(review_to_edit[3], '%Y-%m-%d').date(), max_value=datetime.now().date())
                                
                                with col2:
                                    genres = get_genres()
                                    genre_options = {genre[1]: genre[0] for genre in genres}
                                    current_genre_name = review_to_edit[4]
                                    edit_genre = st.selectbox("📚 장르", list(genre_options.keys()), index=list(genre_options.keys()).index(current_genre_name))
                                    edit_genre_id = genre_options[edit_genre]
                                    
                                    current_rating = review_to_edit[6] if review_to_edit[6] else "평점 없음"
                                    rating_options = ["평점 없음", "1점", "2점", "3점", "4점", "5점"]
                                    if current_rating != "평점 없음":
                                        rating_index = rating_options.index(f"{int(current_rating)}점")
                                    else:
                                        rating_index = 0
                                    edit_rating = st.selectbox("⭐ 평점", rating_options, index=rating_index)
                                    edit_rating_value = None if edit_rating == "평점 없음" else int(edit_rating[0])
                                
                                edit_content = st.text_area("📝 독후감 본문", value=review_to_edit[5], height=200, max_chars=5000)
                                
                                col1, col2, col3 = st.columns([1, 1, 2])
                                with col1:
                                    if st.form_submit_button("💾 저장", type="primary"):
                                        errors = validate_book_review(edit_title, edit_author, edit_read_date, edit_genre_id, edit_content)
                                        if errors:
                                            for error in errors:
                                                st.error(error)
                                        else:
                                            success, message = update_book_review(
                                                st.session_state.edit_review_id, 
                                                edit_title, edit_author, edit_read_date, 
                                                edit_genre_id, edit_content, edit_rating_value
                                            )
                                            if success:
                                                st.success(message)
                                                del st.session_state.edit_review_id
                                                st.rerun()
                                            else:
                                                st.error(message)
                                with col2:
                                    if st.form_submit_button("❌ 취소"):
                                        del st.session_state.edit_review_id
                                        st.rerun()
                
                # 삭제 확인
                if 'delete_review_id' in st.session_state:
                    review_to_delete = get_book_review_by_id(st.session_state.delete_review_id)
                    if review_to_delete:
                        st.warning(f"⚠️ **'{review_to_delete[1]}'** 독후감을 삭제하시겠습니까?")
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("✅ 삭제", type="primary"):
                                success, message = delete_book_review(st.session_state.delete_review_id)
                                if success:
                                    st.success(message)
                                    del st.session_state.delete_review_id
                                    st.rerun()
                                else:
                                    st.error(message)
                        with col2:
                            if st.button("❌ 취소"):
                                del st.session_state.delete_review_id
                                st.rerun()
            else:
                st.info("조건에 맞는 독후감이 없습니다.")
        
        with tab2:
            st.subheader("📊 독후감 통계")
            
            # 전체 독후감 데이터 조회
            all_reviews = get_book_reviews()
            
            if len(all_reviews) > 0:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📖 총 독후감 수", len(all_reviews))
                
                with col2:
                    avg_rating = all_reviews['rating'].mean()
                    st.metric("⭐ 평균 평점", f"{avg_rating:.1f}" if pd.notna(avg_rating) else "평점 없음")
                
                with col3:
                    most_read_genre = all_reviews['genre_name'].mode().iloc[0] if len(all_reviews) > 0 else "없음"
                    st.metric("📚 가장 많이 읽은 장르", most_read_genre)
                
                with col4:
                    recent_review = all_reviews['read_date'].max()
                    st.metric("📅 최근 읽은 날짜", recent_review)
                
                # 시각화
                col1, col2 = st.columns(2)
                
                with col1:
                    # 장르별 분포
                    genre_counts = all_reviews['genre_name'].value_counts()
                    fig_genre = px.pie(
                        values=genre_counts.values,
                        names=genre_counts.index,
                        title="장르별 독서 분포"
                    )
                    st.plotly_chart(fig_genre, use_container_width=True)
                
                with col2:
                    # 평점 분포
                    rating_data = all_reviews[all_reviews['rating'].notna()]
                    if len(rating_data) > 0:
                        rating_counts = rating_data['rating'].value_counts().sort_index()
                        fig_rating = px.bar(
                            x=rating_counts.index,
                            y=rating_counts.values,
                            title="평점 분포",
                            labels={'x': '평점', 'y': '개수'}
                        )
                        st.plotly_chart(fig_rating, use_container_width=True)
                    else:
                        st.info("평점 데이터가 없습니다.")
                
                # 시간별 독서 트렌드
                st.subheader("📈 독서 트렌드")
                all_reviews['read_date'] = pd.to_datetime(all_reviews['read_date'])
                monthly_counts = all_reviews.groupby(all_reviews['read_date'].dt.to_period('M')).size()
                
                fig_trend = px.line(
                    x=[str(period) for period in monthly_counts.index],
                    y=monthly_counts.values,
                    title="월별 독서량 추이",
                    labels={'x': '월', 'y': '독서량'}
                )
                st.plotly_chart(fig_trend, use_container_width=True)
                
                # 상세 통계 테이블
                st.subheader("📋 상세 통계")
                genre_stats = all_reviews.groupby('genre_name').agg({
                    'id': 'count',
                    'rating': 'mean'
                }).round(1)
                genre_stats.columns = ['독서량', '평균 평점']
                genre_stats = genre_stats.sort_values('독서량', ascending=False)
                st.dataframe(genre_stats)
                
            else:
                st.info("독후감 데이터가 없습니다. 먼저 독후감을 작성해보세요.")
    
    elif page == "📊 통합 대시보드":
        st.title("📊 통합 대시보드")
        
        # 데이터 불러오기
        conn = sqlite3.connect('feedback_analysis.db')
        personal_data = pd.read_sql_query("SELECT * FROM personal_records", conn)
        book_reviews_data = pd.read_sql_query("SELECT * FROM book_reviews", conn)
        
        # 최근 독후감 조회
        recent_reviews = pd.read_sql_query('''
            SELECT br.title, br.author, br.read_date, g.name as genre_name, br.rating
            FROM book_reviews br
            JOIN genres g ON br.genre_id = g.id
            ORDER BY br.created_at DESC
            LIMIT 5
        ''', conn)
        
        # 이번 달 독후감 수
        current_month = datetime.now().strftime('%Y-%m')
        monthly_review_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM book_reviews WHERE strftime('%Y-%m', read_date) = ?", 
            conn, params=[current_month]
        ).iloc[0]['count']
        
        conn.close()
        
        if len(personal_data) == 0 and len(book_reviews_data) == 0:
            st.info("분석할 데이터가 없습니다. 먼저 독후감을 작성하거나 개인 기록을 추가해주세요.")
        else:
            # 전체 통계
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📖 총 독후감", len(book_reviews_data))
            with col2:
                st.metric("📅 이번 달 독후감", monthly_review_count)
            with col3:
                st.metric("📚 총 개인 기록", len(personal_data))
            with col4:
                if len(book_reviews_data) > 0:
                    avg_book_rating = book_reviews_data['rating'].mean()
                    st.metric("⭐ 평균 독서 평점", f"{avg_book_rating:.1f}" if pd.notna(avg_book_rating) else "평점 없음")
            
            # 목표 달성률 (월간 목표 10권 가정)
            monthly_goal = 10
            goal_achievement = min(100, (monthly_review_count / monthly_goal) * 100)
            
            st.subheader("🎯 이번 달 독서 목표")
            col1, col2 = st.columns([2, 1])
            with col1:
                st.progress(goal_achievement / 100)
            with col2:
                st.metric("달성률", f"{goal_achievement:.1f}%", f"{monthly_review_count}/{monthly_goal}권")
            
            # 최근 등록 독후감
            if len(recent_reviews) > 0:
                st.subheader("📖 최근 등록 독후감")
                for _, review in recent_reviews.iterrows():
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            rating_display = f"⭐{int(review['rating'])}" if pd.notna(review['rating']) else "평점 없음"
                            st.markdown(f"**{review['title']}** - {review['author']} | {review['genre_name']} | {rating_display}")
                        with col2:
                            st.caption(f"읽은 날짜: {review['read_date']}")
                        st.divider()
            
            # 시각화
            if len(book_reviews_data) > 0:
                st.subheader("📊 독서 분석")
                col1, col2 = st.columns(2)
                
                with col1:
                    # 장르별 독서 분포
                    conn = sqlite3.connect('feedback_analysis.db')
                    genre_review_data = pd.read_sql_query('''
                        SELECT g.name as genre_name, COUNT(*) as count
                        FROM book_reviews br
                        JOIN genres g ON br.genre_id = g.id
                        GROUP BY g.name
                        ORDER BY count DESC
                    ''', conn)
                    conn.close()
                    
                    if len(genre_review_data) > 0:
                        fig_genre_review = px.pie(
                            values=genre_review_data['count'],
                            names=genre_review_data['genre_name'],
                            title="장르별 독서 분포"
                        )
                        st.plotly_chart(fig_genre_review, use_container_width=True)
                
                with col2:
                    # 독서 평점 분포
                    rating_data = book_reviews_data[book_reviews_data['rating'].notna()]
                    if len(rating_data) > 0:
                        rating_counts = rating_data['rating'].value_counts().sort_index()
                        fig_rating_review = px.bar(
                            x=rating_counts.index,
                            y=rating_counts.values,
                            title="독서 평점 분포",
                            labels={'x': '평점', 'y': '개수'}
                        )
                        st.plotly_chart(fig_rating_review, use_container_width=True)
                    else:
                        st.info("독서 평점 데이터가 없습니다.")
                
                # 독서 트렌드
                st.subheader("📈 독서 트렌드")
                book_reviews_data['read_date'] = pd.to_datetime(book_reviews_data['read_date'])
                monthly_book_counts = book_reviews_data.groupby(book_reviews_data['read_date'].dt.to_period('M')).size()
                
                fig_book_trend = px.line(
                    x=[str(period) for period in monthly_book_counts.index],
                    y=monthly_book_counts.values,
                    title="월별 독서량 추이",
                    labels={'x': '월', 'y': '독서량'}
                )
                st.plotly_chart(fig_book_trend, use_container_width=True)
            
            if len(personal_data) > 0:
                st.subheader("📚 개인 기록 분석")
                col1, col2 = st.columns(2)
                
                with col1:
                    type_counts = personal_data['type'].value_counts()
                    fig_type = px.pie(
                        values=type_counts.values,
                        names=type_counts.index,
                        title="기록 유형별 분포"
                    )
                    st.plotly_chart(fig_type, use_container_width=True)
                
                with col2:
                    # 시간별 기록 트렌드
                    personal_data['date_created'] = pd.to_datetime(personal_data['date_created'])
                    daily_counts = personal_data.groupby(personal_data['date_created'].dt.date).size()
                    
                    fig_trend = px.line(
                        x=daily_counts.index,
                        y=daily_counts.values,
                        title="일별 기록 트렌드",
                        labels={'x': '날짜', 'y': '기록 수'}
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
    
    elif page == "📄 보고서 생성":
        st.title("📄 보고서 생성")
        
        # 데이터 불러오기
        conn = sqlite3.connect('feedback_analysis.db')
        personal_data = pd.read_sql_query("SELECT * FROM personal_records", conn)
        book_reviews_data = pd.read_sql_query("SELECT * FROM book_reviews", conn)
        conn.close()
        
        if len(personal_data) == 0 and len(book_reviews_data) == 0:
            st.info("보고서를 생성할 데이터가 없습니다.")
        else:
            st.subheader("📊 보고서 옵션")
            
            report_type = st.selectbox("보고서 유형", ["독후감 분석", "개인 기록", "통합 보고서"])
            
            if st.button("📄 PDF 보고서 생성"):
                if report_type == "독후감 분석" and len(book_reviews_data) > 0:
                    # 독후감 PDF 생성
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    title = Paragraph("독후감 분석 보고서", styles['Title'])
                    story.append(title)
                    story.append(Spacer(1, 12))
                    
                    # 장르별 통계 조회
                    conn = sqlite3.connect('feedback_analysis.db')
                    genre_stats = pd.read_sql_query('''
                        SELECT g.name as genre_name, COUNT(*) as count, AVG(br.rating) as avg_rating
                        FROM book_reviews br
                        JOIN genres g ON br.genre_id = g.id
                        GROUP BY g.name
                        ORDER BY count DESC
                    ''', conn)
                    conn.close()
                    
                    summary = f"""
                    <b>독후감 요약</b><br/>
                    • 총 독후감 수: {len(book_reviews_data)}개<br/>
                    • 평균 평점: {book_reviews_data['rating'].mean():.1f}<br/>
                    • 가장 많이 읽은 장르: {genre_stats.iloc[0]['genre_name'] if len(genre_stats) > 0 else '없음'}<br/>
                    """
                    story.append(Paragraph(summary, styles['Normal']))
                    story.append(Spacer(1, 12))
                    
                    # 장르별 통계 테이블
                    if len(genre_stats) > 0:
                        story.append(Paragraph("장르별 독서 통계", styles['Heading2']))
                        table_data = [['장르', '독서량', '평균 평점']]
                        for _, row in genre_stats.iterrows():
                            avg_rating = f"{row['avg_rating']:.1f}" if pd.notna(row['avg_rating']) else "평점 없음"
                            table_data.append([row['genre_name'], str(row['count']), avg_rating])
                        
                        table = Table(table_data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 14),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(table)
                        story.append(Spacer(1, 12))
                    
                    # 독후감 목록
                    story.append(Paragraph("독후감 목록", styles['Heading2']))
                    table_data = [['제목', '저자', '읽은 날짜', '평점']]
                    for _, row in book_reviews_data.head(20).iterrows():  # 상위 20개만 표시
                        rating_str = str(row['rating']) if pd.notna(row['rating']) else "평점 없음"
                        table_data.append([
                            row['title'][:30] + '...' if len(row['title']) > 30 else row['title'],
                            row['author'][:20] + '...' if len(row['author']) > 20 else row['author'],
                            str(row['read_date']),
                            rating_str
                        ])
                    
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    
                    doc.build(story)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=buffer.getvalue(),
                        file_name="book_reviews_report.pdf",
                        mime="application/pdf"
                    )
                    st.success("독후감 PDF 보고서가 생성되었습니다!")
                
                elif report_type == "개인 기록" and len(personal_data) > 0:
                    # 개인 기록용 PDF 생성 (간단한 버전)
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    title = Paragraph("개인 기록 보고서", styles['Title'])
                    story.append(title)
                    story.append(Spacer(1, 12))
                    
                    summary = f"""
                    <b>기록 요약</b><br/>
                    • 총 기록 수: {len(personal_data)}개<br/>
                    • 평균 평점: {personal_data['rating'].mean():.1f}<br/>
                    • 가장 많은 유형: {personal_data['type'].mode().iloc[0] if len(personal_data) > 0 else '없음'}<br/>
                    """
                    story.append(Paragraph(summary, styles['Normal']))
                    story.append(Spacer(1, 12))
                    
                    # 기록 목록
                    table_data = [['제목', '유형', '평점', '작성일']]
                    for _, row in personal_data.iterrows():
                        table_data.append([
                            row['title'][:30] + '...' if len(row['title']) > 30 else row['title'],
                            row['type'],
                            str(row['rating']),
                            str(row['date_created'])[:10]
                        ])
                    
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 14),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    
                    doc.build(story)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=buffer.getvalue(),
                        file_name="personal_records_report.pdf",
                        mime="application/pdf"
                    )
                    st.success("개인 기록 PDF 보고서가 생성되었습니다!")
                
                elif report_type == "독후감 분석" and len(book_reviews_data) > 0:
                    # 독후감 PDF 생성
                    buffer = io.BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    title = Paragraph("독후감 분석 보고서", styles['Title'])
                    story.append(title)
                    story.append(Spacer(1, 12))
                    
                    # 장르별 통계 조회
                    conn = sqlite3.connect('feedback_analysis.db')
                    genre_stats = pd.read_sql_query('''
                        SELECT g.name as genre_name, COUNT(*) as count, AVG(br.rating) as avg_rating
                        FROM book_reviews br
                        JOIN genres g ON br.genre_id = g.id
                        GROUP BY g.name
                        ORDER BY count DESC
                    ''', conn)
                    conn.close()
                    
                    summary = f"""
                    <b>독후감 요약</b><br/>
                    • 총 독후감 수: {len(book_reviews_data)}개<br/>
                    • 평균 평점: {book_reviews_data['rating'].mean():.1f}<br/>
                    • 가장 많이 읽은 장르: {genre_stats.iloc[0]['genre_name'] if len(genre_stats) > 0 else '없음'}<br/>
                    """
                    story.append(Paragraph(summary, styles['Normal']))
                    story.append(Spacer(1, 12))
                    
                    # 장르별 통계 테이블
                    if len(genre_stats) > 0:
                        story.append(Paragraph("장르별 독서 통계", styles['Heading2']))
                        table_data = [['장르', '독서량', '평균 평점']]
                        for _, row in genre_stats.iterrows():
                            avg_rating = f"{row['avg_rating']:.1f}" if pd.notna(row['avg_rating']) else "평점 없음"
                            table_data.append([row['genre_name'], str(row['count']), avg_rating])
                        
                        table = Table(table_data)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 14),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        story.append(table)
                        story.append(Spacer(1, 12))
                    
                    # 독후감 목록
                    story.append(Paragraph("독후감 목록", styles['Heading2']))
                    table_data = [['제목', '저자', '장르', '읽은 날짜', '평점']]
                    for _, row in book_reviews_data.head(20).iterrows():  # 상위 20개만 표시
                        rating_str = str(row['rating']) if pd.notna(row['rating']) else "평점 없음"
                        table_data.append([
                            row['title'][:30] + '...' if len(row['title']) > 30 else row['title'],
                            row['author'][:20] + '...' if len(row['author']) > 20 else row['author'],
                            "장르",  # 장르명은 별도 조회 필요
                            str(row['read_date']),
                            rating_str
                        ])
                    
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    
                    doc.build(story)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=buffer.getvalue(),
                        file_name="book_reviews_report.pdf",
                        mime="application/pdf"
                    )
                    st.success("독후감 PDF 보고서가 생성되었습니다!")
                
                else:
                    st.warning("선택한 보고서 유형에 대한 데이터가 없습니다.")
            
            # Markdown 보고서 생성
            if st.button("📝 Markdown 보고서 생성"):
                if report_type == "독후감 분석" and len(book_reviews_data) > 0:
                    # 장르별 통계 조회
                    conn = sqlite3.connect('feedback_analysis.db')
                    genre_stats = pd.read_sql_query('''
                        SELECT g.name as genre_name, COUNT(*) as count, AVG(br.rating) as avg_rating
                        FROM book_reviews br
                        JOIN genres g ON br.genre_id = g.id
                        GROUP BY g.name
                        ORDER BY count DESC
                    ''', conn)
                    conn.close()
                    
                    markdown_content = f"""# 독후감 분석 보고서

## 요약
- 총 독후감 수: {len(book_reviews_data)}개
- 평균 평점: {book_reviews_data['rating'].mean():.1f}
- 가장 많이 읽은 장르: {genre_stats.iloc[0]['genre_name'] if len(genre_stats) > 0 else '없음'}

## 장르별 독서 통계
"""
                    for _, row in genre_stats.iterrows():
                        avg_rating = f"{row['avg_rating']:.1f}" if pd.notna(row['avg_rating']) else "평점 없음"
                        markdown_content += f"- **{row['genre_name']}**: {row['count']}권, 평균 평점 {avg_rating}\n"
                    
                    markdown_content += "\n## 독후감 목록\n"
                    for _, row in book_reviews_data.iterrows():
                        rating_str = f"⭐{int(row['rating'])}" if pd.notna(row['rating']) else "평점 없음"
                        markdown_content += f"""
### {row['title']}
- **저자**: {row['author']}
- **읽은 날짜**: {row['read_date']}
- **평점**: {rating_str}
- **독후감**: {row['content'][:200]}...

"""
                    
                    st.download_button(
                        label="📥 Markdown 다운로드",
                        data=markdown_content,
                        file_name="book_reviews_report.md",
                        mime="text/markdown"
                    )
                    st.success("독후감 Markdown 보고서가 생성되었습니다!")
                
                elif report_type == "개인 기록" and len(personal_data) > 0:
                    markdown_content = f"""# 개인 기록 보고서

## 요약
- 총 기록 수: {len(personal_data)}개
- 평균 평점: {personal_data['rating'].mean():.1f}
- 가장 많은 유형: {personal_data['type'].mode().iloc[0] if len(personal_data) > 0 else '없음'}

## 기록 목록
"""
                    for _, row in personal_data.iterrows():
                        markdown_content += f"""
### {row['title']}
- **유형**: {row['type']}
- **평점**: {row['rating']}/5
- **내용**: {row['content']}
- **작성일**: {row['date_created']}

"""
                    
                    st.download_button(
                        label="📥 Markdown 다운로드",
                        data=markdown_content,
                        file_name="personal_records_report.md",
                        mime="text/markdown"
                    )
                    st.success("개인 기록 Markdown 보고서가 생성되었습니다!")
                
                elif report_type == "독후감 분석" and len(book_reviews_data) > 0:
                    # 장르별 통계 조회
                    conn = sqlite3.connect('feedback_analysis.db')
                    genre_stats = pd.read_sql_query('''
                        SELECT g.name as genre_name, COUNT(*) as count, AVG(br.rating) as avg_rating
                        FROM book_reviews br
                        JOIN genres g ON br.genre_id = g.id
                        GROUP BY g.name
                        ORDER BY count DESC
                    ''', conn)
                    conn.close()
                    
                    markdown_content = f"""# 독후감 분석 보고서

## 요약
- 총 독후감 수: {len(book_reviews_data)}개
- 평균 평점: {book_reviews_data['rating'].mean():.1f}
- 가장 많이 읽은 장르: {genre_stats.iloc[0]['genre_name'] if len(genre_stats) > 0 else '없음'}

## 장르별 독서 통계
"""
                    for _, row in genre_stats.iterrows():
                        avg_rating = f"{row['avg_rating']:.1f}" if pd.notna(row['avg_rating']) else "평점 없음"
                        markdown_content += f"- **{row['genre_name']}**: {row['count']}권, 평균 평점 {avg_rating}\n"
                    
                    markdown_content += "\n## 독후감 목록\n"
                    for _, row in book_reviews_data.iterrows():
                        rating_str = f"⭐{int(row['rating'])}" if pd.notna(row['rating']) else "평점 없음"
                        markdown_content += f"""
### {row['title']}
- **저자**: {row['author']}
- **읽은 날짜**: {row['read_date']}
- **평점**: {rating_str}
- **독후감**: {row['content'][:200]}...

"""
                    
                    st.download_button(
                        label="📥 Markdown 다운로드",
                        data=markdown_content,
                        file_name="book_reviews_report.md",
                        mime="text/markdown"
                    )
                    st.success("독후감 Markdown 보고서가 생성되었습니다!")
                
                else:
                    st.warning("선택한 보고서 유형에 대한 데이터가 없습니다.")

if __name__ == "__main__":
    main()

