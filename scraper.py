import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import json
import time
import re

KST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get_og_image(url: str) -> str:
    """상세 페이지에서 og:image 썸네일 가져오기"""
    try:
        res = SESSION.get(url, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        og = soup.find("meta", property="og:image")
        if og:
            src = og.get("content", "")
            if src and "upload/contest" in src:
                return src
    except Exception:
        pass
    return ""


def parse_dday_number(dday: str) -> int:
    """D-13 → 13, D-day → 0, D+5 → -5, 없으면 9999"""
    if not dday:
        return 9999
    dday = dday.strip()
    if dday in ("D-day", "D-Day", "오늘마감"):
        return 0
    m = re.match(r"D[-−](\d+)", dday)
    if m:
        return int(m.group(1))
    m = re.match(r"D\+(\d+)", dday)
    if m:
        return -int(m.group(1))
    return 9999


def scrape_wevity():
    """위비티 IT/소프트웨어 공모전 크롤링 (썸네일 포함)"""
    contests = []
    base_url = "https://www.wevity.com/?c=find&s=1&gub=1&cidx=6&pagenum={page}"

    for page in range(1, 4):
        try:
            res = SESSION.get(base_url.format(page=page), timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            items = soup.select("ul.list > li:not(.top)")
            if not items:
                break

            for item in items:
                try:
                    a_tag = item.select_one("div.tit > a")
                    if not a_tag:
                        continue

                    href = a_tag.get("href", "")
                    detail_url = "https://www.wevity.com/" + href

                    for span in a_tag.find_all("span"):
                        span.decompose()
                    title = a_tag.get_text(strip=True)

                    sub_tit = item.select_one("div.sub-tit")
                    category = sub_tit.get_text(strip=True) if sub_tit else ""

                    organ = item.select_one("div.organ")
                    host = organ.get_text(strip=True) if organ else "-"

                    day_div = item.select_one("div.day")
                    dday, status = "", ""
                    if day_div:
                        dday_span = day_div.find("span")
                        status = dday_span.get_text(strip=True) if dday_span else ""
                        day_text = day_div.get_text(separator=" ", strip=True)
                        dday = day_text.split()[0] if day_text else ""

                    # 상세 페이지에서 썸네일 가져오기
                    thumb = get_og_image(detail_url)
                    time.sleep(0.2)

                    contests.append({
                        "title": title,
                        "host": host,
                        "category": category,
                        "dday": dday,
                        "dday_num": parse_dday_number(dday),
                        "status": status,
                        "link": detail_url,
                        "thumb": thumb,
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
    url = "https://www.contestkorea.com/sub/list.php?int_gbn=1&Txt_bcode=030310"

    try:
        res = SESSION.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select("div.listStyle_1_wrap li a")
        for a_tag in items:
            try:
                for img in a_tag.find_all("img"):
                    img.decompose()
                title = a_tag.get_text(strip=True)
                title = re.sub(r"^\d+\.\s*", "", title).strip()
                if not title:
                    continue

                href = a_tag.get("href", "")
                detail_url = "https://www.contestkorea.com" + href if href.startswith("/") else href

                # 상세 페이지 og:image
                thumb = get_og_image(detail_url)
                time.sleep(0.2)

                contests.append({
                    "title": title,
                    "host": "-",
                    "category": "IT·컴퓨터",
                    "dday": "",
                    "dday_num": 9999,
                    "status": "접수중",
                    "link": detail_url,
                    "thumb": thumb,
                    "source": "공모전대통령",
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[contestkorea] error: {e}")

    return contests


def generate_html(contests: list, updated_at: str) -> str:
    contests_json = json.dumps(contests, ensure_ascii=False)

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
      min-height: 100vh;
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
      max-width: 1040px;
      margin: 2rem auto;
      padding: 0 1rem;
    }}
    .toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.2rem;
      flex-wrap: wrap;
      gap: 0.6rem;
    }}
    .count {{ font-size: 0.9rem; color: #555; }}
    .sort-group {{
      display: flex;
      gap: 0.4rem;
    }}
    .sort-btn {{
      padding: 0.4rem 0.9rem;
      border: 1.5px solid #d1d5db;
      border-radius: 999px;
      background: white;
      font-size: 0.82rem;
      color: #555;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .sort-btn:hover {{ border-color: #3b82f6; color: #1d4ed8; }}
    .sort-btn.active {{
      background: #3b82f6;
      border-color: #3b82f6;
      color: white;
      font-weight: 600;
    }}
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
      display: flex;
      flex-direction: column;
    }}
    .card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.13);
    }}
    .card-img {{
      width: 100%;
      height: 150px;
      object-fit: cover;
      display: block;
    }}
    .card-img-placeholder {{
      width: 100%;
      height: 150px;
      background: linear-gradient(135deg, #e0e7ff, #bfdbfe);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2.5rem;
    }}
    .card-body {{
      padding: 1rem 1.1rem 1.1rem;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      flex: 1;
    }}
    .card-top {{
      display: flex;
      gap: 0.35rem;
      flex-wrap: wrap;
      align-items: center;
    }}
    .card-title {{
      font-size: 0.93rem;
      font-weight: 600;
      color: #1e3a8a;
      text-decoration: none;
      line-height: 1.45;
      display: block;
    }}
    .card-title:hover {{ text-decoration: underline; }}
    .card-category {{ font-size: 0.75rem; color: #9ca3af; }}
    .card-host {{ font-size: 0.82rem; color: #6b7280; }}
    .card-deadline {{
      margin-top: auto;
      padding-top: 0.6rem;
      border-top: 1px solid #f3f4f6;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.8rem;
      color: #374151;
    }}
    .badge {{
      font-size: 0.68rem;
      font-weight: 700;
      padding: 0.18rem 0.55rem;
      border-radius: 999px;
      white-space: nowrap;
    }}
    .badge-urgent {{ background: #fee2e2; color: #dc2626; }}
    .badge-normal {{ background: #dbeafe; color: #1d4ed8; }}
    .badge-done {{ background: #f3f4f6; color: #9ca3af; }}
    .badge-status {{ background: #dcfce7; color: #16a34a; }}
    .badge-source {{ background: #f3f4f6; color: #6b7280; }}
    .no-results {{
      text-align: center;
      color: #9ca3af;
      padding: 4rem 1rem;
      grid-column: 1 / -1;
    }}
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
    <div class="toolbar">
      <p class="count" id="count-label">총 <strong>{len(contests)}</strong>개의 공모전</p>
      <div class="sort-group">
        <button class="sort-btn active" onclick="sortContests('dday')">📅 마감순</button>
        <button class="sort-btn" onclick="sortContests('latest')">🆕 최신순</button>
        <button class="sort-btn" onclick="sortContests('title')">가나다순</button>
      </div>
    </div>
    <div class="grid" id="grid"></div>
  </div>

  <footer>
    출처:
    <a href="https://www.wevity.com" target="_blank">위비티</a> ·
    <a href="https://www.contestkorea.com" target="_blank">공모전 대통령</a><br>
    매일 오전 9시(KST) GitHub Actions 자동 업데이트
  </footer>

  <script>
    const ALL_CONTESTS = {contests_json};
    let currentSort = 'dday';

    function getDdayBadge(dday, ddayNum) {{
      if (!dday) return '';
      if (ddayNum < 0) return `<span class="badge badge-done">${{dday}}</span>`;
      if (ddayNum === 0) return `<span class="badge badge-urgent">D-day</span>`;
      if (ddayNum <= 7) return `<span class="badge badge-urgent">${{dday}}</span>`;
      return `<span class="badge badge-normal">${{dday}}</span>`;
    }}

    function renderCard(c) {{
      const imgHtml = c.thumb
        ? `<img class="card-img" src="${{c.thumb}}" alt="${{c.title}}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=card-img-placeholder>💻</div>'">`
        : `<div class="card-img-placeholder">💻</div>`;

      const ddayBadge = getDdayBadge(c.dday, c.dday_num);
      const statusBadge = c.status ? `<span class="badge badge-status">${{c.status}}</span>` : '';
      const sourceBadge = `<span class="badge badge-source">${{c.source}}</span>`;
      const categoryHtml = c.category ? `<p class="card-category">${{c.category}}</p>` : '';
      const deadlineHtml = c.dday
        ? `<div class="card-deadline">⏰ 마감: ${{c.dday}}</div>`
        : '';

      return `
        <div class="card">
          ${{imgHtml}}
          <div class="card-body">
            <div class="card-top">${{sourceBadge}}${{ddayBadge}}${{statusBadge}}</div>
            <a href="${{c.link}}" target="_blank" class="card-title">${{c.title}}</a>
            ${{categoryHtml}}
            <p class="card-host">🏢 ${{c.host}}</p>
            ${{deadlineHtml}}
          </div>
        </div>`;
    }}

    function sortContests(mode) {{
      currentSort = mode;
      document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
      event.target.classList.add('active');

      let sorted = [...ALL_CONTESTS];
      if (mode === 'dday') {{
        sorted.sort((a, b) => a.dday_num - b.dday_num);
      }} else if (mode === 'latest') {{
        // 원래 순서 유지 (수집 순서 = 최신순)
        sorted = [...ALL_CONTESTS];
      }} else if (mode === 'title') {{
        sorted.sort((a, b) => a.title.localeCompare(b.title, 'ko'));
      }}

      const grid = document.getElementById('grid');
      grid.innerHTML = sorted.map(renderCard).join('');
    }}

    // 초기 렌더링 (마감순)
    (function() {{
      const sorted = [...ALL_CONTESTS].sort((a, b) => a.dday_num - b.dday_num);
      document.getElementById('grid').innerHTML = sorted.map(renderCard).join('');
    }})();
  </script>
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
