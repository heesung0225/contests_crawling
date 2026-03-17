import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import json
import os

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
    # cidx=6 : IT/소프트웨어 카테고리
    base_url = "https://www.wevity.com/?c=find&s=1&gub=1&cidx=6&pagenum={page}"

    for page in range(1, 4):  # 최대 3페이지
        try:
            url = base_url.format(page=page)
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            items = soup.select("ul.list-body > li")
            if not items:
                break

            for item in items:
                try:
                    title_tag = item.select_one("div.tit > a")
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    link = "https://www.wevity.com" + title_tag.get("href", "")

                    host_tag = item.select_one("div.host")
                    host = host_tag.get_text(strip=True) if host_tag else "-"

                    dday_tag = item.select_one("div.day > span.day")
                    dday = dday_tag.get_text(strip=True) if dday_tag else ""

                    date_tag = item.select_one("div.day")
                    date_text = date_tag.get_text(strip=True) if date_tag else "-"

                    prize_tag = item.select_one("div.prize")
                    prize = prize_tag.get_text(strip=True) if prize_tag else "-"

                    thumb_tag = item.select_one("div.thumb img")
                    thumb = thumb_tag.get("src", "") if thumb_tag else ""
                    if thumb and thumb.startswith("/"):
                        thumb = "https://www.wevity.com" + thumb

                    contests.append({
                        "title": title,
                        "host": host,
                        "dday": dday,
                        "date": date_text,
                        "prize": prize,
                        "link": link,
                        "thumb": thumb,
                    })
                except Exception:
                    continue

        except Exception as e:
            print(f"[wevity] page {page} error: {e}")
            break

    return contests


def scrape_contestkorea():
    """공모전 대통령 IT 공모전 크롤링 (보조)"""
    contests = []
    # Txt_bcode=030210 : IT/정보통신
    url = "https://www.contestkorea.com/sub/list.php?Txt_bcode=030210&int_gbn=1"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select("ul.list_style_1 > li")
        for item in items:
            try:
                a_tag = item.select_one("div.list_con_tit > a")
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                link = "https://www.contestkorea.com/sub/" + a_tag.get("href", "").lstrip("./")

                host_tag = item.select_one("span.icon_organizer")
                host = host_tag.get_text(strip=True) if host_tag else "-"

                date_tag = item.select_one("span.icon_date")
                date_text = date_tag.get_text(strip=True) if date_tag else "-"

                prize_tag = item.select_one("span.icon_prize")
                prize = prize_tag.get_text(strip=True) if prize_tag else "-"

                contests.append({
                    "title": title,
                    "host": host,
                    "dday": "",
                    "date": date_text,
                    "prize": prize,
                    "link": link,
                    "thumb": "",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[contestkorea] error: {e}")

    return contests


def generate_html(contests: list, updated_at: str) -> str:
    cards_html = ""
    for c in contests:
        thumb_html = (
            f'<img src="{c["thumb"]}" alt="thumbnail" class="card-thumb" onerror="this.style.display=\'none\'">'
            if c["thumb"] else ""
        )
        dday_class = "dday-urgent" if c["dday"].startswith("D-") and any(
            c["dday"].replace("D-", "").isdigit() and int(c["dday"].replace("D-", "")) <= 7
            for _ in [1]
        ) else "dday-normal"
        dday_badge = f'<span class="dday-badge {dday_class}">{c["dday"]}</span>' if c["dday"] else ""

        cards_html += f"""
        <div class="card">
            {thumb_html}
            <div class="card-body">
                <div class="card-header-row">
                    <a href="{c['link']}" target="_blank" class="card-title">{c['title']}</a>
                    {dday_badge}
                </div>
                <p class="card-host">{c['host']}</p>
                <div class="card-footer">
                    <span class="card-date">📅 {c['date']}</span>
                    <span class="card-prize">🏆 {c['prize']}</span>
                </div>
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
      font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
      background: #f0f4ff;
      color: #222;
      min-height: 100vh;
    }}
    header {{
      background: linear-gradient(135deg, #1e3a8a, #3b82f6);
      color: white;
      padding: 2rem 1.5rem 1.5rem;
      text-align: center;
    }}
    header h1 {{ font-size: 2rem; letter-spacing: -0.5px; }}
    header p {{ margin-top: 0.4rem; opacity: 0.85; font-size: 0.95rem; }}
    .update-badge {{
      display: inline-block;
      margin-top: 0.8rem;
      background: rgba(255,255,255,0.2);
      padding: 0.3rem 0.9rem;
      border-radius: 999px;
      font-size: 0.82rem;
    }}
    .container {{
      max-width: 960px;
      margin: 2rem auto;
      padding: 0 1rem;
    }}
    .count {{ margin-bottom: 1rem; font-size: 0.9rem; color: #555; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1.2rem;
    }}
    .card {{
      background: white;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      transition: transform 0.15s, box-shadow 0.15s;
      display: flex;
      flex-direction: column;
    }}
    .card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 6px 20px rgba(0,0,0,0.12);
    }}
    .card-thumb {{
      width: 100%;
      height: 140px;
      object-fit: cover;
    }}
    .card-body {{
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      flex: 1;
    }}
    .card-header-row {{
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
    }}
    .card-title {{
      font-size: 0.95rem;
      font-weight: 600;
      color: #1e3a8a;
      text-decoration: none;
      flex: 1;
      line-height: 1.4;
    }}
    .card-title:hover {{ text-decoration: underline; }}
    .dday-badge {{
      font-size: 0.72rem;
      font-weight: 700;
      padding: 0.15rem 0.5rem;
      border-radius: 999px;
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .dday-urgent {{ background: #fee2e2; color: #dc2626; }}
    .dday-normal {{ background: #dbeafe; color: #1d4ed8; }}
    .card-host {{ font-size: 0.82rem; color: #777; }}
    .card-footer {{
      display: flex;
      gap: 0.8rem;
      font-size: 0.8rem;
      color: #555;
      margin-top: auto;
    }}
    footer {{
      text-align: center;
      padding: 2rem;
      font-size: 0.8rem;
      color: #aaa;
    }}
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
    출처: <a href="https://www.wevity.com" target="_blank">위비티</a> ·
    <a href="https://www.contestkorea.com" target="_blank">공모전 대통령</a><br>
    매일 오전 9시(KST) 자동 업데이트
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
        json.dump({"updated_at": now, "count": len(contests), "contests": contests}, f, ensure_ascii=False, indent=2)
    print("data.json 생성 완료")


if __name__ == "__main__":
    main()
