import streamlit as st
import replicate
import os
import requests
import PIL.Image
import time
import random
import base64

# --- 0. 系統補丁 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from moviepy.audio.fx.all import audio_loop 
import tempfile

# --- 1. 頁面設定與高級 CSS ---
st.set_page_config(page_title="LUMIÈRE - New Year Rejuvenation", page_icon="✨", layout="centered")

# --- CUSTOM CSS (復刻 Wireframe 風格) ---
st.markdown("""
    <style>
    /* 全局字體 */
    .stApp {
        background-color: #FFFFFF;
        color: #1A1A1A;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 隱藏 Header/Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 標題樣式 - 醫美級襯線體 */
    h1 {
        color: #1A1A1A; /* 黑色標題 */
        font-weight: 300 !important;
        text-align: center;
        letter-spacing: 2px;
        font-size: 28px !important;
        margin-bottom: 5px !important;
    }
    
    /* 副標題 */
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 14px;
        letter-spacing: 1px;
        margin-bottom: 30px;
        font-weight: 300;
    }

    /* === 按鈕樣式 (重點) === */
    
    /* 主按鈕 (黑色底 + 金色字) - 對應 Wireframe 的黑色 Button */
    .stButton>button {
        background-color: #000000 !important;
        color: #D4AF37 !important; /* 香檳金字 */
        border: 1px solid #000000;
        border-radius: 0px; /* 方形銳角 */
        padding: 15px 24px;
        font-size: 16px;
        font-weight: 400;
        letter-spacing: 1.5px;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #333333 !important;
        transform: translateY(-1px);
    }

    /* 次級按鈕 (白色底 + 黑色字) - 對應 Wireframe 的白色 Button */
    .secondary-btn button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
    }

    /* === 上傳區樣式 === */
    .upload-container {
        background-color: #F0F0F0; /* 淺灰底 */
        border: none;
        padding: 40px 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* 隱藏 Streamlit 預設 Uploader 的醜框，改成透明覆蓋 */
    .stFileUploader > div > div {
        background-color: #F5F5F5;
        border: 1px dashed #D4AF37;
        padding: 20px;
    }

    /* 底部步驟條樣式 */
    .step-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 40px;
        margin-bottom: 20px;
    }
    .step-circle {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: #E0E0E0;
        color: #FFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        margin: 0 10px;
        flex-direction: column;
    }
    .step-active {
        background-color: #D4AF37; /* 金色激活 */
    }
    .step-arrow {
        color: #CCC;
        font-size: 20px;
    }
    .step-label {
        font-size: 10px;
        margin-top: 4px;
        color: #666;
    }
    
    /* 提示與檢查項 */
    .check-item {
        font-size: 12px;
        color: #666;
        margin-right: 15px;
    }
    
    /* Toggle Switch 樣式微調 */
    .stToggle {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #F9F9F9;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 狀態與語言管理 ---

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'lang' not in st.session_state:
    st.session_state.lang = 'TC' 

# 語言包
TEXT = {
    'TC': {
        'title': "AI 煥發 · 新春",
        'subtitle': "為您準備個人化短片，送上溫馨祝福",
        'upload_ph': "請按此上傳相片",
        'check_1': "✓ 清晰樣貌照片",
        'check_2': "✗ 帶口罩",
        'check_3': "✗ 多人合照",
        'steps': ["上傳相片", "查看新春形象", "發送祝福短片"],
        's2_title': "您的新春形象真美！",
        's2_sub': "用此繼續生成祝賀短片？",
        'btn_restart': "重新開始",
        'btn_generate': "生成短片",
        's3_title': "短片生成中...",
        's3_sub': "約需時 3 分鐘，請稍等",
        'notify': "完成時通知我",
        'trivia_title': "新春小趣聞",
        'trivia_1': "正月唔買鞋(唉)，但可以買褲(富)！",
        'trivia_2': "利是要派到正月十五，唔好咁快收手！",
        'trivia_3': "初一洗頭會洗走財氣，忍多日啦！",
        's4_title': "祝賀短片已經準備好啦！",
        's4_sub': "立即分享出去啦<br>您亦可於收件匣隨時查看",
        'btn_share': "分享祝福短片",
        'back_home': "返回首頁",
    },
    'EN': {
        'title': "AI Rejuvenation · CNY",
        'subtitle': "Personalized video greeting for your loved ones",
        'upload_ph': "Tap to upload photo",
        'check_1': "✓ Clear Face",
        'check_2': "✗ No Mask",
        'check_3': "✗ Solo Shot",
        'steps': ["Upload", "Preview", "Share"],
        's2_title': "You look radiant!",
        's2_sub': "Generate video with this look?",
        'btn_restart': "Start Over",
        'btn_generate': "Create Video",
        's3_title': "Generating Video...",
        's3_sub': "Takes about 3 mins, please wait",
        'notify': "Notify when done",
        'trivia_title': "CNY Fun Fact",
        'trivia_1': "Buy pants (wealth), not shoes (sigh)!",
        'trivia_2': "Give red packets until the 15th day!",
        'trivia_3': "Don't wash hair on Day 1 (keeps luck)!",
        's4_title': "Your Video is Ready!",
        's4_sub': "Share it now<br>Check inbox anytime",
        'btn_share': "Share Video",
        'back_home': "Back to Home",
    }
}

t = TEXT[st.session_state.lang]

# --- 3. 核心邏輯 (API) ---
# (為了節省篇幅，這裡引用之前的邏輯，但在實際部署時請保留 v4.0 的 generate_image_api, generate_video_api 等函數)
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

def generate_image_api(uploaded_file):
    uploaded_file.seek(0)
    prompt = "a CNY greeting photo of this woman, in 9:16 ratio, do not include any text / 中文字 in the image."
    input_args = {"prompt": prompt, "image_input": [uploaded_file], "resolution": "2K", "aspect_ratio": "9:16", "output_format": "png", "safety_filter_level": "block_only_high"}
    output = replicate.run(MODEL_IMG_GEN, input=input_args)
    if hasattr(output, 'url'): return output.url
    elif isinstance(output, list): return str(output[0])
    return str(output)

def generate_video_api(image_url):
    input_args = {"image": image_url, "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution", "duration": 4, "resolution": "720p", "aspect_ratio": "9:16", "generate_audio": False}
    output = replicate.run(MODEL_VIDEO_GEN, input=input_args)
    return str(output)

def download_file(url, local_filename):
    try:
        r = requests.get(url)
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

# --- 4. UI 流程 ---

# Language Switch (Top Right)
col_head, col_lang = st.columns([8, 2])
with col_lang:
    # 簡單的文字鏈接風格
    lang_label = "EN" if st.session_state.lang == 'TC' else '中文'
    if st.button(lang_label, key="lang_switch"):
        st.session_state.lang = 'EN' if st.session_state.lang == 'TC' else 'TC'
        st.rerun()

# --- SCREEN 1: UPLOAD (Wireframe 1) ---
if st.session_state.step == 1:
    
    st.markdown(f"<h1>{t['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>{t['subtitle']}</div>", unsafe_allow_html=True)
    
    # 模擬 Wireframe 的灰色上傳區
    st.markdown("<br>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(t['upload_ph'], type=['jpg', 'png', 'jpeg'])
    
    # 檢查項 (Checkmarks)
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<span class='check-item'>{t['check_1']}</span>", unsafe_allow_html=True)
    c2.markdown(f"<span class='check-item'>{t['check_2']}</span>", unsafe_allow_html=True)
    c3.markdown(f"<span class='check-item'>{t['check_3']}</span>", unsafe_allow_html=True)

    # 底部 3 步圓形進度條 (Custom HTML)
    st.markdown(f"""
        <div class="step-container">
            <div class="step-circle step-active">icon<span class="step-label">{t['steps'][0]}</span></div>
            <div class="step-arrow">▶</div>
            <div class="step-circle">icon<span class="step-label">{t['steps'][1]}</span></div>
            <div class="step-arrow">▶</div>
            <div class="step-circle">icon<span class="step-label">{t['steps'][2]}</span></div>
        </div>
    """, unsafe_allow_html=True)
    
    # Trigger logic
    if uploaded_file:
        with st.spinner("Analyzing..."):
            try:
                url = generate_image_api(uploaded_file)
                st.session_state['generated_img_url'] = url
                st.session_state.step = 2
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- SCREEN 2: CONFIRMATION (Wireframe 2) ---
elif st.session_state.step == 2:
    
    st.markdown(f"<h1>{t['s2_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>{t['s2_sub']}</div>", unsafe_allow_html=True)
    
    # 圖片預覽 (無邊框，全寬)
    if 'generated_img_url' in st.session_state:
        st.image(st.session_state['generated_img_url'], use_column_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 兩個按鈕 (White vs Black)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button(t['btn_restart']):
            st.session_state.step = 1
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        if st.button(t['btn_generate']):
            st.session_state.step = 3
            st.rerun()

# --- SCREEN 3: GENERATING (Wireframe 3) ---
elif st.session_state.step == 3:
    
    if 'final_video_path' not in st.session_state:
        # Title
        st.markdown(f"<h1>{t['s3_title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtitle'>{t['s3_sub']}</div>", unsafe_allow_html=True)
        
        # Toggle Switch (Visual Only)
        st.markdown("<br>", unsafe_allow_html=True)
        st.toggle(t['notify'], value=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Trivia Carousel (趣聞輪播)
        trivia_placeholder = st.empty()
        trivias = [t['trivia_1'], t['trivia_2'], t['trivia_3']]
        
        # 模擬 3 個循環 (每個 4-5 秒)
        for i in range(3): 
            with trivia_placeholder.container():
                # Icon (模擬 Wireframe 的圓圈 icon)
                st.markdown("""
                    <div style="text-align: center;">
                        <div style="width: 80px; height: 80px; background: #E0E0E0; border-radius: 50%; margin: 0 auto; display: flex; align-items: center; justify-content: center; color: #888;">
                            icon
                        </div>
                        <p style="margin-top: 15px; font-weight: 500;">""" + t['trivia_title'] + """</p>
                        <p style="color: #666;">""" + trivias[i] + """</p>
                    </div>
                """, unsafe_allow_html=True)
            time.sleep(4)
        
        # 執行生成
        try:
            veo_url = generate_video_api(st.session_state['generated_img_url'])
            local_veo = download_file(veo_url, "temp_veo.mp4")
            if local_veo:
                final_path = process_composite(local_veo)
                if final_path:
                    st.session_state['final_video_path'] = final_path
                    st.rerun()
        except:
             st.error("Error generating video")
             if st.button("Back"): st.session_state.step = 1; st.rerun()

    else:
        # --- SCREEN 4: RESULT (Wireframe 4) ---
        st.markdown(f"<h1>{t['s4_title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtitle'>{t['s4_sub']}</div>", unsafe_allow_html=True)
        
        # Video
        st.video(st.session_state['final_video_path'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Black Share Button (WhatsApp Link)
        wa_link = "https://wa.me/?text=Check%20out%20my%20CNY%20video!"
        st.link_button(t['btn_share'], wa_link, use_container_width=True)
        
        # Back Link
        st.markdown(f"""
            <div style="text-align: center; margin-top: 20px;">
                <a href="#" target="_self" style="color: #666; text-decoration: underline; font-size: 14px;">{t['back_home']}</a>
            </div>
        """, unsafe_allow_html=True)
        
        # 重置邏輯 (配合 Back Link 的功能)
        if st.button("Restart (Debug)", key="restart_hidden"): # 隱藏按鈕方便測試
             del st.session_state['final_video_path']
             st.session_state.step = 1
             st.rerun()
