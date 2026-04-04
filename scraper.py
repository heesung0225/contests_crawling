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
            if src:
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
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Apple SD Gothic Neo', 'Pretendard', sans-serif;
      background: #dde8f8;
      color: #1a1d2e;
      min-height: 100vh;
      overflow-x: hidden;
    }}

    /* ── 배경 오브 (연한 파스텔) ── */
    .bg {{
      position: fixed;
      inset: 0;
      z-index: 0;
      overflow: hidden;
      background: linear-gradient(145deg, #e8eeff 0%, #dce8f9 40%, #e4eeff 100%);
    }}
    .orb {{
      position: absolute;
      border-radius: 50%;
      filter: blur(100px);
      opacity: 0.45;
      animation: drift 24s ease-in-out infinite;
    }}
    .orb-1 {{ width: 700px; height: 700px; background: radial-gradient(circle, #a5b4fc, #c4b5fd); top: -200px; left: -150px; animation-delay: 0s; }}
    .orb-2 {{ width: 560px; height: 560px; background: radial-gradient(circle, #93c5fd, #bfdbfe); top: 100px; right: -100px; animation-delay: -8s; }}
    .orb-3 {{ width: 460px; height: 460px; background: radial-gradient(circle, #6ee7f7, #a5f3fc); bottom: -80px; left: 25%; animation-delay: -16s; }}
    .orb-4 {{ width: 340px; height: 340px; background: radial-gradient(circle, #f0abfc, #e879f9); bottom: 160px; right: 15%; animation-delay: -5s; }}

    @keyframes drift {{
      0%,100% {{ transform: translate(0,0) scale(1); }}
      33%      {{ transform: translate(30px,-25px) scale(1.05); }}
      66%      {{ transform: translate(-20px,20px) scale(0.96); }}
    }}

    /* ── 마우스 커서 스포트라이트 ── */
    .cursor-glow {{
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
    }}

    /* ── 페이지 레이어 ── */
    .page {{ position: relative; z-index: 1; }}

    /* ── 헤더 ── */
    header {{
      padding: 3rem 1.5rem 2.6rem;
      text-align: center;
    }}
    .header-card {{
      display: inline-block;
      background: rgba(255,255,255,0.55);
      backdrop-filter: blur(40px) saturate(180%);
      -webkit-backdrop-filter: blur(40px) saturate(180%);
      border: 1px solid rgba(255,255,255,0.85);
      border-radius: 30px;
      padding: 2.2rem 3.2rem;
      box-shadow:
        0 8px 32px rgba(100,120,200,0.12),
        0 2px 8px rgba(100,120,200,0.08),
        inset 0 1.5px 0 rgba(255,255,255,0.9);
      position: relative;
      overflow: hidden;
    }}
    .header-card::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(155deg, rgba(255,255,255,0.5) 0%, transparent 50%);
      border-radius: inherit;
      pointer-events: none;
    }}
    header h1 {{
      font-size: 2.2rem;
      font-weight: 700;
      letter-spacing: -0.8px;
      background: linear-gradient(135deg, #3730a3 0%, #6d28d9 60%, #0284c7 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
    header p {{
      margin-top: 0.45rem;
      color: rgba(30,30,80,0.5);
      font-size: 0.9rem;
    }}
    .update-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      margin-top: 1rem;
      background: rgba(255,255,255,0.6);
      border: 1px solid rgba(255,255,255,0.85);
      padding: 0.32rem 1rem;
      border-radius: 999px;
      font-size: 0.76rem;
      color: rgba(30,30,80,0.55);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
    }}

    /* ── 컨테이너 ── */
    .container {{
      max-width: 1100px;
      margin: 2rem auto;
      padding: 0 1.2rem;
    }}

    /* ── 툴바 ── */
    .toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.6rem;
      flex-wrap: wrap;
      gap: 0.8rem;
    }}
    .count {{
      font-size: 0.86rem;
      color: rgba(30,30,80,0.5);
    }}
    .count strong {{ color: rgba(30,30,80,0.8); }}

    .sort-group {{
      display: flex;
      background: rgba(255,255,255,0.55);
      backdrop-filter: blur(20px) saturate(160%);
      -webkit-backdrop-filter: blur(20px) saturate(160%);
      border: 1px solid rgba(255,255,255,0.8);
      border-radius: 999px;
      padding: 0.28rem;
      box-shadow: 0 2px 12px rgba(100,120,200,0.1);
    }}
    .sort-btn {{
      padding: 0.38rem 1.05rem;
      border: none;
      border-radius: 999px;
      background: transparent;
      font-size: 0.8rem;
      color: rgba(30,30,80,0.5);
      cursor: pointer;
      transition: all 0.18s;
      white-space: nowrap;
    }}
    .sort-btn:hover {{ color: #3730a3; background: rgba(255,255,255,0.5); }}
    .sort-btn.active {{
      background: rgba(255,255,255,0.85);
      color: #3730a3;
      font-weight: 600;
      box-shadow: 0 2px 10px rgba(100,120,200,0.15), inset 0 1px 0 rgba(255,255,255,1);
    }}

    /* ── 그리드 ── */
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.2rem;
    }}

    /* ── 카드 ── */
    .card {{
      background: rgba(255,255,255,0.45);
      backdrop-filter: blur(28px) saturate(180%);
      -webkit-backdrop-filter: blur(28px) saturate(180%);
      border: 1px solid rgba(255,255,255,0.8);
      border-radius: 22px;
      overflow: hidden;
      box-shadow:
        0 4px 20px rgba(100,120,200,0.10),
        0 1px 4px rgba(100,120,200,0.06),
        inset 0 1px 0 rgba(255,255,255,0.95);
      transition: transform 0.18s ease, box-shadow 0.18s ease;
      display: flex;
      flex-direction: column;
      position: relative;
      will-change: transform;
    }}
    /* 상단 하이라이트 */
    .card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 50%;
      background: linear-gradient(to bottom, rgba(255,255,255,0.45), transparent);
      border-radius: 22px 22px 0 0;
      pointer-events: none;
      z-index: 1;
    }}
    /* 마우스 반사광 */
    .card::after {{
      content: '';
      position: absolute;
      inset: 0;
      border-radius: inherit;
      background: radial-gradient(
        220px circle at var(--mx, 50%) var(--my, 50%),
        rgba(255,255,255,0.32) 0%,
        transparent 70%
      );
      opacity: 0;
      transition: opacity 0.22s;
      pointer-events: none;
      z-index: 2;
    }}
    .card:hover::after {{ opacity: 1; }}
    .card:hover {{
      box-shadow:
        0 12px 40px rgba(100,120,200,0.18),
        0 2px 8px rgba(100,120,200,0.10),
        inset 0 1px 0 rgba(255,255,255,1);
    }}

    .card-img {{
      width: 100%;
      height: 164px;
      object-fit: cover;
      display: block;
    }}
    .card-img-placeholder {{
      width: 100%;
      height: 164px;
      background: linear-gradient(135deg, rgba(165,180,252,0.4), rgba(147,197,253,0.4));
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 3rem;
    }}

    .card-body {{
      padding: 1rem 1.15rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 0.48rem;
      flex: 1;
      position: relative;
      z-index: 3;
    }}
    .card-top {{ display: flex; gap: 0.3rem; flex-wrap: wrap; align-items: center; }}
    .card-title {{
      font-size: 0.91rem;
      font-weight: 600;
      color: #1e1b4b;
      text-decoration: none;
      line-height: 1.5;
      display: block;
    }}
    .card-title:hover {{ color: #3730a3; text-decoration: underline; text-underline-offset: 3px; }}
    .card-category {{ font-size: 0.73rem; color: rgba(30,27,75,0.38); }}
    .card-host {{ font-size: 0.8rem; color: rgba(30,27,75,0.5); }}
    .card-deadline {{
      margin-top: auto;
      padding-top: 0.6rem;
      border-top: 1px solid rgba(100,120,200,0.1);
      font-size: 0.77rem;
      color: rgba(30,27,75,0.45);
    }}

    /* ── 배지 ── */
    .badge {{
      font-size: 0.67rem;
      font-weight: 600;
      padding: 0.19rem 0.58rem;
      border-radius: 999px;
      white-space: nowrap;
    }}
    .badge-urgent  {{ background: rgba(239,68,68,0.12);  border: 1px solid rgba(239,68,68,0.25);  color: #dc2626; }}
    .badge-normal  {{ background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.25); color: #2563eb; }}
    .badge-done    {{ background: rgba(0,0,0,0.05);      border: 1px solid rgba(0,0,0,0.1);       color: rgba(30,27,75,0.4); }}
    .badge-status  {{ background: rgba(34,197,94,0.12);  border: 1px solid rgba(34,197,94,0.25);  color: #16a34a; }}
    .badge-source  {{ background: rgba(255,255,255,0.7); border: 1px solid rgba(100,120,200,0.2); color: rgba(30,27,75,0.55); }}

    .no-results {{
      text-align: center;
      color: rgba(30,27,75,0.35);
      padding: 5rem 1rem;
      grid-column: 1 / -1;
    }}

    /* ── 푸터 ── */
    footer {{
      text-align: center;
      padding: 3rem 1rem;
      font-size: 0.77rem;
      color: rgba(30,27,75,0.35);
      line-height: 2.2;
      position: relative;
      z-index: 1;
    }}
    footer a {{ color: #6366f1; text-decoration: none; }}
    footer a:hover {{ color: #4338ca; }}
  </style>
</head>
<body>

  <div class="bg">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="orb orb-4"></div>
  </div>
  <div class="cursor-glow" id="cursorGlow"></div>

  <div class="page">
    <header>
      <div class="header-card">
        <h1>💻 IT 공모전 Daily</h1>
        <p>IT·소프트웨어 분야 공모전 정보를 매일 자동 수집합니다</p>
        <div class="update-badge">🔄 마지막 업데이트: {updated_at}</div>
      </div>
    </header>

    <div class="container">
      <div class="toolbar">
        <p class="count" id="count-label">총 <strong>{len(contests)}</strong>개의 공모전</p>
        <div class="sort-group">
          <button class="sort-btn active" onclick="sortContests('dday', event)">📅 마감순</button>
          <button class="sort-btn" onclick="sortContests('latest', event)">🆕 최신순</button>
          <button class="sort-btn" onclick="sortContests('title', event)">가나다순</button>
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
  </div>

  <script>
    const ALL_CONTESTS = {contests_json};

    /* ── 전역 커서 스포트라이트 ── */
    const cursorGlow = document.getElementById('cursorGlow');
    document.addEventListener('mousemove', (e) => {{
      cursorGlow.style.background =
        `radial-gradient(480px circle at ${{e.clientX}}px ${{e.clientY}}px,
          rgba(99,102,241,0.10) 0%,
          rgba(139,92,246,0.06) 35%,
          transparent 65%)`;
    }});

    /* ── 카드별 반사광 + 3D 틸트 ── */
    function initCards() {{
      document.getElementById('grid').addEventListener('mousemove', (e) => {{
        const card = e.target.closest('.card');
        if (!card) return;
        const r = card.getBoundingClientRect();
        const x = e.clientX - r.left;
        const y = e.clientY - r.top;
        const cx = x / r.width;
        const cy = y / r.height;
        card.style.setProperty('--mx', (cx * 100) + '%');
        card.style.setProperty('--my', (cy * 100) + '%');
        const rx = (cy - 0.5) * -10;
        const ry = (cx - 0.5) *  10;
        card.style.transform = `perspective(700px) rotateX(${{rx}}deg) rotateY(${{ry}}deg) translateY(-4px)`;
      }});
      document.getElementById('grid').addEventListener('mouseleave', (e) => {{
        const card = e.target.closest('.card');
        if (card) card.style.transform = '';
      }}, true);
    }}

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
      const ddayBadge   = getDdayBadge(c.dday, c.dday_num);
      const statusBadge = c.status ? `<span class="badge badge-status">${{c.status}}</span>` : '';
      const sourceBadge = `<span class="badge badge-source">${{c.source}}</span>`;
      const categoryHtml = c.category ? `<p class="card-category">${{c.category}}</p>` : '';
      const deadlineHtml = c.dday ? `<div class="card-deadline">⏰ 마감: ${{c.dday}}</div>` : '';
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

    function render(list) {{
      document.getElementById('grid').innerHTML = list.map(renderCard).join('');
    }}

    function sortContests(mode, e) {{
      document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      let sorted = [...ALL_CONTESTS];
      if (mode === 'dday')  sorted.sort((a, b) => a.dday_num - b.dday_num);
      else if (mode === 'title') sorted.sort((a, b) => a.title.localeCompare(b.title, 'ko'));
      render(sorted);
    }}

    (function () {{
      render([...ALL_CONTESTS].sort((a, b) => a.dday_num - b.dday_num));
      initCards();
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
