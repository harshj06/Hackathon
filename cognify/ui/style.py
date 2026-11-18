import html
import streamlit as st

BUDDY = '''<svg viewBox="0 0 240 240" role="img" aria-label="Buddy, a friendly purple learning companion" xmlns="http://www.w3.org/2000/svg"><ellipse cx="120" cy="214" rx="71" ry="12" fill="#DAD7F1"/><path d="M55 80 Q36 29 75 40 L92 68 M151 66 Q189 24 191 66 L181 92" fill="#8D7ADC"/><rect x="44" y="65" width="152" height="137" rx="58" fill="#7963CC"/><rect x="62" y="85" width="116" height="85" rx="36" fill="#F4F0FF"/><ellipse cx="96" cy="121" rx="8" ry="12" fill="#292245"/><ellipse cx="145" cy="121" rx="8" ry="12" fill="#292245"/><path d="M106 144 Q120 158 135 144" fill="none" stroke="#292245" stroke-width="5" stroke-linecap="round"/><circle cx="80" cy="141" r="8" fill="#FFCEC7"/><circle cx="160" cy="141" r="8" fill="#FFCEC7"/><path d="M43 140 Q10 123 25 102 M196 140 Q226 122 216 99" fill="none" stroke="#7963CC" stroke-width="17" stroke-linecap="round"/><path d="M88 196 L82 213 M153 196 L159 213" stroke="#7963CC" stroke-width="18" stroke-linecap="round"/><path d="m206 45 5 11 12 2-9 8 2 12-10-6-11 5 3-12-8-9 12-1z" fill="#F4BF65"/></svg>'''

