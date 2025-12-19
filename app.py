import streamlit as st
import replicate
import os
import requests
import PIL.Image
import time
import random

# --- 1. 系統補丁 ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from moviepy.audio.fx.all import audio_loop 
import tempfile

# --- 頁面設定 (必須在最上) ---
st.set_page_config(page_title="LUNAR 2025 | Bespoke AI", page_icon="🐍", layout="centered")

# --- CSS: High Fashion Style Injection ---
st.markdown("""
<style>
    /* 全局字體與背景 */
    .stApp {
        background-color: #FAFAFA; /* 極淺灰，比純白更有質感 */
        font-family: 'Helvetica Neue', Helvetica, Arial, serif;
    }
    
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 標題樣式 */
    .brand-title {
        font-family: 'Times New Roman', serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: #1A1A1A;
        text-align: center;
        letter-spacing: 2px;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
    }
    .brand-subtitle {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 0.9rem;
        color: #888;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 3px;
        margin-bottom: 3rem;
    }

    /* 按鈕高級化 (黑底白字+金邊) */
    .stButton > button {
        width: 100%;
        background-color: #1A1A1A;
        color: #FFFFFF;
        border: 1px solid #C5A059; /* 香檳金 */
        border-radius: 0px; /* 直角設計，更時尚 */
        padding: 12px 24px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 14px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #C5A059;
        color: #1A1A1A;
        border-color: #1A1A1A;
    }
    
    /* Secondary Button (重試) */
    .secondary-btn > button {
        background-color: transparent;
        color: #1A1A1A;
        border: 1px solid #CCCCCC;
    }
    
    /* 卡片容器 */
    .card-container {
        background: white;
        padding: 2rem;
        border: 1px solid #EAEAEA;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Loading Carousel Text */
    .carousel-title {
        font-family: 'Times New Roman', serif;
        font-size: 1.2rem;
        color: #C5A059;
        margin-bottom: 0.5rem;
    }
    .carousel-text {
        font-size: 0.9rem;
        color: #555;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# --- SVG Icons (Line Art) ---
ICON_UPLOAD = """<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" stroke-width="1" stroke-linecap="square"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>"""
ICON_CHECK = """<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#C5A059" stroke-width="1" stroke-linecap="square"><polyline points="20 6 9 17 4 12"></polyline></svg>"""
ICON_VIDEO = """<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#1A1A1A" stroke-width="1" stroke-linecap="square"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>"""

# --- 2. 安全驗證 ---
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("SYSTEM ERROR: API Token Missing.")
    st.stop()

# --- 初始化 Session State ---
if 'step' not in st.session_state:
    st.session_state['step'] = 1
if 'generated_img_url' not in st.session_state:
    st.session_state['generated_img_url'] = None
if 'final_video_path' not in st.session_state:
    st.session_state['final_video_path'] = None

# --- 模型設定 ---
MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

# --- 核心功能函數 (保持 v3.2 的穩健邏輯) ---

def download_file(url, local_filename):
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(local_filename, 'wb') as f:
                f.write(r.content)
            return local_filename
        return None
    except:
        return None

def generate_cny_image_strict(uploaded_file):
    """Step 2: Generate (Prompt Hidden)"""
    uploaded_file.seek(0)
    # 客戶指定的 Prompt
    final_prompt = "a CNY greeting photo of this woman, in 9:16 ratio, do not include any text / 中文字 in the image."
    
    input_args = {
        "prompt": final_prompt,
        "image_input": [uploaded_file], 
        "resolution": "2K",
        "aspect_ratio": "9:16",
        "output_format": "png",
        "safety_filter_level": "block_only_high"
    }
    
    output = replicate.run(MODEL_IMG_GEN, input=input_args)
    
    if hasattr(output, 'url'):
        return output.url
    elif isinstance(output, list):
        return str(output[0])
    else:
        return str(output)

def animate_with_veo_fast(image_url):
    """Step 3: Veo Animation"""
    input_args = {
        "image": image_url,
        "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution, smooth motion",
        "duration": 4,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": False 
    }
    output = replicate.run(MODEL_VIDEO_GEN, input=input_args)
    return str(output)

def resize_with_padding(clip, target_resolution=(1080, 1920)):
    target_w, target_h = target_resolution
    resized_clip = clip.resize(height=target_h)
    if resized_clip.w > target_w:
         resized_clip = resized_clip.resize(width=target_w)
    background = ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
    final_composite = CompositeVideoClip([background, resized_clip.set_position("center")])
    return final_composite

def process_final_composite(veo_video_path):
    if not os.path.exists("intro.mp4") or not os.path.exists("outro.mp4"):
        return None

    if not os.path.exists(veo_video_path) or os.path.getsize(veo_video_path) < 1000:
         return None
         
    try:
        clip_intro_raw = VideoFileClip("intro.mp4")
        clip_veo_raw = VideoFileClip(veo_video_path)
        clip_outro_raw = VideoFileClip("outro.mp4")
        
        target_res = (1080, 1920)
        clip_intro = resize_with_padding(clip_intro_raw, target_res)
        clip_veo = resize_with_padding(clip_veo_raw, target_res)
        clip_outro = resize_with_padding(clip_outro_raw, target_res)

        final_clip = concatenate_videoclips([clip_intro, clip_veo, clip_outro], method="compose")
        
        if os.path.exists("bgm.mp3"):
            bgm = AudioFileClip("bgm.mp3")
            if bgm.duration < final_clip.duration:
                bgm = audio_loop(bgm, duration=final_clip.duration)
            else:
                bgm = bgm.subclip(0, final_clip.duration)
            bgm = bgm.volumex(0.6)
            final_clip = final_clip.set_audio(bgm)
            
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        
        final_clip.write_videofile(
            tfile.name, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24,
            preset="slow", 
            verbose=False,
            logger=None
        )
        
        clip_intro_raw.close()
        clip_veo_raw.close()
        clip_outro_raw.close()
        if os.path.exists("bgm.mp3"): bgm.close()
        
        return tfile.name

    except Exception:
        return None

# --- UI Components ---

def render_header():
    st.markdown(f"""
    <div class="brand-title">LUNAR 2025</div>
    <div class="brand-subtitle">The Bespoke AI Experience</div>
    """, unsafe_allow_html=True)

def render_trivia_card():
    """High Fashion Trivia Carousel"""
    # 這是高級知識庫
    trivia_db = [
        {"title": "The Vermilion Aesthetic", "desc": "In Eastern art history, Red (Vermilion) represents not just luck, but the life force that connects generations."},
        {"title": "The Peony Symbolism", "desc": "Known as the 'King of Flowers', the Peony embodies prosperity, honor, and elegance in traditional textile design."},
        {"title": "The Infinite Knot", "desc": "The Mystic Knot (Pan Chang) has no beginning or end, symbolizing the Buddhist concept of eternal continuity."},
        {"title": "The Gold Standard", "desc": "Gold accents in Lunar attire mirror the imperial history, signifying spiritual enlightenment and wealth."},
    ]
    card = random.choice(trivia_db)
    
    st.markdown(f"""
    <div class="card-container">
        <div style="margin-bottom:10px;">⏳</div>
        <div class="carousel-title">{card['title']}</div>
        <div class="carousel-text">{card['desc']}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Main App Logic (SPA) ---

render_header()

# ================= SCREEN 1: UPLOAD =================
if st.session_state['step'] == 1:
    
    st.markdown(f"""
    <div style="text-align:center; margin-bottom: 2rem;">
        {ICON_UPLOAD}
        <p style="margin-top:10px; color:#555;">UPLOAD PORTRAIT</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg', 'webp'], label_visibility="collapsed")
    
    st.markdown("""
    <div style="font-size: 0.8rem; color: #999; text-align: center; margin-top: 1rem;">
        RECOMMENDATION<br>
        High resolution • Clear lighting • Front facing<br>
        Avoid: Sunglasses • Masks • Group photos
    </div>
    """, unsafe_allow_html=True)

    if uploaded_file:
        if st.button("GENERATE PORTRAIT"):
            with st.spinner("Analyzing aesthetics..."):
                try:
                    img_url = generate_cny_image_strict(uploaded_file)
                    st.session_state['generated_img_url'] = img_url
                    st.session_state['step'] = 2
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ================= SCREEN 2: REVIEW =================
elif st.session_state['step'] == 2:
    
    st.markdown(f"""
    <div style="text-align:center; margin-bottom: 1rem;">
        {ICON_CHECK}
        <p style="margin-top:10px; color:#C5A059;">REVIEW PORTRAIT</p>
    </div>
    """, unsafe_allow_html=True)

    # 顯示生成的圖片 (Card Style)
    col_img, _ = st.columns([3, 0.1]) # Center hack
    with col_img:
        st.image(st.session_state['generated_img_url'], use_column_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        # 使用 CSS class 自定義樣式
        st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
        if st.button("DISCARD"):
            st.session_state['generated_img_url'] = None
            st.session_state['step'] = 1
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        if st.button("PROCEED TO VIDEO"):
            st.session_state['step'] = 3
            st.rerun()

# ================= SCREEN 3: VIDEO RESULT =================
elif st.session_state['step'] == 3:
    
    # 如果還沒有生成視頻，進入 Loading/Processing 狀態
    if st.session_state['final_video_path'] is None:
        
        # 顯示 High Fashion Trivia
        render_trivia_card()
        
        # 進度條 (Visual Only)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("INITIALIZING CREATIVE DIRECTOR AI...")
        progress_bar.progress(10)
        time.sleep(1) # Fake delay for UX
        
        try:
            # 1. Veo Generation
            status_text.text("RENDERING CINEMATIC MOTION (Estimated: 2 mins)...")
            progress_bar.progress(30)
            
            # 由於 Streamlit 是同步的，這裡會 Block 住，Carousel 無法轉動
            # 但我們可以呈現一個靜態的高級介面
            veo_url = animate_with_veo_fast(st.session_state['generated_img_url'])
            
            progress_bar.progress(70)
            status_text.text("DOWNLOADING RAW FOOTAGE...")
            local_veo = download_file(veo_url, "temp_veo.mp4")
            
            # 2. Compositing
            if local_veo:
                progress_bar.progress(85)
                status_text.text("COMPOSITING FINAL CUT WITH AUDIO...")
                final_path = process_final_composite(local_veo)
                
                if final_path:
                    progress_bar.progress(100)
                    st.session_state['final_video_path'] = final_path
                    # 清理暫存
                    os.remove(local_veo)
                    st.rerun() # 刷新頁面顯示結果
                else:
                    st.error("Compositing Failed.")
                    time.sleep(2)
                    st.session_state['step'] = 2
                    st.rerun()
            else:
                 st.error("Video Generation Failed.")
                 time.sleep(2)
                 st.session_state['step'] = 2
                 st.rerun()

        except Exception as e:
            st.error(f"System Error: {e}")

    # 如果已經有視頻，顯示結果
    else:
        st.markdown(f"""
        <div style="text-align:center; margin-bottom: 1rem;">
            {ICON_VIDEO}
            <p style="margin-top:10px; color:#1A1A1A;">YOUR MASTERPIECE</p>
        </div>
        """, unsafe_allow_html=True)

        st.video(st.session_state['final_video_path'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 下載按鈕
        with open(st.session_state['final_video_path'], "rb") as f:
            st.download_button(
                label="DOWNLOAD VIDEO",
                data=f,
                file_name="LUNAR_2025_ELEGANCE.mp4",
                mime="video/mp4"
            )
            
        # WhatsApp Share Link (Native)
        st.markdown("""
        <a href="https://wa.me/?text=Check%20out%20my%20Lunar%20New%20Year%20AI%20Portrait!%20%23LUNAR2025" target="_blank" style="text-decoration:none;">
            <button style="width:100%; margin-top:10px; background-color:#25D366; color:white; border:none; padding:12px; text-transform:uppercase; font-family:sans-serif; cursor:pointer;">
                Share via WhatsApp
            </button>
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        if st.button("CREATE ANOTHER PORTRAIT"):
            # Reset All
            st.session_state['step'] = 1
            st.session_state['generated_img_url'] = None
            st.session_state['final_video_path'] = None
            st.rerun()
