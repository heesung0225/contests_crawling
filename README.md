# 💻 IT 공모전 Daily

IT·소프트웨어 분야 공모전 정보를 매일 자동 수집하여 웹페이지로 제공합니다.

## 🔗 웹페이지
👉 **[IT 공모전 Daily 바로가기](https://<YOUR_USERNAME>.github.io/<YOUR_REPO_NAME>/)**

## 📌 수집 출처
- [위비티](https://www.wevity.com) - IT/소프트웨어 카테고리
- [공모전 대통령](https://www.contestkorea.com) - IT/정보통신 카테고리

## ⚙️ 동작 방식
- **GitHub Actions**가 매일 오전 9시(KST)에 자동으로 크롤링 실행
- 수집된 데이터로 `index.html`과 `data.json`을 자동 업데이트
- **GitHub Pages**로 정적 웹페이지 배포

## 🗂️ 파일 구조
```
├── scraper.py          # 크롤링 + HTML 생성 스크립트
├── index.html          # 자동 생성되는 웹페이지
├── data.json           # 자동 생성되는 원본 데이터
├── requirements.txt    # Python 패키지
└── .github/workflows/
    └── update.yml      # 매일 자동 실행 워크플로우
```
