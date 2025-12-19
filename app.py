import streamlit as st
import replicate
import os
import requests
import PIL.Image
import time
import random
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from moviepy.audio.fx.all import audio_loop 
import tempfile
import base64

# --- 0. 系統補丁 (System Patch) ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- 1. 頁面設定 (Page Config) ---
st.set_page_config(page_title="LUMIÈRE", page_icon="✨", layout="centered")

# --- 2. THE "CHANEL" CSS INJECTION (魔改核心) ---
# 這裡我們強行注入 CSS 來覆蓋 Streamlit 的預設樣式
st.markdown("""
    <style>
    /* 1. 引入高級字體 (Playfair Display for Headings, Lato for Body) */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Lato:wght@300;400;700&display=swap');

    /* 2. 全局變數 */
    :root {
        --bg-color: #FFFFFF;
        --text-main: #1D1D1D;
        --text-sub: #757575;
        --brand-black: #000000;
        --brand-gold: #C5A059;
        --border-color: #E5E5E5;
    }

    /* 3. 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* 4. 全局樣式重置 */
    .stApp {
        background-color: var(--bg-color);
        font-family: 'Lato', sans-serif;
        color: var(--text-main);
    }
    
    /* 5. 標題樣式 (Luxury Vibe) */
    h1 {
        font-family: 'Playfair Display', serif;
        font-weight: 500;
        font-size: 2.5rem !important;
        text-align: center;
        letter-spacing: 2px;
        color: var(--brand-black);
        margin-bottom: 0.5rem;
        margin-top: 1rem;
    }
    
    h2, h3 {
        font-family: 'Playfair Display', serif;
        font-weight: 400;
        text-align: center;
        color: var(--text-main);
    }

    p {
        font-weight: 300;
        line-height: 1.6;
        letter-spacing: 0.5px;
        color: var(--text-sub);
        text-align: center;
    }

    /* 6. 按鈕魔改 (鋼琴黑 + 銳角) */
    .stButton > button {
        background-color: var(--brand-black) !important;
        color: white !important;
        border: 1px solid var(--brand-black) !important;
        border-radius: 0px !important; /* 銳角 */
        padding: 16px 32px !important;
        font-family: 'Lato', sans-serif !important;
        text-transform: uppercase;
        font-size: 14px !important;
        letter-spacing: 2px !important;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: none !important;
    }
    
    .stButton > button:hover {
        background-color: white !important;
        color: var(--brand-black) !important;
        border: 1px solid var(--brand-black) !important;
    }

    /* 次級按鈕 (透明背景) */
    .secondary-button > button {
        background-color: transparent !important;
        color: var(--text-sub) !important;
        border: none !important;
        text-decoration: underline;
        text-transform: none;
        letter-spacing: 1px;
    }

    /* 7. 上傳區塊魔改 */
    [data-testid='stFileUploader'] {
        width: 100%;
        padding: 0;
    }
    [data-testid='stFileUploader'] section {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 0px;
        padding: 40px 20px;
    }
    /* 隱藏預設按鈕，只留 Drag & Drop */
    [data-testid='stFileUploader'] section > button { 
        display: none;
    }
    
    /* 8. 圖片容器 */
    .img-container {
        border: 1px solid #F0F0F0;
        padding: 10px;
        background: white;
        margin-bottom: 20px;
    }
    
    /* 9. Loading Bar 魔改 (變金色) */
    .stProgress > div > div > div > div {
        background-color: var(--brand-gold);
    }
    
    /* 10. Logo 區域 */
    .logo-area {
        text-align: center;
        margin-bottom: 40px;
        font-family: 'Playfair Display', serif;
        font-size: 20px;
        font-weight: bold;
        letter-spacing: 5px;
        border-bottom: 1px solid #EEE;
        padding-bottom: 20px;
    }

    </style>
""", unsafe_allow_html=True)

