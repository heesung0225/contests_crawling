import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import json

KST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape_wevity():
    """위비티 IT/소프트웨어 공모전 크롤링"""
    contests = []
    base_url = "https://www.wevity.com/?c=find&s=1&gub=1&cidx=6&pagenum={page}"

    for page in range(1, 4):
        try:
            res = requests.get(base_url.format(page=page), headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            # 헤더(top 클래스) 제외한 실제 공모전 항목
            items = soup.select("ul.list > li:not(.top)")
            if not items:
                break

            for item in items:
                try:
                    a_tag = item.select_one("div.tit > a")
                    if not a_tag:
                        continue

                    # span 태그(신규, SPECIAL 뱃지) 텍스트 제거
                    for span in a_tag.find_all("span"):
                        span.decompose()
                    title = a_tag.get_text(strip=True)

                    href = a_tag.get("href", "")
                    link = "https://www.wevity.com/" + href.lstrip("?")
                    link = "https://www.wevity.com/" + href if not href.startswith("http") else href

                    sub_tit = item.select_one("div.sub-tit")
                    category = sub_tit.get_text(strip=True) if sub_tit else ""

                    organ = item.select_one("div.organ")
                    host = organ.get_text(strip=True) if organ else "-"

                    day_div = item.select_one("div.day")
                    if day_div:
                        dday_span = day_div.find("span")
                        status = dday_span.get_text(strip=True) if dday_span else ""
                        # D-숫자 또는 D-day 추출
                        day_text = day_div.get_text(separator=" ", strip=True)
                        dday = day_text.split()[0] if day_text else ""
                    else:
                        dday, status = "", ""

                    contests.append({
                        "title": title,
                        "host": host,
                        "category": category,
                        "dday": dday,
                        "status": status,
                        "link": "https://www.wevity.com/" + href,
                        "source": "위비티",
                    })
                except Exception:
                    continue

        except Exception as e:
            print(f"[wevity] page {page} error: {e}")
            break

    return contests


def scrape_contestkorea():
    """공모전 대통령 IT 공모전 크롤링"""
    contests = []
    # 030310: IT·컴퓨터 카테고리
    url = "https://www.contestkorea.com/sub/list.php?int_gbn=1&Txt_bcode=030310"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select("div.listStyle_1_wrap li a")
        for a_tag in items:
            try:
                # 번호와 NEW 이미지 제거 후 텍스트 추출
                for img in a_tag.find_all("img"):
                    img.decompose()
                title = a_tag.get_text(strip=True)
                # 앞 번호("1." 등) 제거
                import re
                title = re.sub(r"^\d+\.\s*", "", title).strip()
                if not title:
                    continue

                href = a_tag.get("href", "")
                link = "https://www.contestkorea.com" + href if href.startswith("/") else href

                contests.append({
                    "title": title,
                    "host": "-",
                    "category": "IT·컴퓨터",
                    "dday": "",
                    "status": "접수중",
                    "link": link,
                    "source": "공모전대통령",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[contestkorea] error: {e}")

    return contests


def generate_html(contests: list, updated_at: str) -> str:
    if not contests:
        cards_html = '<p style="text-align:center;color:#999;padding:3rem">현재 수집된 공모전이 없습니다.</p>'
    else:
        cards_html = ""
        for c in contests:
            dday = c.get("dday", "")
            # D-7 이하면 urgent
            urgent = False
            if dday.startswith("D-") and dday[2:].isdigit():
                urgent = int(dday[2:]) <= 7
            dday_class = "dday-urgent" if urgent else "dday-normal"
            dday_badge = f'<span class="dday-badge {dday_class}">{dday}</span>' if dday else ""
            status_badge = f'<span class="status-badge">{c["status"]}</span>' if c.get("status") else ""
            source_badge = f'<span class="source-badge">{c["source"]}</span>'
            category = f'<p class="card-category">{c["category"]}</p>' if c.get("category") else ""

            cards_html += f"""
        <div class="card">
          <div class="card-body">
            <div class="card-top">
              {source_badge}{dday_badge}{status_badge}
            </div>
            <a href="{c['link']}" target="_blank" class="card-title">{c['title']}</a>
            {category}
            <p class="card-host">🏢 {c['host']}</p>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IT 공모전 Daily</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', 'Apple SD Gothic Neo', Pretendard, sans-serif;
      background: #f0f4ff;
      color: #222;
    }}
    header {{
      background: linear-gradient(135deg, #1e3a8a, #3b82f6);
      color: white;
      padding: 2.5rem 1.5rem 2rem;
      text-align: center;
    }}
    header h1 {{ font-size: 2rem; letter-spacing: -0.5px; }}
    header p {{ margin-top: 0.4rem; opacity: 0.85; font-size: 0.95rem; }}
    .update-badge {{
      display: inline-block;
      margin-top: 0.9rem;
      background: rgba(255,255,255,0.2);
      padding: 0.35rem 1rem;
      border-radius: 999px;
      font-size: 0.82rem;
    }}
    .container {{
      max-width: 1000px;
      margin: 2rem auto;
      padding: 0 1rem;
    }}
    .count {{ margin-bottom: 1.2rem; font-size: 0.9rem; color: #555; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1.2rem;
    }}
    .card {{
      background: white;
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 2px 10px rgba(0,0,0,0.07);
      transition: transform 0.15s, box-shadow 0.15s;
    }}
    .card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }}
    .card-body {{ padding: 1.1rem; display: flex; flex-direction: column; gap: 0.5rem; }}
    .card-top {{ display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center; }}
    .card-title {{
      font-size: 0.95rem;
      font-weight: 600;
      color: #1e3a8a;
      text-decoration: none;
      line-height: 1.45;
      display: block;
    }}
    .card-title:hover {{ text-decoration: underline; }}
    .card-category {{ font-size: 0.78rem; color: #888; }}
    .card-host {{ font-size: 0.82rem; color: #666; }}
    .dday-badge, .status-badge, .source-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.18rem 0.55rem;
      border-radius: 999px;
    }}
    .dday-urgent {{ background: #fee2e2; color: #dc2626; }}
    .dday-normal {{ background: #dbeafe; color: #1d4ed8; }}
    .status-badge {{ background: #dcfce7; color: #16a34a; }}
    .source-badge {{ background: #f3f4f6; color: #6b7280; }}
    footer {{
      text-align: center;
      padding: 2.5rem 1rem;
      font-size: 0.8rem;
      color: #aaa;
      line-height: 2;
    }}
    footer a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <header>
    <h1>💻 IT 공모전 Daily</h1>
    <p>IT·소프트웨어 분야 공모전 정보를 매일 자동 수집합니다</p>
    <div class="update-badge">🔄 마지막 업데이트: {updated_at}</div>
  </header>
  <div class="container">
    <p class="count">총 <strong>{len(contests)}</strong>개의 공모전</p>
    <div class="grid">
      {cards_html}
    </div>
  </div>
  <footer>
    출처:
    <a href="https://www.wevity.com" target="_blank">위비티</a> ·
    <a href="https://www.contestkorea.com" target="_blank">공모전 대통령</a><br>
    매일 오전 9시(KST) GitHub Actions 자동 업데이트
  </footer>
</body>
</html>"""


def main():
    print("크롤링 시작...")
    contests = []

    wevity = scrape_wevity()
    print(f"  위비티: {len(wevity)}개")
    contests.extend(wevity)

    korea = scrape_contestkorea()
    print(f"  공모전대통령: {len(korea)}개")
    contests.extend(korea)

    # 중복 제거 (제목 기준)
    seen = set()
    unique = []
    for c in contests:
        if c["title"] not in seen:
            seen.add(c["title"])
            unique.append(c)
    contests = unique
    print(f"총 {len(contests)}개 (중복 제거 후)")

    now = datetime.now(KST).strftime("%Y년 %m월 %d일 %H:%M (KST)")
    html = generate_html(contests, now)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html 생성 완료")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": now, "count": len(contests), "contests": contests},
                  f, ensure_ascii=False, indent=2)
    print("data.json 생성 완료")


if __name__ == "__main__":
    main()
