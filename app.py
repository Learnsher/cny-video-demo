import streamlit as st
import replicate
import os
import requests
import PIL.Image
import time
import random

# --- 1. 系統補丁 (保持穩定性) ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from moviepy.audio.fx.all import audio_loop 
import tempfile

# --- 2. 頁面設定 & CSS (High Fashion Style) ---
st.set_page_config(page_title="2025 Snake Year Prestige Campaign", page_icon="🐍", layout="centered")

# CSS: 定義高級醫美風格 (勃艮第紅 + 香檳金 + 襯線字體)
st.markdown("""
    <style>
    /* 全局字體與背景 */
    .stApp {
        background-color: #FAFAFA; /* 極簡白灰背景 */
    }
    h1, h2, h3 {
        font-family: 'Times New Roman', serif;
        color: #800020; /* Burgundy 勃艮第紅 */
        font-weight: 300;
    }
    
    /* 按鈕樣式 (香檳金) */
    .stButton > button {
        background-color: #C5A059 !important; /* Champagne Gold */
        color: white !important;
        border-radius: 0px !important; /* 銳利邊角 High Fashion 感 */
        border: none !important;
        padding: 12px 24px !important;
        font-size: 16px !important;
        font-weight: 300 !important;
        letter-spacing: 1px;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #B08D55 !important;
    }
    
    /* 上傳框優化 */
    .stFileUploader {
        border: 1px dashed #C5A059;
        padding: 20px;
        border-radius: 0px;
    }
    
    /* 進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #800020;
    }
    
    /* 卡片容器 */
    .info-card {
        background-color: white;
        padding: 20px;
        border: 1px solid #E0E0E0;
        margin-top: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .carousel-text {
        font-family: 'Times New Roman', serif;
        font-size: 18px;
        color: #333;
        font-style: italic;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 安全驗證 ---
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("系統配置錯誤：未檢測到 API Token。")
    st.stop()

# --- 模型設定 ---
MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

# --- 狀態管理 (State Management) ---
if 'step' not in st.session_state:
    st.session_state['step'] = 1
if 'generated_img_url' not in st.session_state:
    st.session_state['generated_img_url'] = None

# --- 核心功能函數 ---

def download_file(url, local_filename):
    """下載檔案"""
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(local_filename, 'wb') as f:
                f.write(r.content)
            return local_filename
    except:
        pass
    return None

def resize_with_padding(clip, target_resolution=(1080, 1920)):
    """智能縮放：保留完整畫面，不足處填補黑邊"""
    target_w, target_h = target_resolution
    resized_clip = clip.resize(height=target_h)
    if resized_clip.w > target_w:
         resized_clip = resized_clip.resize(width=target_w)
    background = ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
    return CompositeVideoClip([background, resized_clip.set_position("center")])

def process_final_composite(veo_video_path):
    """合成最終影片"""
    if not os.path.exists("intro.mp4") or not os.path.exists("outro.mp4"):
        return None
        
    try:
        clip_intro = resize_with_padding(VideoFileClip("intro.mp4"))
        clip_veo = resize_with_padding(VideoFileClip(veo_video_path))
        clip_outro = resize_with_padding(VideoFileClip("outro.mp4"))
        
        final_clip = concatenate_videoclips([clip_intro, clip_veo, clip_outro], method="compose")
        
        if os.path.exists("bgm.mp3"):
            bgm = AudioFileClip("bgm.mp3")
            if bgm.duration < final_clip.duration:
                bgm = audio_loop(bgm, duration=final_clip.duration)
            else:
                bgm = bgm.subclip(0, final_clip.duration)
            final_clip = final_clip.set_audio(bgm.volumex(0.6))
            
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        final_clip.write_videofile(
            tfile.name, codec="libx264", audio_codec="aac", fps=24, preset="slow", verbose=False, logger=None
        )
        return tfile.name
    except Exception as e:
        print(f"Composite Error: {e}")
        return None

# --- 冷知識數據 (Luxury/Cultural Style) ---
TRIVIA_LIST = [
    {"icon": "local_florist", "text": "逛花市，轉大運。桃花代表緣分，百合寓意百年好合。"},
    {"icon": "auto_awesome", "text": "蛇年又稱「小龍年」，象徵智慧、靈動與新生。"},
    {"icon": "redeem", "text": "利是，又稱「利市」，寓意新一年大吉大利，好運連連。"},
    {"icon": "face_3", "text": "新年煥新顏，以最佳狀態迎接每一個閃耀時刻。"},
    {"icon": "diamond", "text": "珠光寶氣賀新歲，金飾不僅是裝飾，更承載著富貴與傳承。"},
    {"icon": "checkroom", "text": "穿上新衣，不僅是習俗，更是對自我的一份儀式感。"}
]

# --- UI 構建 ---

# Header (所有頁面共用)
col_h1, col_h2 = st.columns([1, 5])
with col_h1:
    st.markdown("## 🐍") # 品牌 Logo 位置
with col_h2:
    st.markdown("### 2025 PRESTIGE LUNAR NEW YEAR")
st.markdown("---")

# --- SCREEN 1: UPLOAD (啟動) ---
if st.session_state['step'] == 1:
    st.markdown("<h1 style='text-align: center;'>專屬訂製．您的賀歲光采</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Upload your portrait to create a personalized cinematic greeting.</p>", unsafe_allow_html=True)
    
    st.markdown("#### :material/upload: 上傳照片")
    uploaded_file = st.file_uploader("請選擇一張清晰的人像照片", type=['jpg', 'png', 'jpeg', 'webp'], label_visibility="collapsed")
    
    # Tips Section (Card Style)
    st.markdown("""
    <div class="info-card">
        <h5 style="color: #800020; margin-bottom: 10px;">💡 Perfect Result Guide</h5>
        <p style="font-size: 14px; text-align: left; margin: 5px 0;">:material/check_circle: <b>建議：</b> 光線充足、正面清晰、單人半身照。</p>
        <p style="font-size: 14px; text-align: left; margin: 5px 0;">:material/cancel: <b>避免：</b> 佩戴墨鏡/口罩、多人合照、模糊不清。</p>
    </div>
    """, unsafe_allow_html=True)
    
    if uploaded_file:
        if st.button("✨ 立即生成 (Generate Preview)"):
            st.session_state['uploaded_file'] = uploaded_file
            st.session_state['step'] = 2
            st.rerun()

# --- SCREEN 2: PREVIEW (預覽與確認) ---
elif st.session_state['step'] == 2:
    
    # 如果還沒生成 URL，就執行生成 (Loading State)
    if st.session_state['generated_img_url'] is None:
        with st.status("正在為您訂製專屬賀年造型...", expanded=True) as status:
            st.write("AI 正在分析面部特徵...")
            
            # 定義 Prompt (隱藏)
            hidden_prompt = "a CNY greeting photo of this woman, in 9:16 ratio, do not include any text / 中文字 in the image."
            
            try:
                # 呼叫 Banana Pro
                st.session_state['uploaded_file'].seek(0)
                input_args = {
                    "prompt": hidden_prompt,
                    "image_input": [st.session_state['uploaded_file']],
                    "resolution": "2K",
                    "aspect_ratio": "9:16",
                    "output_format": "png",
                    "safety_filter_level": "block_only_high"
                }
                output = replicate.run(MODEL_IMG_GEN, input=input_args)
                
                # 獲取結果
                if hasattr(output, 'url'):
                    st.session_state['generated_img_url'] = output.url
                elif isinstance(output, list):
                    st.session_state['generated_img_url'] = str(output[0])
                else:
                    st.session_state['generated_img_url'] = str(output)
                    
                status.update(label="生成完成！", state="complete", expanded=False)
            except Exception as e:
                st.error(f"生成遭遇技術問題，請重試: {e}")
                if st.button("返回上一步"):
                    st.session_state['step'] = 1
                    st.rerun()
                st.stop()
    
    # 顯示生成結果
    st.markdown("<h3 style='text-align: center;'>Preview Your Look</h3>", unsafe_allow_html=True)
    
    # 圖片置中
    col_img_1, col_img_2, col_img_3 = st.columns([1, 2, 1])
    with col_img_2:
        st.image(st.session_state['generated_img_url'], caption="AI 預覽效果", use_column_width=True)
    
    st.markdown("<p style='text-align: center; font-size: 14px; color: #800020;'>*確認效果滿意後，我們將為您製作動態影片*</p>", unsafe_allow_html=True)
    
    # 雙按鈕 Action
    col_btn_1, col_btn_2 = st.columns(2)
    with col_btn_1:
        if st.button("🔄 重新調整 (Retry)"):
            st.session_state['generated_img_url'] = None
            st.session_state['step'] = 1
            st.rerun()
    with col_btn_2:
        if st.button("✨ 確認並製作影片 (Proceed)"):
            st.session_state['step'] = 3
            st.rerun()

# --- SCREEN 3: VIDEO GEN & ENGAGEMENT (等待與結果) ---
elif st.session_state['step'] == 3:
    
    # 容器：用於顯示輪播內容
    carousel_placeholder = st.empty()
    video_result_placeholder = st.empty()
    
    # 開始製作影片 (使用非阻塞方式模擬)
    if 'final_video_path' not in st.session_state:
        
        # 1. 啟動後台任務 (Submit Prediction)
        try:
            # 模擬通知開關 UI
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #eee;">
                <span>:material/notifications_active: 完成後通知我 (Notify me)</span>
                <span style="color: #C5A059;">ON</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 使用 replicate.predictions.create (Async)
            prediction = replicate.predictions.create(
                version=MODEL_VIDEO_GEN.split(":")[1] if ":" in MODEL_VIDEO_GEN else None, # 如果使用 model slug 則不需要 version hash，這裡簡化處理
                model=MODEL_VIDEO_GEN,
                input={
                    "image": st.session_state['generated_img_url'],
                    "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution, smooth motion",
                    "duration": 4,
                    "resolution": "720p",
                    "aspect_ratio": "9:16",
                    "generate_audio": False 
                }
            )
            
            # 2. 輪播循環 (Polling Loop)
            start_time = time.time()
            carousel_index = 0
            
            while prediction.status not in ['succeeded', 'failed', 'canceled']:
                # 更新輪播內容
                current_trivia = TRIVIA_LIST[carousel_index % len(TRIVIA_LIST)]
                
                with carousel_placeholder.container():
                    st.markdown(f"""
                    <div class="info-card" style="margin-top: 30px; border-top: 3px solid #C5A059;">
                        <h2 style="font-size: 32px; margin: 0;">:material/{current_trivia['icon']}:</h2>
                        <p class="carousel-text">{current_trivia['text']}</p>
                        <p style="font-size: 12px; color: #999; margin-top: 15px;">影片製作中... 請稍候片刻</p>
                        <div style="width: 100%; background-color: #eee; height: 4px; margin-top: 10px;">
                            <div style="width: {min((time.time() - start_time)*100/180, 95)}%; background-color: #800020; height: 4px; transition: width 0.5s;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 檢查狀態
                prediction.reload()
                
                # 每 4 秒切換一次 trivia
                time.sleep(4) 
                carousel_index += 1
            
            if prediction.status == 'succeeded':
                veo_url = prediction.output
                
                # 顯示狀態
                carousel_placeholder.empty()
                with st.spinner("影片生成完成，正在進行最後合成 (Final Polish)..."):
                    local_veo = download_file(veo_url, "temp_veo.mp4")
                    if local_veo:
                        final_path = process_final_composite(local_veo)
                        st.session_state['final_video_path'] = final_path
                    else:
                        st.error("影片下載失敗。")
                        
            else:
                st.error("影片生成失敗，請重試。")
                st.stop()
                
        except Exception as e:
            st.error(f"系統繁忙: {e}")
            st.stop()

    # 3. 顯示最終結果 (Final Result)
    if 'final_video_path' in st.session_state:
        carousel_placeholder.empty() # 清除輪播
        
        st.markdown("<h3 style='text-align: center; color: #800020;'>Your Exclusive Moment</h3>", unsafe_allow_html=True)
        
        col_res_1, col_res_2, col_res_3 = st.columns([1, 2, 1])
        with col_res_2:
            st.video(st.session_state['final_video_path'])
            
            # CTA Buttons
            with open(st.session_state['final_video_path'], "rb") as f:
                st.download_button(
                    label=":material/download: 下載珍藏 (Download)",
                    data=f,
                    file_name="2025_prestige_greeting.mp4",
                    mime="video/mp4"
                )
            
            # 分享按鈕 (模擬)
            st.link_button(":material/share: 分享這份專屬祝福 (WhatsApp)", "https://wa.me/?text=Check%20out%20my%20Prestige%20CNY%20Video!")
            
            if st.button("✨ 製作另一段祝福 (Create Another)"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
