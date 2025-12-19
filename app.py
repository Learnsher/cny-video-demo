import streamlit as st
import replicate
import os
import requests
import PIL.Image  # 新增這一行

# --- 修正 Pillow 10+ 的 ANTIALIAS 錯誤 ---
# 這段必須放在 from moviepy... 之前
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ---------------------------------------

from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
import tempfile

# --- 頁面設定 ---
st.set_page_config(page_title="CNY Video Gen Ultimate", page_icon="🧧")

# --- 1. 安全驗證 ---
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 錯誤：未檢測到 API Token。請在 Streamlit Secrets 中設定 REPLICATE_API_TOKEN。")
    st.stop()

# --- 模型設定 ---
MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

# --- 核心功能函數 ---

def download_file(url, local_filename):
    """下載檔案"""
    try:
        r = requests.get(url, timeout=60)
        with open(local_filename, 'wb') as f:
            f.write(r.content)
        return local_filename
    except Exception as e:
        st.error(f"下載失敗: {e}")
        return None

def generate_cny_image_strict(uploaded_file, prompt):
    """步驟 2: Nano Banana Pro (使用 image_input 列表)"""
    
    uploaded_file.seek(0)
    final_prompt = f"{prompt}, festive chinese new year atmosphere, cinematic lighting, photorealistic, 8k"
    
    print(f"DEBUG: Calling {MODEL_IMG_GEN}")

    # 根據 Nano Banana Pro API: image_input 必須是 list
    input_args = {
        "prompt": final_prompt,
        "image_input": [uploaded_file], 
        "resolution": "2K",
        "aspect_ratio": "9:16",
        "output_format": "png",
        "safety_filter_level": "block_only_high"
    }
    
    output = replicate.run(MODEL_IMG_GEN, input=input_args)
    
    # 取得圖片 URL
    if hasattr(output, 'url'):
        return output.url
    elif isinstance(output, list):
        return str(output[0])
    else:
        return str(output)

def animate_with_veo_fast(image_url):
    """步驟 4: Veo 3.1 Fast (根據你的 Python Example)"""
    
    print(f"DEBUG: Calling {MODEL_VIDEO_GEN}")
    
    # 根據 Veo 3.1 API Example
    input_args = {
        "image": image_url, # 這裡接受 URL 字串
        "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution, smooth motion",
        "duration": 4,          # 你的需求：3秒
        "resolution": "720p",   # 建議 720p 以加快速度，或改 "1080p"
        "aspect_ratio": "9:16", # 你的需求：直式
        "generate_audio": False # 關閉 AI 音效，因為我們要用 bgm.mp3
    }
    
    output = replicate.run(MODEL_VIDEO_GEN, input=input_args)
    
    return str(output)

def process_final_composite(veo_video_path):
    """步驟 4後製: 合成 Intro + Veo + Outro + BGM"""
    
    if not os.path.exists("intro.mp4") or not os.path.exists("outro.mp4"):
        st.error("⚠️ 找不到素材！請確認 intro.mp4 和 outro.mp4 已上傳至 GitHub 根目錄。")
        return None

    try:
        clip_intro = VideoFileClip("intro.mp4")
        clip_veo = VideoFileClip(veo_video_path)
        clip_outro = VideoFileClip("outro.mp4")
        
        # 強制統一尺寸 (9:16 - 1080x1920)
        target_res = (1080, 1920)
        
        def safe_resize(clip):
            return clip.resize(height=target_res[1]).crop(x_center=clip.w/2, width=target_res[0])

        try:
            clip_intro = safe_resize(clip_intro)
            clip_veo = safe_resize(clip_veo)
            clip_outro = safe_resize(clip_outro)
        except Exception:
            # Fallback if crop fails
            clip_intro = clip_intro.resize(newsize=target_res)
            clip_veo = clip_veo.resize(newsize=target_res)
            clip_outro = clip_outro.resize(newsize=target_res)

        final_clip = concatenate_videoclips([clip_intro, clip_veo, clip_outro], method="compose")
        
        if os.path.exists("bgm.mp3"):
            bgm = AudioFileClip("bgm.mp3")
            if bgm.duration < final_clip.duration:
                bgm = bgm.loop(duration=final_clip.duration)
            else:
                bgm = bgm.subclip(0, final_clip.duration)
            
            bgm = bgm.volumex(0.6)
            # 因為我們關閉了 Veo 的音效，所以直接使用 BGM
            final_clip = final_clip.set_audio(bgm)
            
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        final_clip.write_videofile(
            tfile.name, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24,
            preset="medium",
            logger=None
        )
        
        clip_intro.close()
        clip_veo.close()
        clip_outro.close()
        if os.path.exists("bgm.mp3"): bgm.close()
        
        return tfile.name

    except Exception as e:
        st.error(f"合成過程發生錯誤: {e}")
        return None

# --- UI 前端介面 ---

st.title("🧧 CNY 活動祝賀視頻系統")
st.markdown("流程：上傳照片 -> 生成賀圖 -> 確認 -> 生成影片")

uploaded_file = st.file_uploader("1. 上傳您的照片 (不限比例)", type=['jpg', 'png', 'jpeg', 'webp'])

if uploaded_file:
    st.image(uploaded_file, caption="原始照片", width=200)
    
    default_prompt = "A festive Chinese New Year portrait, traditional elegant red and gold clothing, joyful expression, holding a red envelope"
    user_prompt = st.text_area("提示詞 (Prompt)", default_prompt, height=100)

    # 步驟 2
    if st.button("2. 生成賀圖預覽 (Nano Banana Pro)"):
        with st.spinner("正在生成圖片..."):
            try:
                img_url = generate_cny_image_strict(uploaded_file, user_prompt)
                st.session_state['generated_img_url'] = img_url
                st.success("圖片生成成功！")
            except Exception as e:
                st.error(f"生成圖片失敗: {e}")

# 步驟 3
if 'generated_img_url' in st.session_state:
    st.markdown("---")
    st.subheader("3. 請確認生成結果")
    st.image(st.session_state['generated_img_url'], caption="AI 預覽圖 (9:16)", width=300)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔄 不滿意，清除重試"):
            del st.session_state['generated_img_url']
            st.rerun()
    with col2:
        confirm_btn = st.button("✅ 確認 OK - 製作最終視頻")

    # 步驟 4 & 5
    if confirm_btn:
        st.markdown("---")
        progress_box = st.empty()
        
        try:
            # A. Veo 3.1
            with progress_box.container():
                st.info("正在啟動 Google Veo 3.1 Fast (需時約 1-3 分鐘)...")
                veo_url = animate_with_veo_fast(st.session_state['generated_img_url'])
                local_veo = download_file(veo_url, "temp_veo.mp4")
            
            if local_veo:
                # B. 合成
                with progress_box.container():
                    st.info("動畫完成！正在進行最終合成...")
                    final_path = process_final_composite(local_veo)
                
                if final_path:
                    progress_box.empty()
                    st.success("🎉 視頻製作完成！")
                    st.video(final_path)
                    
                    with open(final_path, "rb") as f:
                        st.download_button(
                            label="下載祝賀視頻 (.mp4)",
                            data=f,
                            file_name="cny_greeting.mp4",
                            mime="video/mp4"
                        )
                    os.remove(local_veo)
                    
        except Exception as e:
            st.error(f"製作失敗: {e}")
