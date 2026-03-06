# app.py — İnci Holding Stratejik Teknoloji Bülteni
# Deploy: streamlit.io/cloud (ücretsiz, public link)

import re, time, json
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

import streamlit as st
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
import torch
from sentence_transformers import SentenceTransformer, util

# ══════════════════════════════════════════════════
#  SABİTLER
# ══════════════════════════════════════════════════
SOURCES = {
    "techcrunch":    {"name": "TechCrunch",       "rss": "https://techcrunch.com/feed/"},
    "wired":         {"name": "Wired",            "rss": "https://www.wired.com/feed/rss"},
    "arstechnica":   {"name": "Ars Technica",     "rss": "https://feeds.arstechnica.com/arstechnica/index"},
    "venturebeat":   {"name": "VentureBeat",      "rss": "https://venturebeat.com/feed/"},
    "mittech":       {"name": "MIT Tech Review",  "rss": "https://www.technologyreview.com/feed/"},
    "electrek":      {"name": "Electrek",         "rss": "https://electrek.co/feed/"},
    "ainews":        {"name": "AI News",          "rss": "https://www.artificialintelligence-news.com/feed/"},
    "thehackernews": {"name": "The Hacker News",  "rss": "https://feeds.feedburner.com/TheHackersNews"},
    "bleepingcomp":  {"name": "BleepingComputer", "rss": "https://www.bleepingcomputer.com/feed/"},
    "securityweek":  {"name": "SecurityWeek",     "rss": "https://www.securityweek.com/feed/"},
    "greenbiz":      {"name": "GreenBiz",         "rss": "https://www.greenbiz.com/rss.xml"},
    "cleantechnica": {"name": "CleanTechnica",    "rss": "https://cleantechnica.com/feed/"},
    "autonews":      {"name": "Automotive News",  "rss": "https://www.autonews.com/rss.xml"},
    "logmgmt":       {"name": "Logistics Mgmt",   "rss": "https://www.logisticsmgmt.com/rss"},
    "mfg_tomorrow":  {"name": "Mfg Tomorrow",     "rss": "https://www.manufacturingtomorrow.com/rss.xml"},
    "webrazzi":      {"name": "Webrazzi",         "rss": "https://webrazzi.com/feed/"},
    "egirisim":      {"name": "eGirişim",         "rss": "https://egirisim.com/feed/"},
    "bthaber":       {"name": "BT Haber",         "rss": "https://www.bthaber.com/feed/"},
    "webtekno":      {"name": "Webtekno",         "rss": "https://www.webtekno.com/rss.xml"},
    "donanimhaber":  {"name": "DonanımHaber",     "rss": "https://www.donanimhaber.com/rss/tum/"},
    "shiftdelete":   {"name": "ShiftDelete",      "rss": "https://shiftdelete.net/feed/"},
    "supplychain247":{"name": "Supply Chain 247", "rss": "https://www.supplychain247.com/rss"},
    "cisa_alerts":   {"name": "CISA Alerts",      "rss": "https://www.cisa.gov/cybersecurity-advisories/all.xml"},
    "startupwatch":  {"name": "Startups Watch",   "rss": "https://startups.watch/feed"},
}

TR_SOURCES       = {"webrazzi","egirisim","bthaber","webtekno","donanimhaber","shiftdelete"}
SECURITY_SOURCES = {"thehackernews","bleepingcomp","cisa_alerts","securityweek"}
CVE_PAT = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
SEC_KW  = ["cve","vulnerability","0day","exploit","ransomware","data breach",
           "malware","siber saldırı","siber güvenlik","veri ihlali","zafiyet"]

