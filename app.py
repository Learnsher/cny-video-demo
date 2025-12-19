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

# --- 0. 系統補丁 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- 1. 頁面設定 ---
st.set_page_config(page_title="LUMIÈRE", page_icon="✨", layout="wide") # 使用 Wide 方便我們用 CSS 控制中間的 Container

# --- 2. THE "PIXEL PERFECT" CSS (核心改動) ---
st.markdown("""
    <style>
    /* ========== 字體引入 ========== */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600&family=Manrope:wght@300;400;600&display=swap');

    /* ========== 全局重置 (CSS Reset) ========== */
    .stApp {
        background-color: #FFFFFF;
        font-family: 'Manrope', sans-serif;
    }
    
    /* 移除 Streamlit 預設的頂部和兩側空白 */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 480px; /* 強制模擬手機寬度 */
        margin: 0 auto;   /* 居中 */
        background-color: #FFFFFF;
        min-height: 100vh;
        box-shadow: 0 0 20px rgba(0,0,0,0.05); /* 增加一點陰影讓它像個 App */
    }
    
    /* 隱藏 Header/Footer/Menu */
    header, footer, #MainMenu {visibility: hidden;}
    
    /* ========== UI 元件樣式 ========== */
    
    /* 1. 標題區域 (HTML 渲染) */
    .header-section {
        text-align: center;
        margin-bottom: 2rem;
        padding: 0 20px;
    }
    .brand-title {
        font-family: 'Playfair Display', serif;
        font-size: 36px;
        color: #000;
        margin-bottom: 10px;
        letter-spacing: 1px;
    }
    .sub-title {
        font-size: 14px;
        color: #666;
        line-height: 1.6;
        font-weight: 300;
    }

    /* 2. 上傳器 (深度魔改) */
    [data-testid='stFileUploader'] {
        padding: 0 20px;
    }
    [data-testid='stFileUploader'] section {
        background-color: #F4F4F4; /* 淺灰底色 */
        border: none;
        border-radius: 0;
        padding: 60px 0; /* 增加高度 */
    }
    /* 隱藏預設按鈕，只留拖曳區 */
    [data-testid='stFileUploader'] button {display: none;}
    
    /* 3. 按鈕 (Pixel Perfect Alignment) */
    /* 強制按鈕填滿 Column */
    div.stButton > button {
        width: 100%;
        border-radius: 0px !important;
        padding: 16px 0 !important;
        font-family: 'Manrope', sans-serif;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-size: 14px;
        border: 1px solid #000;
        transition: all 0.2s;
    }
    
    /* 黑色實心按鈕 (Primary) */
    .primary-btn div.stButton > button {
        background-color: #000 !important;
        color: #FFF !important;
    }
    .primary-btn div.stButton > button:hover {
        background-color: #333 !important;
    }

    /* 白色空心按鈕 (Secondary) */
    .secondary-btn div.stButton > button {
        background-color: #FFF !important;
        color: #000 !important;
    }
    .secondary-btn div.stButton > button:hover {
        background-color: #F4F4F4 !important;
    }
    
    /* 底部按鈕容器 (固定在底部或緊貼內容) */
    .action-area {
        padding: 20px;
        margin-top: 20px;
    }

    /* 4. 圖片容器 (HTML) */
    .image-wrapper {
        width: 100%;
        aspect-ratio: 9/16;
        background-color: #EEE;
        overflow: hidden;
        position: relative;
    }
    .image-wrapper img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    /* 5. 載入動畫文字 */
    .loading-text {
        text-align: center;
        margin-top: 20px;
        font-family: 'Playfair Display', serif;
        font-size: 18px;
        color: #C5A059;
    }
    
    /* 6. 進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #C5A059;
    }

    </style>
""", unsafe_allow_html=True)

# --- 3. 語言包 ---
TEXT = {
    'TC': {
        'brand': "AI 煥發·新春",
        'sub': "為您準備個人化短片<br>送上溫馨祝福",
        'upload_hint': "請上傳清晰正面照片",
        'tips': "✓ 清晰樣貌   ✕ 帶口罩   ✕ 多人合照",
        's2_title': "您的新年形象真美！",
        's2_sub': "用此繼續生成祝賀短片？",
        'btn_retry': "重新開始",
        'btn_confirm': "生成短片",
        's3_title': "短片生成中...",
        's3_sub': "約需時3分鐘，請稍等",
        'trivia': ["🧧 正月買褲(富)，全年富足", "✨ 保持心情愉悅，運氣自然來", "💧 新春護膚重點：保濕與光澤"],
        's4_title': "祝賀短片準備好啦！",
        's4_sub': "立即分享給親友",
        'btn_share': "分享祝福短片",
        'btn_dl': "下載珍藏",
        'btn_home': "返回首頁"
    }
}
t = TEXT['TC'] # 簡化 Demo，暫用單一語言，可自行擴充

# --- 4. 後端函數 ---
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

# --- 5. 狀態管理 ---
if 'step' not in st.session_state: st.session_state.step = 1

# --- 6. 頁面渲染 (HTML-First Approach) ---

