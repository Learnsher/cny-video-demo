import streamlit as st
import replicate
import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
import tempfile

# --- 頁面設定 ---
st.set_page_config(page_title="CNY Video Gen Ultimate", page_icon="🧧")

# --- 1. 安全驗證：讀取 API Key ---
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("❌ 錯誤：未檢測到 API Token。請在 Streamlit Secrets 中設定 REPLICATE_API_TOKEN。")
    st.stop()

# --- 模型設定 (根據你的指定) ---
# 注意：請確保你的 Replicate 帳號有權限存取這兩個模型
MODEL_IMG_GEN = "google/nano-banana-pro" 
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

# --- 核心功能函數 ---

def download_file(url, local_filename):
    """下載 Replicate 生成的檔案"""
    try:
        r = requests.get(url, timeout=60)
        with open(local_filename, 'wb') as f:
            f.write(r.content)
        return local_filename
    except Exception as e:
        st.error(f"下載失敗: {e}")
        return None

def generate_cny_image_safe(uploaded_file, prompt):
    """步驟 2: 圖生圖 (修正版：透過 Prompt 控制比例，避免 API 報錯)"""
    
    # 確保檔案指針在開頭
    uploaded_file.seek(0)
    
    # 【關鍵修正】將 9:16 寫入 Prompt，而不是作為參數傳送
    final_prompt = f"{prompt}, 9:16 ratio, vertical composition, high quality"
    
    print(f"DEBUG: Using Model: {MODEL_IMG_GEN}")
    print(f"DEBUG: Prompt: {final_prompt}")

    # 設定參數 (移除 aspect_ratio 以防斷線)
    # 如果你的模型輸入欄位叫 'input_image'，請將下方的 'image' 改為 'input_image'
    input_args = {
        "image": uploaded_file,
        "prompt": final_prompt,
        "prompt_strength": 0.65,  # 0.65 代表 65% 聽從 Prompt，35% 保留原圖特徵
        "num_inference_steps": 25,
        "guidance_scale": 7.5
    }
    
    output = replicate.run(
        MODEL_IMG_GEN,
        input=input_args
    )
    
    # 格式處理：強制轉字串
    if isinstance(output, list):
        return str(output[0])
    else:
        return str(output)

def animate_with_veo_fast(image_url):
    """步驟 4: 生成視頻 (Veo 3.1 Fast)"""
    
    input_args = {
        "image": image_url,
        "prompt": "Slow cinematic camera pan, festive atmosphere, glowing lights, 4k resolution, smooth motion",
    }
    
    output = replicate.run(
        MODEL_VIDEO_GEN,
        input=input_args
    )
    return str(output)

def process_final_composite(veo_video_path):
    """步驟 4後製: 合成 Intro + Gen Video + Outro + BGM"""
    
    # 檢查素材是否存在 (在根目錄)
    if not os.path.exists("intro.mp4") or not os.path.exists("outro.mp4"):
        st.error("⚠️ 找不到素材！請確認 intro.mp4 和 outro.mp4 已上傳至 GitHub 根目錄。")
        return None

    try:
        # 1. 讀取影片
        clip_intro = VideoFileClip("intro.mp4")
        clip_veo = VideoFileClip(veo_video_path)
        clip_outro = VideoFileClip("outro.mp4")
        
        # 2. 強制統一尺寸 (9:16 - 1080x1920)
        # 這是為了防止不同來源影片尺寸不合導致合成失敗
        target_res = (1080, 1920)
        
        def safe_resize(clip):
            # 先調整高度，再裁切寬度，確保填滿畫面
            return clip.resize(height=target_res[1]).crop(x_center=clip.w/2, width=target_res[0])

        clip_intro = safe_resize(clip_intro)
        clip_veo = safe_resize(clip_veo)
        clip_outro = safe_resize(clip_outro)

        # 3. 拼接
        final_clip = concatenate_videoclips([clip_intro, clip_veo, clip_outro], method="compose")
        
        # 4. 加入音樂
        if os.path.exists("bgm.mp3"):
            bgm = AudioFileClip("bgm.mp3")
            # 讓音樂循環或裁切以配合影片長度
            if bgm.duration < final_clip.duration:
                bgm = bgm.loop(duration=final_clip.duration)
            else:
                bgm = bgm.subclip(0, final_clip.duration)
            
            # 設定音量
            bgm = bgm.volumex(0.6)
            final_clip = final_clip.set_audio(bgm)
            
        # 5. 輸出 (使用 tempfile 避免權限問題)
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        final_clip.write_videofile(
            tfile.name, 
            codec="libx264", 
            audio_codec="aac", 
            fps=24,
            preset="medium",
            threads=4,
            logger=None # 隱藏過多 log
        )
        
        # 關閉資源
        clip_intro.close()
        clip_veo.close()
        clip_outro.close()
        
        return tfile.name

    except Exception as e:
        st.error(f"合成過程發生錯誤: {e}")
        return None

# --- UI 前端介面 ---

st.title("🧧 CNY 活動祝賀視頻系統")
st.markdown("流程：上傳照片 -> 生成賀圖 -> 確認 -> 生成影片")

# Step 1: Upload
uploaded_file = st.file_uploader("1. 上傳您的照片 (不限比例)", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    st.image(uploaded_file, caption="原始照片", width=200)
    
    # 預設提示詞
    default_prompt = "A festive Chinese New Year portrait, traditional elegant red and gold clothing, joyful expression, holding a red envelope, background filled with glowing red lanterns, golden bokeh, cinematic lighting"
    user_prompt = st.text_area("提示詞 (Prompt)", default_prompt, height=100)

    # Step 2: Generate Image
    if st.button("2. 生成賀圖預覽 (Nano Banana Pro)"):
        with st.spinner("正在生成圖片，請稍候..."):
            try:
                img_url = generate_cny_image_safe(uploaded_file, user_prompt)
                st.session_state['generated_img_url'] = img_url
                st.success("圖片生成成功！請在下方確認。")
            except Exception as e:
                st.error(f"生成圖片失敗: {e}")

# Step 3: Confirm & Review
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

    # Step 4: Generate Video & Combine
    if confirm_btn:
        st.markdown("---")
        progress_box = st.empty()
        
        try:
            # Phase A: Veo Animation
            with progress_box.container():
                st.info("正在啟動 Google Veo 3 Fast 生成動畫 (這需要幾分鐘)...")
                veo_url = animate_with_veo_fast(st.session_state['generated_img_url'])
                
                # 下載 Veo 影片
                local_veo = download_file(veo_url, "temp_veo.mp4")
            
            if local_veo:
                # Phase B: Final Composite
                with progress_box.container():
                    st.info("動畫完成！正在進行最終合成 (加上 Intro/Outro/音樂)...")
                    final_path = process_final_composite(local_veo)
                
                if final_path:
                    progress_box.empty()
                    st.success("🎉 視頻製作完成！")
                    st.video(final_path)
                    
                    with open(final_path, "rb") as f:
                        st.download_button(
                            label="下載祝賀視頻 (.mp4)",
                            data=f,
                            file_name="cny_greeting_video.mp4",
                            mime="video/mp4"
                        )
                    
                    # 清理暫存
                    os.remove(local_veo)
                    
        except Exception as e:
            st.error(f"製作過程中斷: {e}")