INCI_COMPANIES = {
    "Maxion İnci": {
        "sector": "Otomotiv ve Mobilite", "color": "#C0392B", "icon": "🚗",
        "keywords": ["alüminyum jant","sac jant","binek araç","wheel","rim",
                     "automotive manufacturing","oem supplier","lightweight materials",
                     "auto parts","akıllı fabrika","smart manufacturing"],
    },
    "Maxion Jantaş": {
        "sector": "Otomotiv ve Mobilite", "color": "#E74C3C", "icon": "🏗️",
        "keywords": ["ağır vasıta","ticari araç","kamyon jantı","steel wheel",
                     "commercial vehicle","stamping","heavy duty trucks","fleet vehicles"],
    },
    "İnci GS Yuasa": {
        "sector": "Enerji ve Depolama", "color": "#27AE60", "icon": "🔋",
        "keywords": ["akü","battery","enerji depolama","energy storage","lead-acid",
                     "lithium-ion","bms","electric vehicle battery","ev charging"],
    },
    "Vflow Tech": {
        "sector": "Enerji ve Depolama", "color": "#2ECC71", "icon": "⚡",
        "keywords": ["vanadyum redoks","akış bataryaları","flow battery",
                     "şebeke dengeleme","redox flow","microgrid","renewable grid"],
    },
    "İncitaş": {
        "sector": "Enerji ve Depolama", "color": "#F39C12", "icon": "☀️",
        "keywords": ["güneş enerjisi","solar","mikroinverter","off-grid",
                     "fotovoltaik","solar array","mobile energy"],
    },
    "Yusen İnci Lojistik": {
        "sector": "Lojistik ve Tedarik", "color": "#8E44AD", "icon": "📦",
        "keywords": ["lojistik","logistics","tedarik zinciri","supply chain",
                     "hava kargo","deniz kargo","warehouse management",
                     "freight","last mile","rota optimizasyonu"],
    },
    "ISM Minibar": {
        "sector": "Endüstriyel Soğutma", "color": "#2980B9", "icon": "🏨",
        "keywords": ["minibar","absorbe soğutma","peltier","otel ekipmanları",
                     "hospitality tech","compact fridge","akıllı otel"],
    },
    "Starcool": {
        "sector": "Endüstriyel Soğutma", "color": "#3498DB", "icon": "❄️",
        "keywords": ["araç buzdolabı","karavan soğutma","portable fridge",
                     "hvac","mobile cooling","soğuk zincir","cold chain"],
    },
    "Vinci B.V.": {
        "sector": "Girişim ve İnovasyon", "color": "#9B59B6", "icon": "🚀",
        "keywords": ["endüstriyel teknoloji girişimi","mobilite yatırımı",
                     "b2b saas","deep tech","corporate venture","sanayi 4.0 yatırımı"],
    },
    "İnci Holding (Genel)": {
        "sector": "Girişim ve İnovasyon", "color": "#8B1A1A", "icon": "🏢",
        "keywords": ["açık inovasyon","kurumsal inovasyon","sürdürülebilirlik",
                     "esg","endüstriyel dönüşüm","stratejik ortaklık","dijital dönüşüm"],
    },
}

MACRO_SECTORS = {
    "Otomotiv ve Mobilite":  ["Maxion İnci", "Maxion Jantaş"],
    "Enerji ve Depolama":    ["İnci GS Yuasa", "Vflow Tech", "İncitaş"],
    "Lojistik ve Tedarik":   ["Yusen İnci Lojistik"],
    "Endüstriyel Soğutma":   ["ISM Minibar", "Starcool"],
    "Girişim ve İnovasyon":  ["Vinci B.V.", "İnci Holding (Genel)"],
}
SECTOR_ICONS = {
    "Otomotiv ve Mobilite": "🚗", "Enerji ve Depolama": "🔋",
    "Lojistik ve Tedarik": "📦", "Endüstriyel Soğutma": "❄️",
    "Girişim ve İnovasyon": "🚀",
}

def normalize(t):  return re.sub(r"\s+", " ", (t or "").strip())
def parse_dt(s):
    try: return dtparser.parse(s)
    except: return datetime.now()
def get_sector(name):
    for s, cs in MACRO_SECTORS.items():
        if name in cs: return s
    return "Genel"

# ══════════════════════════════════════════════════
#  MODEL (bir kez yüklenir, cache'de kalır)
# ══════════════════════════════════════════════════
@st.cache_resource(show_spinner="🧠 NLP modeli yükleniyor (ilk seferinde ~30 sn)...")
def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model  = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=device)
    names    = list(INCI_COMPANIES.keys())
    kw_texts = [" ".join(INCI_COMPANIES[c]["keywords"]) for c in names]
    sec_texts= [INCI_COMPANIES[c]["sector"]             for c in names]
    emb_kw   = model.encode(kw_texts,  convert_to_tensor=True)
    emb_sec  = model.encode(sec_texts, convert_to_tensor=True)
    neg = ("telefon aksesuar oyun PlayStation bitcoin kripto magazin siyaset "
           "reality show indirim kampanya kasko sigorta taksi tüketici")
    emb_neg  = model.encode([neg], convert_to_tensor=True)
    return model, names, emb_kw, emb_sec, emb_neg

