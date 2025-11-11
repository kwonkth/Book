# 고객 피드백 분석 & 개인 기록 관리 시스템

## 📋 프로젝트 개요

이 프로젝트는 고객 피드백 데이터를 분석하여 주요 이슈와 감성 분포를 시각화하고, 동시에 개인 독서·취미 기록 관리 등 생활 데이터를 함께 관리/분석할 수 있는 Streamlit 웹 애플리케이션입니다.

## 🎯 주요 기능

### 📝 피드백 분석
- **감성 분석**: 피드백 텍스트에서 긍정, 부정, 중립 감성 분류
- **키워드 추출**: 자주 언급되는 주요 키워드 추출 및 시각화
- **데이터 업로드**: CSV 또는 Excel 파일 업로드 기능 지원
- **시각화**: 감성 분포 및 키워드 빈도 차트 제공

### 📚 개인 기록 관리
- **다양한 기록 유형**: 독서, 취미, 운동, 학습 등 다양한 카테고리 지원
- **평점 시스템**: 1-5점 평점 시스템으로 기록 평가
- **카테고리 분류**: 사용자 정의 카테고리로 기록 분류
- **통계 분석**: 유형별, 평점별 분포 시각화

### 📊 통합 대시보드
- **통합 시각화**: 피드백과 개인 기록 데이터의 통합 분석
- **필터링**: 기간, 카테고리별 분석 비교
- **트렌드 분석**: 시간별 데이터 변화 추이 분석

### 📄 보고서 생성
- **PDF 보고서**: 분석 결과를 PDF 형태로 내보내기
- **Markdown 보고서**: Markdown 형태의 보고서 생성
- **자동 요약**: 주요 인사이트와 통계 정보 자동 생성

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **데이터베이스**: SQLite
- **시각화**: Plotly
- **보고서**: ReportLab (PDF), Markdown
- **데이터 처리**: Pandas, NumPy

## 🚀 설치 및 실행

### 1. 저장소 클론
```bash
git clone <repository-url>
cd metoring
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 애플리케이션 실행
```bash
streamlit run app.py
```

### 5. 브라우저에서 접속
```
http://localhost:8501
```

## 📁 프로젝트 구조

```
metoring/
├── app.py                 # 메인 Streamlit 애플리케이션
├── requirements.txt       # Python 의존성 목록
├── README.md             # 프로젝트 문서
├── feedback_analysis.db  # SQLite 데이터베이스 (자동 생성)
└── cfa-streamlit-extended-prd.txt  # 프로젝트 요구사항 문서
```

## 💡 사용 방법

### 피드백 분석
1. **데이터 업로드**: CSV 또는 Excel 파일을 업로드합니다
2. **컬럼 선택**: 분석할 텍스트 컬럼을 선택합니다
3. **분석 실행**: "분석 시작" 버튼을 클릭하여 감성 분석을 실행합니다
4. **결과 확인**: 감성 분포 차트와 키워드 빈도 차트를 확인합니다

### 개인 기록 관리
1. **기록 추가**: 새 기록 폼을 작성하여 개인 기록을 추가합니다
2. **필터링**: 유형별, 카테고리별로 기록을 필터링합니다
3. **통계 확인**: 기록 유형별 분포와 평점 분포를 확인합니다

### 보고서 생성
1. **보고서 유형 선택**: 피드백 분석, 개인 기록, 또는 통합 보고서를 선택합니다
2. **형식 선택**: PDF 또는 Markdown 형식을 선택합니다
3. **다운로드**: 생성된 보고서를 다운로드합니다

## 🔧 주요 모듈

### 감성 분석
- 규칙 기반 감성 분석 (긍정/부정/중립 키워드 매칭)
- 확장 가능한 구조로 더 정교한 NLP 모델 적용 가능

### 키워드 추출
- 빈도 기반 키워드 추출
- 상위 N개 키워드 자동 선별

### 데이터 시각화
- Plotly를 활용한 인터랙티브 차트
- 감성 분포 파이 차트
- 키워드 빈도 막대 차트
- 시간별 트렌드 라인 차트

## 🌐 Streamlit Cloud 배포

이 애플리케이션은 Streamlit Cloud에서 배포할 수 있습니다:

1. GitHub 저장소에 코드 업로드
2. Streamlit Cloud에서 새 앱 생성
3. 저장소 연결 및 배포 설정
4. 자동 배포 완료

## 📈 향후 개선 계획

- [ ] 더 정교한 감성 분석 모델 적용 (BERT, KoBERT 등)
- [ ] 실시간 데이터 업데이트 기능
- [ ] 사용자 인증 시스템
- [ ] 데이터 백업 및 복원 기능
- [ ] API 엔드포인트 제공
- [ ] 모바일 반응형 UI 개선

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해 주세요.

---

**개발자**: AI Assistant  
**버전**: 1.0.0  
**최종 업데이트**: 2024년