# --- 3. 語言包 (Copywriting) ---
TEXT = {
    'TC': {
        'brand': "LUMIÈRE",
        'title': "煥發・新春",
        'subtitle': "以 AI 科技，預見您蛇年的自信光采",
        'upload_title': "UPLOAD PORTRAIT",
        'upload_desc': "請上傳清晰正面照片<br><span style='font-size:12px; color:#999'>支援 JPG, PNG, WEBP</span>",
        'tips': "💡 建議：光線充足，避免遮擋臉部",
        'generating': "正在構建您的新春形象...",
        's2_title': "CONFIRM YOUR LOOK",
        's2_desc': "您的氣質獨一無二。是否以此製作短片？",
        'btn_retry': "重選照片",
        'btn_confirm': "確認並製作短片",
        's3_title': "CREATING VIDEO",
        's3_desc': "這就像一場護膚療程，需要一點時間 (約3分鐘)...",
        'trivia': ["🧧 正月買褲(富)，全年富足", "✨ 保持心情愉悅，運氣自然來", "💧 新春護膚重點：保濕與光澤"],
        's4_title': "YOUR MOMENT",
        's4_desc': "您的專屬祝福已準備好",
        'btn_share': "分享至 WhatsApp",
        'btn_download': "下載影片",
        'btn_home': "返回首頁"
    },
    'EN': {
        'brand': "LUMIÈRE",
        'title': "RADIANT YEAR",
        'subtitle': "Visualize your radiance this Year of the Snake",
        'upload_title': "UPLOAD PORTRAIT",
        'upload_desc': "Upload a clear front-facing photo<br><span style='font-size:12px; color:#999'>Supports JPG, PNG, WEBP</span>",
        'tips': "💡 Tip: Use well-lit photos for best results",
        'generating': "Sculpting your festive look...",
        's2_title': "CONFIRM LOOK",
        's2_desc': "Does this capture your aura?",
        'btn_retry': "RETAKE",
        'btn_confirm': "GENERATE VIDEO",
        's3_title': "CREATING VIDEO",
        's3_desc': "Like a beauty ritual, this takes a moment (approx 3 mins)...",
        'trivia': ["🧧 New trousers bring wealth", "✨ Joy brings luck", "💧 Hydration is key"],
        's4_title': "YOUR MOMENT",
        's4_desc': "Your exclusive video is ready",
        'btn_share': "SHARE ON WHATSAPP",
        'btn_download': "DOWNLOAD VIDEO",
        'btn_home': "RETURN HOME"
    }
}

# --- 4. 狀態管理 ---
if 'step' not in st.session_state: st.session_state.step = 1
if 'lang' not in st.session_state: st.session_state.lang = 'TC'
t = TEXT[st.session_state.lang]

# --- 5. 後端函數 (Backend Logic) ---
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

def generate_image_api(uploaded_file):
    uploaded_file.seek(0)
    prompt = "a CNY greeting photo of this woman, in 9:16 ratio, do not include any text / 中文字 in the image."
    input_args = {
        "prompt": prompt, "image_input": [uploaded_file], 
        "resolution": "2K", "aspect_ratio": "9:16", "output_format": "png", "safety_filter_level": "block_only_high"
    }
    output = replicate.run(MODEL_IMG_GEN, input=input_args)
    if hasattr(output, 'url'): return output.url
    elif isinstance(output, list): return str(output[0])
    return str(output)

def generate_video_api(image_url):
    input_args = {
        "image": image_url, "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution",
        "duration": 4, "resolution": "720p", "aspect_ratio": "9:16", "generate_audio": False 
    }
    return str(replicate.run(MODEL_VIDEO_GEN, input=input_args))

def download_file(url, local_filename):
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(local_filename, 'wb') as f: f.write(r.content)
            return local_filename
    except: return None

def resize_with_padding(clip, target_resolution=(1080, 1920)):
    target_w, target_h = target_resolution
    resized_clip = clip.resize(height=target_h)
    if resized_clip.w > target_w: resized_clip = resized_clip.resize(width=target_w)
    background = ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
    return CompositeVideoClip([background, resized_clip.set_position("center")])

def process_composite(veo_path):
    if not os.path.exists("intro.mp4") or not os.path.exists("outro.mp4"): return None
    try:
        clip_intro = resize_with_padding(VideoFileClip("intro.mp4"))
        clip_veo = resize_with_padding(VideoFileClip(veo_path))
        clip_outro = resize_with_padding(VideoFileClip("outro.mp4"))
        final_clip = concatenate_videoclips([clip_intro, clip_veo, clip_outro], method="compose")
        if os.path.exists("bgm.mp3"):
            bgm = AudioFileClip("bgm.mp3")
            if bgm.duration < final_clip.duration: bgm = audio_loop(bgm, duration=final_clip.duration)
            else: bgm = bgm.subclip(0, final_clip.duration)
            final_clip = final_clip.set_audio(bgm.volumex(0.6))
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        final_clip.write_videofile(tfile.name, codec="libx264", audio_codec="aac", fps=24, preset="medium", verbose=False, logger=None)
        return tfile.name
    except: return None

