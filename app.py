import streamlit as st
import replicate
import os
import requests
import PIL.Image
import time
import random

# --- 0. 系統補丁 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from moviepy.audio.fx.all import audio_loop 
import tempfile

# --- 1. 頁面設定與 CSS ---
st.set_page_config(page_title="LUMIÈRE - New Year Rejuvenation", page_icon="✨", layout="centered")

# --- CUSTOM CSS FOR LUXURY LOOK ---
st.markdown("""
    <style>
    /* 全局字體與背景 */
    .stApp {
        background-color: #FAFAFA; /* 高級灰白底 */
        color: #4A4A4A;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 隱藏 Streamlit 默認 Header/Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 標題樣式 - 勃艮第紅 */
    h1, h2, h3 {
        color: #800020 !important; 
        font-weight: 300 !important;
        text-align: center;
        letter-spacing: 1px;
    }
    
    /* 高級按鈕 - 香檳金漸變 */
    .stButton>button {
        background: linear-gradient(135deg, #D4AF37 0%, #C5A028 100%);
        color: white !important;
        border: none;
        border-radius: 0px; /* 銳利邊角更顯時尚 */
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 500;
        letter-spacing: 1px;
        width: 100%;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #E5C158 0%, #D4AF37 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 8px rgba(0,0,0,0.15);
    }

    /* 次級按鈕 (重試) - 極簡白金 */
    .secondary-btn button {
        background: transparent !important;
        border: 1px solid #D4AF37 !important;
        color: #D4AF37 !important;
        box-shadow: none !important;
    }

    /* 上傳區塊優化 */
    .stFileUploader {
        padding: 20px;
        border: 1px dashed #D4AF37;
        background-color: #FFFFFF;
        text-align: center;
    }
    
    /* 進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #D4AF37;
    }
    
    /* 卡片式容器 */
    .css-1y4p8pa {
        padding: 2rem;
        border-radius: 10px;
        background: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 狀態與語言管理 (State Management) ---

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'lang' not in st.session_state:
    st.session_state.lang = 'TC' # Default Traditional Chinese

# 語言包 (Copywriting)
TEXT = {
    'TC': {
        'title': "LUMIÈRE 煥發·新春",
        'subtitle': "以 AI 科技，預見您蛇年的自信光采",
        'upload_label': "上傳您的個人寫真",
        'upload_hint': "建議使用光線充足、輪廓清晰的正面照片，展現最真實的自信美。",
        'tip_title': "✧ 專業美學建議",
        'tip_content': "光影是輪廓的靈魂。請避免背光或過度遮擋臉部，讓 AI 捕捉您肌膚的細膩質感。",
        'generating_img': "正在為您定制專屬賀年形象...",
        'confirm_title': "確認您的新春形象",
        'confirm_desc': "這張照片捕捉了您的獨特氣質。是否以此製作視頻？",
        'btn_retry': "↻ 重新調整",
        'btn_confirm': "✧ 確認並製作視頻",
        'video_loading_title': "正在雕琢您的新春時刻...",
        'video_tips': [
            "💧 水潤光感：新春護膚重點在於深層補水，讓妝容更貼服持久。",
            "✨ 緊緻輪廓：定期進行膠原激活療程，讓下顎線條在鏡頭前更迷人。",
            "🌙 細胞修復：優質睡眠是最好的美容液，助您在新年煥發自然光采。",
            "👁️ 明眸亮采：眼周肌膚最易顯露疲態，適當熱敷可提升眼神魅力。",
            "🛡️ 全天候防護：冬日紫外線不容忽視，防曬是抗衰老的關鍵一步。"
        ],
        'result_title': "您的專屬新春時刻",
        'share_whatsapp': "分享至 WhatsApp",
        'download': "下載珍藏",
        'restart': "為家人製作",
        'error_upload': "請先上傳照片",
    },
    'EN': {
        'title': "LUMIÈRE Rejuvenation",
        'subtitle': "Visualize your radiance this Year of the Snake with AI.",
        'upload_label': "Upload Your Portrait",
        'upload_hint': "Please use a well-lit, clear front-facing photo to showcase your authentic beauty.",
        'tip_title': "✧ Aesthetic Advice",
        'tip_content': "Lighting is the soul of contour. Avoid backlighting to allow AI to capture your skin texture.",
        'generating_img': "Tailoring your festive look...",
        'confirm_title': "Confirm Your Look",
        'confirm_desc': "This image captures your unique aura. Proceed to video creation?",
        'btn_retry': "↻ Retake",
        'btn_confirm': "✧ Proceed",
        'video_loading_title': "Sculpting your moment...",
        'video_tips': [
            "💧 Hydration: The key to a flawless festive look is deep hydration.",
            "✨ Contour: Collagen treatments define your jawline for camera-ready confidence.",
            "🌙 Repair: Quality sleep is the best serum for natural festive radiance.",
            "👁️ Bright Eyes: Revitalize eye contours to enhance your captivating gaze.",
            "🛡️ Protection: Winter UV protection is the essential step for anti-aging."
        ],
        'result_title': "Your Exclusive Moment",
        'share_whatsapp': "Share on WhatsApp",
        'download': "Download",
        'restart': "Create Another",
        'error_upload': "Please upload a photo first.",
    }
}

t = TEXT[st.session_state.lang]

# --- 3. 核心邏輯 (Backend Functions) ---

if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]

MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

def generate_image_api(uploaded_file):
    uploaded_file.seek(0)
    # 這裡使用了您指定的 Prompt，並且隱藏不顯示給用戶
    prompt = "a CNY greeting photo of this woman, in 9:16 ratio, do not include any text / 中文字 in the image."
    
    input_args = {
        "prompt": prompt,
        "image_input": [uploaded_file], 
        "resolution": "2K",
        "aspect_ratio": "9:16",
        "output_format": "png",
        "safety_filter_level": "block_only_high"
    }
    output = replicate.run(MODEL_IMG_GEN, input=input_args)
    if hasattr(output, 'url'): return output.url
    elif isinstance(output, list): return str(output[0])
    return str(output)

def generate_video_api(image_url):
    input_args = {
        "image": image_url,
        "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution, smooth motion",
        "duration": 4, # API requires 4, 6, or 8
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": False 
    }
    output = replicate.run(MODEL_VIDEO_GEN, input=input_args)
    return str(output)

# 下載與合成 (保留 v3.2 的穩健邏輯)
def download_file(url, local_filename):
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(local_filename, 'wb') as f:
                f.write(r.content)
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
    if not os.path.exists(veo_path) or os.path.getsize(veo_path) < 1000: return None
    
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

# --- 4. UI 流程 (Single Page Application Flow) ---

# Top Navigation (Language Switch)
col_logo, col_lang = st.columns([8, 2])
with col_lang:
    lang_choice = st.radio("Language", ["TC", "EN"], horizontal=True, label_visibility="collapsed")
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

t = TEXT[st.session_state.lang] # Refresh text

st.markdown(f"<h1>{t['title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #888; margin-bottom: 30px;'>{t['subtitle']}</p>", unsafe_allow_html=True)

# ---------------- SCREEN 1: UPLOAD ----------------
if st.session_state.step == 1:
    
    # 視覺化上傳區 (Upload Area)
    st.markdown("---")
    uploaded_file = st.file_uploader(t['upload_label'], type=['jpg', 'png', 'jpeg', 'webp'])
    
    if uploaded_file:
        # 即時顯示預覽 (Visual Feedback)
        st.image(uploaded_file, caption="Preview", width=None, use_column_width=True)
        
        # 顯示專業提示卡片 (Premium Tip Card)
        st.info(f"**{t['tip_title']}**\n\n{t['tip_content']}")
        
        # Action Button
        if st.button("✧ " + t['generating_img']):
            with st.spinner(t['generating_img']):
                try:
                    url = generate_image_api(uploaded_file)
                    st.session_state['generated_img_url'] = url
                    st.session_state.step = 2
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        # 空狀態時的提示
        st.markdown(f"<div style='text-align: center; color: #aaa; padding: 20px;'>⚜️ {t['upload_hint']}</div>", unsafe_allow_html=True)

# ---------------- SCREEN 2: CONFIRMATION ----------------
elif st.session_state.step == 2:
    
    st.markdown(f"<h3>{t['confirm_title']}</h3>", unsafe_allow_html=True)
    
    # Hero Image Display
    if 'generated_img_url' in st.session_state:
        # 顯示圖片，加一點陰影 CSS 效果
        st.image(st.session_state['generated_img_url'], use_column_width=True)
        st.markdown(f"<p style='text-align: center; margin-top: 10px;'>{t['confirm_desc']}</p>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            # 使用 CSS class 渲染次級按鈕樣式
            st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
            if st.button(t['btn_retry']):
                st.session_state.step = 1
                del st.session_state['generated_img_url']
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            if st.button(t['btn_confirm']):
                st.session_state.step = 3
                st.rerun()

# ---------------- SCREEN 3: VIDEO GEN & RESULT ----------------
elif st.session_state.step == 3:
    
    # 這裡我們需要判斷是「正在生成」還是「生成完成」
    if 'final_video_path' not in st.session_state:
        # === 娛樂化等待模式 (Carousel Simulation) ===
        
        st.markdown(f"<h3>{t['video_loading_title']}</h3>", unsafe_allow_html=True)
        
        # Progress Bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        tips_container = st.empty()
        
        # 模擬進度 (前半段) - 展示醫美知識 Carousel
        # 由於 replicate.run 是 blocking call，我們在 call 之前先跑一段「儀式感」動畫
        tips = t['video_tips']
        
        # 展示 3 個 Tips (約 6-8 秒)
        for i in range(3):
            random_tip = random.choice(tips)
            tips_container.info(f"⚜️ **Beauty Knowledge**\n\n{random_tip}")
            # 模擬進度條移動
            for p in range(i*30, (i+1)*30):
                progress_bar.progress(p + 1)
                time.sleep(0.02) 
            time.sleep(1.5) # 停留讓用戶閱讀
            
        status_text.text("AI Rendering in progress (High-Res)...")
        progress_bar.progress(90)
        
        # 真正的 API Call (Blocking)
        try:
            veo_url = generate_video_api(st.session_state['generated_img_url'])
            local_veo = download_file(veo_url, "temp_veo.mp4")
            
            if local_veo:
                status_text.text("Finalizing Composite...")
                final_path = process_composite(local_veo)
                if final_path:
                    st.session_state['final_video_path'] = final_path
                    st.rerun() # 刷新頁面顯示結果
        except Exception as e:
             st.error(f"Production Error: {e}")
             if st.button("Return"):
                 st.session_state.step = 1
                 st.rerun()

    else:
        # === 結果展示 (Result) ===
        st.markdown(f"<h3>{t['result_title']}</h3>", unsafe_allow_html=True)
        
        # Video Player (Autoplay muted usually requires user interaction on web, but we try)
        st.video(st.session_state['final_video_path'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Call to Actions
        col_share, col_dl = st.columns(2)
        
        with col_share:
            # WhatsApp Share Link
            msg = "Look at my exclusive Lumière CNY video! ✨"
            wa_link = f"https://wa.me/?text={msg}"
            st.link_button(f"💬 {t['share_whatsapp']}", wa_link)
            
        with col_dl:
            with open(st.session_state['final_video_path'], "rb") as f:
                st.download_button(
                    label=f"📥 {t['download']}",
                    data=f,
                    file_name="Lumiere_CNY_2025.mp4",
                    mime="video/mp4"
                )
        
        st.markdown("---")
        if st.button(t['restart']):
            # Reset all
            for key in ['generated_img_url', 'final_video_path']:
                if key in st.session_state: del st.session_state[key]
            st.session_state.step = 1
            st.rerun()