# ══════════════════════════════════════════════════
#  RSS ÇEKME (TTL: 3 saat)
# ══════════════════════════════════════════════════
@st.cache_data(ttl=10800, show_spinner=False)
def fetch_rss(max_per=18):
    items, seen = [], set()
    for key, info in SOURCES.items():
        try:
            feed = feedparser.parse(info["rss"])
            for e in feed.entries[:max_per]:
                title = normalize(e.get("title",""))
                url   = (e.get("link","") or "").strip()
                if not title or not url or url in seen or len(title) < 15: continue
                raw  = getattr(e,"published","") or getattr(e,"updated","") or ""
                desc = getattr(e,"summary","") or getattr(e,"description","") or ""
                if desc:
                    desc = BeautifulSoup(desc,"html.parser").get_text(" ",strip=True)
                    desc = normalize(desc)[:800]
                if len(desc) < 30 and "CVE" not in title: continue
                seen.add(url)
                full = f"{title} {desc}"
                cves = list(set(CVE_PAT.findall(full)))
                is_s = any(k in full.lower() for k in SEC_KW) or key in SECURITY_SOURCES
                items.append({
                    "title": title, "description": desc, "url": url,
                    "source": info["name"], "date": parse_dt(raw).strftime("%Y-%m-%d"),
                    "country": "Türkiye" if key in TR_SOURCES else "Global",
                    "cve_ids": ",".join(cves), "is_security": bool(is_s),
                })
            time.sleep(0.3)
        except: pass
    return items

# ══════════════════════════════════════════════════
#  NLP ANALİZ (RSS sonucu değişince yeniden çalışır)
# ══════════════════════════════════════════════════
@st.cache_data(ttl=10800, show_spinner=False)
def run_nlp(_items_hash, items, threshold=52.0):
    model, names, emb_kw, emb_sec, emb_neg = load_model()
    texts = [f"{i['title']} {i['description']}" for i in items]
    n_emb = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
    sim_kw  = util.cos_sim(n_emb, emb_kw)
    sim_sec = util.cos_sim(n_emb, emb_sec)
    sim_neg = util.cos_sim(n_emb, emb_neg)
    max_sim,_ = torch.max(torch.stack([sim_kw, sim_sec]), dim=0)

    result = []
    for idx, item in enumerate(items):
        it = dict(item)
        sc      = max_sim[idx]
        best_i  = torch.argmax(sc).item()
        raw_sim = sc[best_i].item()
        neg_sim = sim_neg[idx][0].item()
        sem_sc  = ((raw_sim+1)/2)*100
        best    = names[best_i]
        cd      = INCI_COMPANIES[best]

        if neg_sim >= raw_sim*0.70:
            it.update({"status":"trash","hybrid_score":0,"semantic_score":round(sem_sc,1),
                       "company":"","sector":"","color":"#444","icon":"","matched_kw":""})
        elif sem_sc < 56:
            it.update({"status":"unmatched","hybrid_score":round(sem_sc,1),"semantic_score":round(sem_sc,1),
                       "company":"","sector":"","color":"#444","icon":"","matched_kw":""})
        else:
            tl   = texts[idx].lower()
            hits = [k for k in cd["keywords"]
                    if (k in tl if " " in k else bool(re.search(rf"\b{re.escape(k)}\b", tl)))]
            kw_s = min(100.0, len(hits)*25.0)
            hyb  = round(sem_sc*0.75 + kw_s*0.25, 1)
            it.update({
                "status":         "matched" if hyb >= threshold else "unmatched",
                "company":        best, "sector": get_sector(best),
                "color":          cd["color"], "icon": cd["icon"],
                "matched_kw":     ", ".join(hits[:5]) if hits else "Semantik Uyum",
                "hybrid_score":   hyb, "semantic_score": round(sem_sc,1),
            })
        result.append(it)
    return result