# --- 6. UI 構建 (UI Construction) ---

# Top Navigation (Logo + Lang)
c1, c2 = st.columns([8, 2])
with c1:
    st.markdown(f"<div class='logo-area'>{t['brand']}</div>", unsafe_allow_html=True)
with c2:
    if st.button("EN/繁", key="lang_switch"):
        st.session_state.lang = 'EN' if st.session_state.lang == 'TC' else 'TC'
        st.rerun()

# --- SCREEN 1: LANDING & UPLOAD ---
if st.session_state.step == 1:
    st.markdown(f"<h1>{t['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p>{t['subtitle']}</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown(f"<div style='text-align:center; margin-bottom:10px; font-weight:bold; letter-spacing:1px;'>{t['upload_title']}</div>", unsafe_allow_html=True)
    
    # Uploader
    uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'])
    st.markdown(f"<p style='font-size:13px; margin-top:-20px;'>{t['upload_desc']}</p>", unsafe_allow_html=True)
    
    st.markdown(f"<div style='background:#F9F9F9; padding:10px; text-align:center; font-size:12px; margin-top:20px; color:#888;'>{t['tips']}</div>", unsafe_allow_html=True)

    if uploaded_file:
        st.write("")
        if st.button("START EXPERIENCE"): # 統一用英文 Button 增加高級感
            with st.spinner(t['generating']):
                try:
                    url = generate_image_api(uploaded_file)
                    st.session_state['generated_img_url'] = url
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

# --- SCREEN 2: PREVIEW ---
elif st.session_state.step == 2:
    st.markdown(f"<h3>{t['s2_title']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p>{t['s2_desc']}</p>", unsafe_allow_html=True)
    
    if 'generated_img_url' in st.session_state:
        st.markdown(f"""
        <div class="img-container">
            <img src="{st.session_state['generated_img_url']}" style="width:100%; display:block;">
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        # 使用 CSS class secondary-button
        st.markdown('<div class="secondary-button">', unsafe_allow_html=True)
        if st.button(t['btn_retry']):
            st.session_state.step = 1
            del st.session_state['generated_img_url']
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        if st.button(t['btn_confirm']):
            st.session_state.step = 3
            st.rerun()

# --- SCREEN 3: LOADING ---
elif st.session_state.step == 3:
    st.markdown(f"<h3>{t['s3_title']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p>{t['s3_desc']}</p>", unsafe_allow_html=True)
    
    # 模擬進度條
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Trivia Carousel
    trivia_box = st.empty()
    
    # Simulation Loop
    for i in range(1, 101):
        progress_bar.progress(i)
        
        # 每 20% 換一次 Trivia
        if i % 20 == 0:
            trivia = random.choice(t['trivia'])
            trivia_box.markdown(f"<div style='text-align:center; padding:20px; color:#C5A059; font-style:italic;'>{trivia}</div>", unsafe_allow_html=True)
        
        time.sleep(0.05) # 模擬時間
        
    try:
        # Real API Call
        if 'generated_img_url' in st.session_state:
            veo_url = generate_video_api(st.session_state['generated_img_url'])
            local_veo = download_file(veo_url, "temp_veo.mp4")
            if local_veo:
                final_path = process_composite(local_veo)
                if final_path:
                    st.session_state['final_video_path'] = final_path
                    st.session_state.step = 4
                    st.rerun()
    except Exception as e:
        st.error("Error: " + str(e))
        if st.button("BACK"):
            st.session_state.step = 1
            st.rerun()

# --- SCREEN 4: RESULT ---
elif st.session_state.step == 4:
    st.markdown(f"<h3>{t['s4_title']}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p>{t['s4_desc']}</p>", unsafe_allow_html=True)
    
    if 'final_video_path' in st.session_state:
        st.video(st.session_state['final_video_path'])
    
    st.write("")
    
    # Share (WhatsApp Link)
    st.link_button(t['btn_share'], "https://wa.me/?text=Check%20out%20my%20Luxury%20CNY%20Video!%20✨")
    
    # Download
    with open(st.session_state['final_video_path'], "rb") as f:
        st.download_button(t['btn_download'], data=f, file_name="Lumiere_CNY.mp4", mime="video/mp4")
    
    st.write("")
    st.markdown('<div class="secondary-button">', unsafe_allow_html=True)
    if st.button(t['btn_home']):
        st.session_state.step = 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