# ====== SCREEN 1: UPLOAD ======
if st.session_state.step == 1:
    
    # 1. 頂部標題 (HTML)
    st.markdown(f"""
        <div class="header-section" style="padding-top: 40px;">
            <div class="brand-title">{t['brand']}</div>
            <div class="sub-title">{t['sub']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. 上傳器 (Streamlit Widget - CSS 已隱藏按鈕，變成灰色區塊)
    # 為了模擬 HTML 結構，我們直接放 Widget，CSS 會負責排版
    uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'])
    
    # 3. 提示文字 (HTML)
    st.markdown(f"""
        <div style="text-align: center; margin-top: 15px;">
            <div style="font-weight: 500; font-size: 14px;">{t['upload_hint']}</div>
            <div style="color: #999; font-size: 12px; margin-top: 5px;">{t['tips']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 4. 底部裝飾 (模擬 Wireframe 的圓圈 Step)
    st.markdown("""
        <div style="display: flex; justify-content: center; margin-top: 50px; opacity: 0.5;">
             <span style="margin: 0 10px; font-size: 12px;">● 上傳</span>
             <span style="margin: 0 10px; font-size: 12px;">○ 預覽</span>
             <span style="margin: 0 10px; font-size: 12px;">○ 生成</span>
        </div>
    """, unsafe_allow_html=True)

    # Logic
    if uploaded_file:
        # 當偵測到檔案時，自動觸發生成 (模擬流暢體驗)
        # 這裡我們不放 Button，直接跳轉，讓 UX 更順
        with st.spinner("Processing..."):
            try:
                url = generate_image_api(uploaded_file)
                st.session_state['generated_img_url'] = url
                st.session_state.step = 2
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ====== SCREEN 2: PREVIEW ======
elif st.session_state.step == 2:
    
    # 標題
    st.markdown(f"""
        <div class="header-section" style="padding-top: 20px;">
            <div style="font-family: 'Playfair Display'; font-size: 24px; margin-bottom: 5px;">{t['s2_title']}</div>
            <div class="sub-title">{t['s2_sub']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 圖片預覽 (HTML 容器，確保 9:16)
    if 'generated_img_url' in st.session_state:
        st.markdown(f"""
            <div style="padding: 0 20px;">
                <div class="image-wrapper">
                    <img src="{st.session_state['generated_img_url']}">
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 底部按鈕區 (使用 Columns + CSS Class 實現對齊)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True) # Spacer
    
    col1, col2 = st.columns([1, 1], gap="small")
    
    with col1:
        # 左邊：白色按鈕 (Secondary)
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button(t['btn_retry']):
            st.session_state.step = 1
            del st.session_state['generated_img_url']
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        # 右邊：黑色按鈕 (Primary)
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button(t['btn_confirm']):
            st.session_state.step = 3
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ====== SCREEN 3: LOADING ======
elif st.session_state.step == 3:
    
    st.markdown(f"""
        <div style="text-align: center; padding-top: 100px;">
            <div style="font-family: 'Playfair Display'; font-size: 24px; margin-bottom: 10px;">{t['s3_title']}</div>
            <div style="color: #666; font-size: 14px;">{t['s3_sub']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 自定義 Toggle 樣式 UI (純展示)
    st.markdown("""
        <div style="display: flex; justify-content: center; align-items: center; margin-top: 30px; background: #FAFAFA; padding: 10px; margin-left: 40px; margin-right: 40px;">
            <span style="font-size: 14px; margin-right: 10px;">完成時通知我</span>
            <div style="width: 40px; height: 20px; background: #DDD; border-radius: 10px; position: relative;">
                <div style="width: 18px; height: 18px; background: #FFF; border-radius: 50%; position: absolute; top: 1px; left: 1px;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    # Progress Logic
    progress_bar = st.progress(0)
    trivia_placeholder = st.empty()
    
    for i in range(1, 101):
        progress_bar.progress(i)
        if i % 25 == 0:
            trivia = random.choice(t['trivia'])
            trivia_placeholder.markdown(f"<div class='loading-text'>{trivia}</div>", unsafe_allow_html=True)
        time.sleep(0.04) # 3-4秒動畫
    
    # Execute API
    try:
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
        st.error(str(e))
        if st.button("Back"):
            st.session_state.step = 1
            st.rerun()

# ====== SCREEN 4: RESULT ======
elif st.session_state.step == 4:
    
    st.markdown(f"""
        <div class="header-section" style="padding-top: 20px;">
            <div style="font-family: 'Playfair Display'; font-size: 24px; margin-bottom: 5px;">{t['s4_title']}</div>
            <div class="sub-title">{t['s4_sub']}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Video 容器
    if 'final_video_path' in st.session_state:
        # 使用 HTML Video Tag 確保無邊框
        # 注意：Streamlit 有時無法直接讀取 local mp4 進入 HTML tag，所以我們用 base64 encode
        video_file = open(st.session_state['final_video_path'], 'rb')
        video_bytes = video_file.read()
        video_b64 = base64.b64encode(video_bytes).decode()
        
        st.markdown(f"""
            <div style="padding: 0 20px;">
                <div class="image-wrapper">
                    <video autoplay muted controls loop style="width: 100%; height: 100%; object-fit: cover;">
                        <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                    </video>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Action Buttons
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # 黑色按鈕 (Share)
    st.markdown('<div class="primary-btn" style="padding: 0 20px;">', unsafe_allow_html=True)
    st.link_button(t['btn_share'], "https://wa.me/?text=My%20CNY%20Video!")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 黑色按鈕 (Download) - 需要用 st.download_button 但我們要用 CSS 偽裝它
    st.markdown('<div class="primary-btn" style="padding: 10px 20px 0 20px;">', unsafe_allow_html=True)
    with open(st.session_state['final_video_path'], "rb") as f:
        st.download_button(t['btn_dl'], data=f, file_name="CNY_Video.mp4", mime="video/mp4")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 底部返回
    st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="secondary-btn" style="padding: 0 20px;">', unsafe_allow_html=True)
    if st.button(t['btn_home']):
        st.session_state.step = 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
