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

# --- 0. 系統補丁 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- 1. 頁面設定 ---
st.set_page_config(page_title="LUMIÈRE - CNY Campaign", page_icon="✨", layout="mobile") 
# layout="mobile" 是一個隱藏參數，讓畫面在 Desktop 也是窄屏，模擬手機 App 體驗

# --- 2. HIGH FASHION CSS (關鍵部分) ---
st.markdown("""
    <style>
    /* 引入高級字體 */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=Lato:wght@300;400&display=swap');

    /* 全局變數 */
    :root {
        --bg-color: #FFFFFF;
        --text-color: #1A1A1A;
        --accent-gold: #C5A059;
        --brand-black: #000000;
        --brand-red: #800020;
    }

    /* 隱藏預設 Header/Footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-color);
        font-family: 'Lato', sans-serif;
    }

    /* 標題樣式 (Serif) - Chanel/Dior 風格 */
    h1 {
        font-family: 'Playfair Display', serif;
        font-weight: 500;
        font-size: 32px !important;
        text-align: center;
        color: var(--text-color);
        letter-spacing: 1.5px;
        margin-bottom: 0.5rem;
    }
    
    p, label, div {
        font-weight: 300;
        letter-spacing: 0.5px;
    }

    /* 上傳框 (仿 Wireframe 灰色方塊) */
    .stFileUploader > div > div {
        background-color: #F2F2F2;
        border: none;
        border-radius: 0px; /* 銳利邊角 */
        padding: 40px 20px;
        align-items: center;
        justify-content: center;
    }
    .stFileUploader button {
        display: none; /* 隱藏原本醜醜的按鈕，只留拖曳區 */
    }
    /* 這裡用 CSS Hack 模擬 Wireframe 中的 icon */
    .stFileUploader::before {
        content: "📷";  /* 實際上我們會用 icon 圖片，這裡暫用 Emoji 示意 */
        font-size: 40px;
        display: block;
        text-align: center;
        margin-bottom: 10px;
        color: #999;
    }
    .stFileUploader::after {
        content: "請按此上傳相片";
        display: block;
        text-align: center;
        color: #666;
        font-size: 14px;
        margin-top: -30px; /* 調整位置 */
    }

    /* 按鈕樣式 (Solid Black - Screen 4 & Screen 2 Primary) */
    .primary-btn button {
        background-color: var(--brand-black) !important;
        color: white !important;
        border: none;
        border-radius: 0px; /* 直角 */
        padding: 14px 0px;
        font-size: 14px;
        letter-spacing: 2px;
        text-transform: uppercase;
        width: 100%;
        transition: all 0.3s;
    }
    .primary-btn button:hover {
        background-color: #333 !important;
    }

    /* 按鈕樣式 (Outline - Screen 2 Secondary) */
    .outline-btn button {
        background-color: transparent !important;
        color: var(--brand-black) !important;
        border: 1px solid var(--brand-black) !important;
        border-radius: 0px;
        padding: 14px 0px;
        font-size: 14px;
        letter-spacing: 2px;
        width: 100%;
    }

    /* 進度圓圈 (Step 1 Footer) */
    .step-indicator {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 40px;
        color: #999;
        font-size: 12px;
    }
    .step-circle {
        width: 50px;
        height: 50px;
        background-color: #E0E0E0;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 10px;
        color: white;
        font-family: serif;
    }
    .step-arrow {
        color: #E0E0E0;
    }

    /* 圖片/影片容器 (Teal Placeholder -> Real Image) */
    .media-container img, .media-container video {
        width: 100%;
        aspect-ratio: 9/16;
        object-fit: cover;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1); /* 高級陰影 */
    }

    /* Loading Icon 圓圈 */
    .loading-circle {
        width: 80px;
        height: 80px;
        background-color: #D8D8D8;
        border-radius: 50%;
        margin: 20px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
    }
    
    /* Toggle Switch 顏色覆寫 */
    .stToggle {
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 狀態管理 & 語言包 ---

if 'step' not in st.session_state: st.session_state.step = 1
if 'lang' not in st.session_state: st.session_state.lang = 'EN' # 預設英文以符合 wireframe

TEXT = {
    'TC': {
        'title': "AI 煥發·新春",
        'subtitle': "為您準備個人化短片<br>送上溫馨祝福",
        'upload_hint': "✓ 清晰樣貌照片   ✕ 帶口罩   ✕ 多人合照",
        'step_1': "上傳相片", 'step_2': "查看新春形象", 'step_3': "發送祝福短片",
        's2_title': "您的新年形象真美！",
        's2_sub': "用此繼續生成祝賀短片？",
        'btn_restart': "重新開始",
        'btn_gen': "生成短片",
        's3_title': "短片生成中...",
        's3_sub': "約需時3分鐘，請稍等",
        'notify': "完成時通知我",
        'trivia_title': "新年小趣聞",
        's4_title': "祝賀短片已經準備好啦！",
        's4_sub': "立即分享出去啦<br>您亦可於收件匣隨時查看",
        'btn_share': "分享祝福短片",
        'back': "返回首頁"
    },
    'EN': {
        'title': "Radiant New Year",
        'subtitle': "Prepare your personalized video<br>Send warm wishes",
        'upload_hint': "✓ Clear Face   ✕ Mask   ✕ Group Photo",
        'step_1': "Upload", 'step_2': "Review", 'step_3': "Generate",
        's2_title': "You look stunning!",
        's2_sub': "Proceed to generate video with this look?",
        'btn_restart': "Restart",
        'btn_gen': "Create Video",
        's3_title': "Creating Video...",
        's3_sub': "Approx. 3 mins, please wait",
        'notify': "Notify me when done",
        'trivia_title': "CNY Trivia",
        's4_title': "Your Video is Ready!",
        's4_sub': "Share it now<br>Or view it in your inbox anytime",
        'btn_share': "Share Video",
        'back': "Back to Home"
    }
}
t = TEXT[st.session_state.lang]

# --- 4. 後端函數 (Robust Logic) ---
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

# --- 5. UI Layout (The Wireframe Implementation) ---

# Top Bar (Language Switch)
col_head_1, col_head_2 = st.columns([8, 2])
with col_head_2:
    # 這裡可以做成下拉選單，但為了簡潔用 Radio
    lang_choice = st.radio("Lang", ["EN", "TC"], horizontal=True, label_visibility="collapsed")
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

t = TEXT[st.session_state.lang] # Update text

# ================= SCREEN 1: UPLOAD =================
if st.session_state.step == 1:
    
    st.markdown(f"<h1>{t['title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666; font-size: 14px; margin-bottom: 40px;'>{t['subtitle']}</p>", unsafe_allow_html=True)
    
    # Upload Area
    uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'])
    
    # Do's and Don'ts (Below uploader)
    st.markdown(f"<p style='text-align: center; color: #333; font-size: 12px; margin-top: 10px;'>{t['upload_hint']}</p>", unsafe_allow_html=True)
    
    # Process Indicator (Footer) - 模擬 Wireframe 底部圓圈
    st.markdown(f"""
    <div class='step-indicator'>
        <div style='text-align: center;'>
            <div class='step-circle' style='background-color: #D8D8D8;'>icon</div>
            <div style='margin-top: 5px;'>{t['step_1']}</div>
        </div>
        <div class='step-arrow'>▶</div>
        <div style='text-align: center;'>
            <div class='step-circle'>icon</div>
            <div style='margin-top: 5px; color: #CCC;'>{t['step_2']}</div>
        </div>
        <div class='step-arrow'>▶</div>
        <div style='text-align: center;'>
            <div class='step-circle'>icon</div>
            <div style='margin-top: 5px; color: #CCC;'>{t['step_3']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Logic
    if uploaded_file:
        with st.spinner("Processing..."):
            try:
                url = generate_image_api(uploaded_file)
                st.session_state['generated_img_url'] = url
                st.session_state.step = 2
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ================= SCREEN 2: CONFIRMATION =================
elif st.session_state.step == 2:
    
    st.markdown(f"<h2 style='font-size: 20px; font-weight: 400; text-align: center; margin-bottom: 10px;'>{t['s2_title']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666; font-size: 14px;'>{t['s2_sub']}</p>", unsafe_allow_html=True)
    
    # Image Placeholder (9:16)
    if 'generated_img_url' in st.session_state:
        st.markdown(f'<div class="media-container"><img src="{st.session_state["generated_img_url"]}"></div>', unsafe_allow_html=True)
    
    st.write("") # Spacer
    
    # Buttons (Bottom)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="outline-btn">', unsafe_allow_html=True)
        if st.button(t['btn_restart']):
            st.session_state.step = 1
            del st.session_state['generated_img_url']
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
        if st.button(t['btn_gen']):
            st.session_state.step = 3
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ================= SCREEN 3: LOADING =================
elif st.session_state.step == 3:
    
    st.markdown(f"<h2 style='font-size: 20px; text-align: center; margin-top: 40px;'>{t['s3_title']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666;'>{t['s3_sub']}</p>", unsafe_allow_html=True)
    
    # Notification Toggle (Wireframe specific)
    # 使用 columns 來置中 toggle
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"<div style='background: #F9F9F9; padding: 15px; border-radius: 5px; display: flex; align-items: center; justify-content: space-between;'><span>{t['notify']}</span>", unsafe_allow_html=True)
        st.toggle("", value=False, label_visibility="collapsed") 
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.write("")
    
    # Trivia Section (Placeholder for carousel)
    st.markdown(f"<p style='text-align: center; color: #999; margin-top: 40px;'>{t['trivia_title']}</p>", unsafe_allow_html=True)
    
    trivia_placeholder = st.empty()
    
    # Progress Simulation & API Call
    # 這裡我們模擬 Wireframe 中間那個灰色圓形 Icon
    trivia_list = [
        "🧧 正月唔買鞋(唉)，但可以買褲(富)！",
        "🥟 餃子形狀似元寶，食得多賺得多！",
        "🔴 本命年著紅底褲，鴻運當頭！"
    ]
    
    # 1. 模擬動畫 (Kill Time)
    for i in range(2): # 轉兩次
        for trivia in trivia_list:
            trivia_placeholder.markdown(f"""
                <div style='text-align: center;'>
                    <div class='loading-circle'>icon</div>
                    <p style='font-size: 16px; color: #333; font-weight: 600;'>{trivia}</p>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            
    # 2. 實際生成
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
        st.error("Error generating video.")
        if st.button("Back"):
            st.session_state.step = 1
            st.rerun()

# ================= SCREEN 4: RESULT =================
elif st.session_state.step == 4:

    st.markdown(f"<h2 style='font-size: 20px; text-align: center; margin-top: 20px;'>{t['s4_title']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666; font-size: 14px;'>{t['s4_sub']}</p>", unsafe_allow_html=True)
    
    # Video Placeholder
    if 'final_video_path' in st.session_state:
         st.markdown(f"""
         <div class="media-container">
            <video controls autoplay muted style="width:100%; aspect-ratio:9/16;">
                <source src="data:video/mp4;base64,{st.session_state['final_video_path']}" type="video/mp4">
            </video>
         </div>
         """, unsafe_allow_html=True)
         # 注意：上面的 video tag 在 Streamlit 有時會讀取不到 local path，
         # 為了穩定，我們還是用 st.video，但用 CSS 去修飾它
         st.video(st.session_state['final_video_path'])
    
    st.write("")
    
    # Share Button (Solid Black)
    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    # 這裡可以用 st.link_button 連去 WhatsApp
    st.link_button(t['btn_share'], "https://wa.me/?text=Check%20out%20my%20CNY%20video!")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Back to Home (Text Link)
    st.markdown(f"<div style='text-align: center; margin-top: 20px; text-decoration: underline; cursor: pointer;'>", unsafe_allow_html=True)
    if st.button(t['back'], type="secondary"): # Use simple button but styled
        st.session_state.step = 1
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