# ══════════════════════════════════════════════════
#  STREAMLIT ARAYÜZÜ
# ══════════════════════════════════════════════════
st.set_page_config(
    page_title="İnci Holding | Teknoloji Bülteni",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

/* Arka plan */
.stApp { background: #0C0C0C; color: #E4DCD4; }
section[data-testid="stSidebar"] { background: #111111; border-right: 1px solid #222; }
section[data-testid="stSidebar"] > div { padding-top: 0; }

/* Butonlar */
.stButton > button {
    background: #8B1A1A; color: #FFF; border: none;
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600; letter-spacing: 0.8px;
    border-radius: 2px; padding: 8px 20px;
    transition: background .2s;
}
.stButton > button:hover { background: #A52020; border: none; }
.stButton > button:active { background: #6A1010; border: none; }

/* Selectbox & text input */
.stSelectbox > div > div { background: #1A1A1A; border-color: #2A2A2A; color: #E4DCD4; }
.stTextInput > div > div > input {
    background: #1A1A1A; border-color: #2A2A2A; color: #E4DCD4;
    font-family: 'IBM Plex Mono', monospace; font-size: 12px;
}

/* Metric */
[data-testid="metric-container"] {
    background: #141414; border: 1px solid #222;
    border-radius: 3px; padding: 12px 16px;
}
[data-testid="metric-container"] label { color: #666; font-size: 10px; letter-spacing: 1.5px; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace; font-size: 22px; color: #E4DCD4;
}

/* Divider */
hr { border-color: #1E1E1E; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #111; }
::-webkit-scrollbar-thumb { background: #8B1A1A; border-radius: 2px; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='padding:18px 16px 14px;border-bottom:1px solid #1E1E1E;margin-bottom:16px'>
      <div style='display:flex;align-items:center;gap:10px'>
        <div style='width:5px;height:26px;background:#8B1A1A;border-radius:1px;flex-shrink:0'></div>
        <div>
          <div style='font-size:14px;font-weight:700;letter-spacing:1.5px;color:#FFF'>İNCİ HOLDİNG</div>
          <div style='font-size:9px;color:#444;letter-spacing:2.5px;font-family:"IBM Plex Mono"'>STRATEJİK TEKNOLOJİ BÜLTENİ</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⟳  Bülteni Güncelle", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f"""
    <div style='font-size:10px;color:#555;font-family:"IBM Plex Mono";
         padding:6px 10px;background:#141414;border-radius:2px;
         border:1px solid #1E1E1E;margin:10px 0 18px;text-align:center'>
      Hafta {datetime.now().isocalendar()[1]} · {datetime.now().strftime("%d.%m.%Y")} · 3s cache
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='font-size:9px;color:#444;letter-spacing:2px;margin-bottom:8px;font-family:\"IBM Plex Mono\"'>GÖRÜNÜM</div>", unsafe_allow_html=True)
    tab = st.radio("", ["📋 Bülten", "🗂 Sektörler", "🔒 Siber Güvenlik", "🌍 Bülten Dışı"], label_visibility="collapsed")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:9px;color:#444;letter-spacing:2px;margin-bottom:8px;font-family:\"IBM Plex Mono\"'>SEKTÖR FİLTRESİ</div>", unsafe_allow_html=True)
    sel_sectors = []
    for sector, icon in SECTOR_ICONS.items():
        if st.checkbox(f"{icon} {sector}", key=f"sec_{sector}"):
            sel_sectors.append(sector)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:9px;color:#444;letter-spacing:2px;margin-bottom:8px;font-family:\"IBM Plex Mono\"'>ŞİRKET FİLTRESİ</div>", unsafe_allow_html=True)
    sel_companies = []
    for name, cd in INCI_COMPANIES.items():
        if st.checkbox(f"{cd['icon']} {name}", key=f"comp_{name}"):
            sel_companies.append(name)


# ══════════════════════════════════════════════════
#  VERİ YÜKLEME
# ══════════════════════════════════════════════════
with st.spinner("📡 RSS kaynakları okunuyor..."):
    raw_items = fetch_rss()

with st.spinner("🧠 NLP analizi yapılıyor..."):
    items_hash = hash(frozenset(i["url"] for i in raw_items))
    all_items  = run_nlp(items_hash, raw_items)

matched   = [i for i in all_items if i["status"] == "matched"]
unmatched = [i for i in all_items if i["status"] == "unmatched"]
trash     = [i for i in all_items if i["status"] == "trash"]
sec_items = [i for i in all_items if i["is_security"] or i["cve_ids"]]


# ══════════════════════════════════════════════════
#  TOOLBAR (arama + sıralama)
# ══════════════════════════════════════════════════
col_s, col_r, col_sp = st.columns([3, 2, 5])
with col_s:
    search = st.text_input("", placeholder="🔍  Arama...", label_visibility="collapsed")
with col_r:
    sort_by = st.selectbox("", ["Skora Göre", "Tarihe Göre", "Kaynağa Göre"], label_visibility="collapsed")


# ══════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════
avg_sc = round(sum(i["hybrid_score"] for i in matched) / max(len(matched),1), 1)
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("İNCELENEN",    len(all_items))
c2.metric("BÜLTENE GİREN", len(matched))
c3.metric("BÜLTEN DIŞI",  len(unmatched))
c4.metric("ÇÖPE ATILAN",  len(trash))
c5.metric("ORT. SKOR",    avg_sc)
c6.metric("GÜVENLİK",     len(sec_items))

st.markdown("<hr style='margin:8px 0 18px'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════
#  FİLTRELEME
# ══════════════════════════════════════════════════
def apply_filters(pool):
    if sel_sectors:
        pool = [i for i in pool if i.get("sector") in sel_sectors]
    if sel_companies:
        pool = [i for i in pool if i.get("company") in sel_companies]
    if search:
        q = search.lower()
        pool = [i for i in pool if
                q in (i.get("title","")).lower() or
                q in (i.get("description","")).lower() or
                q in (i.get("matched_kw","")).lower() or
                q in (i.get("source","")).lower()]
    if sort_by == "Skora Göre":   pool.sort(key=lambda x: x.get("hybrid_score",0), reverse=True)
    elif sort_by == "Tarihe Göre":pool.sort(key=lambda x: x.get("date",""), reverse=True)
    elif sort_by == "Kaynağa Göre":pool.sort(key=lambda x: x.get("source",""))
    return pool


# ══════════════════════════════════════════════════
#  KART RENDER
# ══════════════════════════════════════════════════
def conf_color(sc):
    if sc>=70: return "#27AE60","Çok Yüksek"
    if sc>=60: return "#F39C12","Yüksek"
    return "#E74C3C","Orta"

def render_card(item):
    col   = item.get("color","#555")
    sc    = item.get("hybrid_score",0)
    cc, cl = conf_color(sc)
    desc  = (item.get("description","") or "")[:260]
    if len(item.get("description","") or "") > 260: desc += "..."
    kws = "".join([
        f'<span style="background:#1A1A1A;border:1px solid #2A2A2A;color:#666;'
        f'border-radius:2px;padding:2px 7px;font-size:10px;font-family:IBM Plex Mono,monospace;'
        f'margin-right:4px">{k.strip()}</span>'
        for k in (item.get("matched_kw","") or "").split(",")[:4] if k.strip()
    ])
    sec_badge = ('<span style="background:#1A0808;color:#E74C3C;border:1px solid #5A1010;'
                 'border-radius:2px;padding:2px 7px;font-size:10px;margin-right:4px">🔒 Güvenlik</span>'
                 if item.get("is_security") else "")

    st.markdown(f"""
    <div style="background:#141414;border:1px solid #222;border-left:3px solid {col};
                border-radius:3px;padding:16px 18px;margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px">
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;line-height:1.45;margin-bottom:7px">
            <a href="{item['url']}" target="_blank"
               style="color:#E4DCD4;text-decoration:none">{item['title']}</a>
          </div>
          <div style="font-size:11px;color:#888;line-height:1.65;margin-bottom:10px">{desc}</div>
          <div>
            <span style="border:1px solid {col};color:{col};border-radius:2px;
                         padding:3px 8px;font-size:10px;font-weight:500;margin-right:5px;
                         background:color-mix(in srgb,{col} 12%,transparent)">
              {item.get('icon','')} {item.get('company','')}
            </span>
            <span style="background:#1C1C1C;color:#666;border:1px solid #222;
                         border-radius:2px;padding:3px 8px;font-size:10px;margin-right:5px">
              {item.get('sector','')}
            </span>
            {kws}{sec_badge}
          </div>
        </div>
        <div style="flex-shrink:0;text-align:right;min-width:80px">
          <div style="font-size:28px;font-weight:700;color:{cc};
                      font-family:'IBM Plex Mono',monospace;line-height:1">{int(sc)}</div>
          <div style="font-size:9px;color:#444;letter-spacing:1px;margin:2px 0">UYUM SKORU</div>
          <div style="height:3px;background:#2A2A2A;border-radius:2px;overflow:hidden;margin-top:3px">
            <div style="height:100%;width:{sc}%;background:{cc};border-radius:2px"></div>
          </div>
          <div style="font-size:10px;color:{cc};font-weight:600;margin-top:5px">{cl}</div>
        </div>
      </div>
      <div style="margin-top:10px;padding-top:8px;border-top:1px solid #1E1E1E;
                  display:flex;justify-content:space-between">
        <span style="font-size:10px;color:#3A3A3A">{item.get('source','')} · {item.get('country','')}</span>
        <span style="font-size:10px;color:#3A3A3A;font-family:'IBM Plex Mono',monospace">{item.get('date','')}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════
#  SEKMELER
# ══════════════════════════════════════════════════

# ── BÜLTEN ──
if tab == "📋 Bülten":
    pool = apply_filters(matched)
    st.markdown(f"<div style='font-size:10px;color:#555;font-family:IBM Plex Mono,monospace;margin-bottom:14px'>"
                f"{len(pool)} HABER GÖSTERİLİYOR</div>", unsafe_allow_html=True)
    if not pool:
        st.markdown("<div style='text-align:center;padding:60px;color:#333;font-size:13px'>◈ &nbsp; Filtreyle eşleşen haber bulunamadı.</div>", unsafe_allow_html=True)
    else:
        for item in pool[:50]:
            render_card(item)

# ── SEKTÖRLER ──
elif tab == "🗂 Sektörler":
    pool = apply_filters(matched)
    for sector, icon in SECTOR_ICONS.items():
        si = [i for i in pool if i.get("sector") == sector]
        if not si: continue
        col_h = INCI_COMPANIES[MACRO_SECTORS[sector][0]]["color"]
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
                    background:#141414;border-radius:3px;border-left:3px solid {col_h};
                    margin-bottom:10px">
          <span style="font-size:14px;font-weight:600;flex:1;color:#E4DCD4">{icon} {sector}</span>
          <span style="background:{col_h};color:#FFF;border-radius:10px;padding:2px 10px;
                       font-size:11px;font-family:'IBM Plex Mono',monospace;font-weight:600">{len(si)}</span>
        </div>""", unsafe_allow_html=True)

        rows_html = ""
        for idx, item in enumerate(si[:10], 1):
            sc   = item.get("hybrid_score", 0)
            cc,_ = conf_color(sc)
            title_s = (item["title"][:70]+"..." if len(item["title"])>70 else item["title"])
            rows_html += f"""<tr style="border-bottom:1px solid #141414">
              <td style="padding:7px 10px;color:#555">{idx}</td>
              <td style="padding:7px 10px"><a href="{item['url']}" target="_blank"
                  style="color:#888;text-decoration:none">{title_s}</a></td>
              <td style="padding:7px 10px;color:{INCI_COMPANIES.get(item.get('company',''),{}).get('color','#777')}">{item.get('icon','')} {item.get('company','')}</td>
              <td style="padding:7px 10px;color:#555">{item.get('source','')}</td>
              <td style="padding:7px 10px;font-family:'IBM Plex Mono',monospace;
                         font-weight:700;color:{cc}">{int(sc)}</td>
              <td style="padding:7px 10px;color:#444;font-family:'IBM Plex Mono',monospace">{item.get('date','')}</td>
            </tr>"""

        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;font-size:11px;margin-bottom:22px">
          <tr style="background:#1A1A1A">
            <th style="padding:7px 10px;text-align:left;color:#555;border-bottom:1px solid #222">#</th>
            <th style="padding:7px 10px;text-align:left;color:#555;border-bottom:1px solid #222">Başlık</th>
            <th style="padding:7px 10px;text-align:left;color:#555;border-bottom:1px solid #222">Şirket</th>
            <th style="padding:7px 10px;text-align:left;color:#555;border-bottom:1px solid #222">Kaynak</th>
            <th style="padding:7px 10px;text-align:left;color:#555;border-bottom:1px solid #222">Skor</th>
            <th style="padding:7px 10px;text-align:left;color:#555;border-bottom:1px solid #222">Tarih</th>
          </tr>
          {rows_html}
        </table>""", unsafe_allow_html=True)

# ── SİBER GÜVENLİK ──
elif tab == "🔒 Siber Güvenlik":
    if not sec_items:
        st.markdown("<div style='text-align:center;padding:60px;color:#333'>🔒 Bu taramada güvenlik haberi bulunamadı.</div>", unsafe_allow_html=True)
    else:
        cve_items   = [i for i in sec_items if i.get("cve_ids")]
        other_items = [i for i in sec_items if not i.get("cve_ids")]
        if cve_items:
            st.markdown("<div style='font-size:10px;color:#444;letter-spacing:2px;margin-bottom:10px;font-family:IBM Plex Mono,monospace'>CVE BİLDİRİMLERİ</div>", unsafe_allow_html=True)
            for item in cve_items[:8]:
                st.markdown(f"""
                <div style="background:#141414;border:1px solid #3A1010;border-left:3px solid #E74C3C;
                            border-radius:3px;padding:12px 16px;margin-bottom:8px">
                  <span style="background:#2A0808;color:#E74C3C;border:1px solid #5A1010;
                               border-radius:2px;padding:2px 8px;font-size:10px;
                               font-family:'IBM Plex Mono',monospace">{item.get('cve_ids','')[:40]}</span>
                  <div style="font-size:12px;font-weight:600;color:#E4DCD4;margin:6px 0 3px">
                    <a href="{item['url']}" target="_blank" style="color:#E4DCD4;text-decoration:none">{item['title']}</a>
                  </div>
                  <div style="font-size:10px;color:#444">{item['source']} · {item.get('date','')}</div>
                </div>""", unsafe_allow_html=True)
        if other_items:
            st.markdown("<div style='font-size:10px;color:#444;letter-spacing:2px;margin:16px 0 10px;font-family:IBM Plex Mono,monospace'>SİBER GÜVENLİK GELİŞMELERİ</div>", unsafe_allow_html=True)
            for item in other_items[:8]:
                st.markdown(f"""
                <div style="background:#141414;border:1px solid #2A1A3A;border-left:3px solid #8E44AD;
                            border-radius:3px;padding:12px 16px;margin-bottom:8px">
                  <div style="font-size:12px;font-weight:600;color:#E4DCD4;margin-bottom:3px">
                    <a href="{item['url']}" target="_blank" style="color:#E4DCD4;text-decoration:none">{item['title']}</a>
                  </div>
                  <div style="font-size:10px;color:#444">{item['source']} · {item.get('date','')}</div>
                </div>""", unsafe_allow_html=True)

# ── BÜLTEN DIŞI ──
elif tab == "🌍 Bülten Dışı":
    pool = sorted(unmatched, key=lambda x: x.get("semantic_score",0), reverse=True)
    if search:
        pool = [i for i in pool if search.lower() in i.get("title","").lower()]
    st.markdown(f"<div style='font-size:10px;color:#555;font-family:IBM Plex Mono,monospace;margin-bottom:14px'>"
                f"{len(pool)} TEMİZ HABER (SEKTÖRLE EŞLEŞMEDİ)</div>", unsafe_allow_html=True)
    if pool:
        rows = "".join([f"""<tr>
          <td style="padding:9px 10px"><a href="{i['url']}" target="_blank"
              style="color:#888;text-decoration:none;font-size:12px">{(i['title'][:90]+'...' if len(i['title'])>90 else i['title'])}</a></td>
          <td style="padding:9px 10px;color:#444;font-size:11px;white-space:nowrap">{i['source']}</td>
          <td style="padding:9px 10px;color:#444;font-size:11px;font-family:'IBM Plex Mono',monospace">{i.get('date','')}</td>
        </tr>""" for i in pool[:30]])
        st.markdown(f"""
        <div style="background:#141414;border:1px solid #1E1E1E;border-radius:3px;overflow:hidden">
        <table style="width:100%;border-collapse:collapse">
          <tr style="background:#1A1A1A">
            <th style="padding:8px 10px;text-align:left;color:#444;font-size:10px;border-bottom:1px solid #222">BAŞLIK</th>
            <th style="padding:8px 10px;text-align:left;color:#444;font-size:10px;border-bottom:1px solid #222">KAYNAK</th>
            <th style="padding:8px 10px;text-align:left;color:#444;font-size:10px;border-bottom:1px solid #222">TARİH</th>
          </tr>
          {rows}
        </table></div>""", unsafe_allow_html=True)