def theme(font_size=17, contrast=False, reduce_motion=False, accent='#6554C0'):
    st.markdown(f'''<style>
    :root {{ --accent:{accent}; }}
    [data-testid="stToolbar"] {{ visibility:hidden; }}
    .stApp {{ background:{'#FFFFFF' if contrast else '#F7F8FC'}; color:#20253D; }}
    html,body,[class*="css"] {{ font-family:Inter,ui-sans-serif,system-ui,sans-serif; }}
    .stMainBlockContainer {{ max-width:1240px; padding-top:4rem; padding-bottom:4rem; }}
    p, .stMarkdown, label {{ font-size:{font_size}px !important; line-height:1.65; }}
    h1,h2,h3 {{ letter-spacing:-.035em; color:#20253D; }}
    h1 {{ font-size:clamp(2.4rem,4vw,3.7rem) !important; line-height:1.1 !important; }}
    [data-testid="stSidebar"] {{ background:#EEEDF6; border-right:1px solid #DEDBEC; }}
    [data-testid="stMetric"] {{ background:#fff; border:1px solid #DFE2EE; border-radius:18px; padding:18px; }}
    [data-testid="stMetricLabel"] {{ color:#4B526A; }}
    [data-testid="stMetricValue"] {{ color:#53429D; }}
    .stButton button,.stFormSubmitButton button {{ border-radius:12px; min-height:46px; font-weight:600; }}
    .stButton button:focus-visible, input:focus-visible {{ outline:3px solid #AE7900 !important; outline-offset:3px; }}
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {{ background:var(--accent); border-color:var(--accent); color:white; }}
    [data-testid="stVerticalBlockBorderWrapper"]>div {{ border-radius:18px !important; }}
    .eyebrow {{ color:#5C4B9B; text-transform:uppercase; letter-spacing:.16em; font-size:12px; font-weight:750; margin:0 0 18px; }}
    .hero {{ padding:34px; background:linear-gradient(120deg,#ECE7FF,#F4F5FF 66%,#E6F4EE); border:1px solid #DFD9F2; border-radius:28px; margin:12px 0 26px; }}
    .hero p {{ max-width:650px; color:#4B526A; }}
    .brand {{ font-size:25px; font-weight:800; letter-spacing:-1px; margin-bottom:8px; }}
    .brand span {{ color:#7963CC; }}
    .pill {{ display:inline-block; background:#E7F3EC; color:#245740; padding:5px 12px; border-radius:30px; font-size:12px; font-weight:650; }}
    .card {{ background:white; border:1px solid #DFE2EE; border-radius:18px; padding:24px; height:100%; margin-bottom:12px; }}
    .card h3 {{ margin-top:6px; font-size:21px; }}
    .muted {{ color:#596077; }}
    .buddy {{ width:min(100%,235px); margin:auto; }}
    .step {{ display:flex; gap:16px; align-items:center; padding:14px 0; border-bottom:1px solid #E4E6EF; }}
    .step strong {{ background:#EEE9FC; color:#5C4B9B; border-radius:50%; min-width:35px; height:35px; text-align:center; line-height:35px; }}
    {'* {animation:none !important; transition:none !important;}' if reduce_motion else '.card {animation:appear .3s ease;} @keyframes appear {from {opacity:.2;transform:translateY(3px)} to {opacity:1;transform:translateY(0)}}'}
    {'p,label,.muted,.hero p,.eyebrow {color:#161626 !important;} .card,.hero {border:2px solid #38314A !important;}' if contrast else ''}
    [data-testid="stSidebar"] [data-baseweb="radio"] {{ padding:7px 10px; border-radius:12px; margin-bottom:2px; }}
    [data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) {{ background:#fff; box-shadow:0 2px 8px #53439412; }}
    [data-testid="stSidebar"] [data-baseweb="radio"]:focus-within {{ outline:2px solid #6554C0; }}
    .stat {{ background:#fff; border:1px solid #E1DEEF; border-radius:18px; padding:16px 20px; margin:10px 0; }}
    .stat span {{ display:block; color:#5C6075; font-size:13px; }}
    .stat strong {{ display:block; color:#524296; font-size:27px; margin-top:5px; }}
    .mini-stat {{ background:#fff; border:1px solid #E1DEEF; border-radius:16px; padding:12px 16px; margin:8px 0 18px; }}
    .mini-stat span {{ display:block; color:#666B80; font-size:12px; text-transform:uppercase; letter-spacing:.08em; }}
    .mini-stat b {{ display:block; color:#524296; font-size:22px; margin-top:3px; }}
    .quest-banner {{ display:flex; justify-content:space-between; gap:20px; align-items:center; background:linear-gradient(120deg,#35275D,#6554C0 58%,#7C6AE0); color:#fff; border-radius:22px; padding:22px 26px; margin:10px 0 12px; box-shadow:0 12px 24px #5D4BAC22; }}
    .quest-banner strong {{ display:block; font-size:24px; letter-spacing:-.03em; }}
    .quest-banner p {{ margin:3px 0 0; color:#EEEAFE; font-size:14px !important; }}
    .quest-kicker {{ display:block; color:#CFC5FF; font-size:11px; font-weight:800; letter-spacing:.14em; margin-bottom:6px; }}
    .quest-reward {{ min-width:120px; text-align:center; background:#FFFFFF1A; border:1px solid #FFFFFF33; border-radius:16px; padding:12px; }}
    .quest-reward span {{ font-size:24px; color:#FFD477; }}
    .quest-reward b,.quest-reward small {{ display:block; }}
    .quest-reward small {{ color:#EEEAFE; font-size:11px; margin-top:2px; }}
    .section-label {{ color:#5C4B9B; text-transform:uppercase; letter-spacing:.12em; font-size:12px; font-weight:800; margin:10px 0 4px; }}
    .quest-card {{ min-height:92px; background:#fff; border:1px solid #DFE2EE; border-radius:17px 17px 0 0; padding:16px 18px 8px; }}
    .quest-card b {{ display:inline-block; color:#292545; font-size:17px; margin-left:10px; }}
    .quest-card p {{ margin:6px 0 0; color:#62677A; font-size:14px !important; }}
    .game-card {{ background:#fff; border:1px solid #DFE2EE; border-radius:18px; padding:18px; min-height:150px; margin:16px 0 0; box-shadow:0 6px 14px #37305D08; }}
    .game-card h3 {{ margin:12px 0 4px; font-size:18px; }}
    .game-card p {{ margin:0; color:#62677A; font-size:14px !important; line-height:1.45; }}
    .quest-icon {{ display:inline-grid; place-items:center; width:31px; height:31px; border-radius:10px; color:#fff; background:#7963CC; font-weight:800; }}
    .round-header {{ display:flex; justify-content:space-between; align-items:end; gap:16px; margin:26px 0 8px; }}
    .round-header h2 {{ margin:0; }}
    .round-count {{ color:#5C4B9B; background:#EEE9FC; padding:8px 12px; border-radius:30px; font-weight:700; font-size:13px; }}
    .question-number {{ color:#7562BA; font-size:11px; font-weight:800; letter-spacing:.14em; }}
    .result-card {{ background:linear-gradient(120deg,#EAF7F0,#F1EDFF); border:1px solid #CFE6D9; border-radius:22px; padding:24px; margin:22px 0 14px; }}
    .result-card h2 {{ margin:0 0 4px; }}
    .result-card p {{ margin:0; color:#4B526A; }}
    @media(max-width:640px) {{ .quest-banner {{ display:block; }} .quest-reward {{ margin-top:16px; }} .round-header {{ display:block; }} .round-count {{ display:inline-block; margin-top:8px; }} }}
    .trail {{ display:flex; align-items:center; gap:14px; padding:16px 8px; font-weight:600; color:#41425D; }}
    .trail span {{ display:grid; place-items:center; border:2px solid #CABFEA; border-radius:50%; min-width:38px; height:38px; color:#6554C0; background:#FFF; }}
    .playground {{ background:#ECE8FC; border:1px solid #DDD5F4; border-radius:22px; padding:28px; text-align:center; margin:16px 0; }}
    .playground strong {{ font-size:32px; color:#51408F; }}
    .dots {{ font-size:29px; color:#7360C2; margin-bottom:18px; overflow-wrap:anywhere; }}
    .dots span {{ color:#20253D; }}
    .fraction-grid {{ display:flex; justify-content:center; flex-wrap:wrap; gap:8px; margin-bottom:18px; }}
    .fraction-part {{ display:block; width:42px; height:55px; background:#FFF; border:2px solid #7562BA; border-radius:8px; }}
    .fraction-part.filled {{ background:#7562BA; }}
    [data-testid="stChatMessage"] {{ border:1px solid #E2DEEF; border-radius:20px; background:#fff; }}
    [data-testid="stText"] {{ white-space:pre-wrap; overflow-wrap:anywhere; font-family:inherit; }}
    @media(max-width:640px) {{ .stMainBlockContainer {{ padding:4rem 1rem 1rem; }} .hero {{ padding:22px; }} }}
    @media(prefers-reduced-motion:reduce) {{ * {{animation:none !important;transition:none !important;}} }}
    </style>''', unsafe_allow_html=True)

def brand():
    st.markdown('<div class="brand">cognify<span>✦</span></div>', unsafe_allow_html=True)

def hero(title, subtitle, eyebrow='YOUR NEXT DISCOVERY'):
    st.markdown(f'<div class="hero"><div class="eyebrow">{html.escape(eyebrow)}</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>', unsafe_allow_html=True)

def card(title, text, icon='✦'):
    st.markdown(f'<div class="card"><span class="pill">{html.escape(icon)}</span><h3>{html.escape(title)}</h3><p class="muted">{html.escape(text)}</p></div>', unsafe_allow_html=True)

def mascot():
    st.markdown('<div class="buddy">' + BUDDY + '</div>', unsafe_allow_html=True)
