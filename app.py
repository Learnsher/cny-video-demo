import streamlit as st
import replicate
import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import tempfile

# --- 設定區 ---
st.set_page_config(page_title="CNY Video Gen Ultimate", page_icon="🧧")

# 1. 安全設定：從 Streamlit Secrets 讀取 Key
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("嚴重錯誤：未設定 API Token。請在 Streamlit Secrets 設定 REPLICATE_API_TOKEN。")
    st.stop()

# --- 模型定義 (根據你的要求) ---
# 【重要】請確保你的帳號有權限訪問此模型，否則會報錯
MODEL_IMG_GEN = "google/nano-banana-pro" 

# 【重要】請確保你的帳號有權限訪問此模型
MODEL_VIDEO_GEN = "google/veo-3.1-fast"

# --- 輔助函數 ---

def download_file(url, local_filename):
    """下載檔案到本地暫存"""
    r = requests.get(url)
    with open(local_filename, 'wb') as f:
        f.write(r.content)
    return local_filename

def generate_cny_image_with_banana(uploaded_file, prompt):
    """步驟 2: 使用 Nano Banana Pro 進行圖生圖"""
    # 這裡假設該模型接受 'image' (檔案物件) 和 'prompt' 作為輸入
    # 如果該模型的參數名不一樣 (例如叫 'input_image' 或需要特定 LoRA 觸發詞)，請在此修改
    input_args = {
        "image": uploaded_file,
        "prompt": prompt,
        "aspect_ratio": "9:16" # 嘗試強制 9:16，取決於模型是否支援
    }
    
    output = replicate.run(
        MODEL_IMG_GEN,
        input=input_args
    )
    
    # 處理回傳格式，強制轉字串 URL
    if isinstance(output, list):
        return str(output[0])
    else:
        return str(output)

def animate_with_veo_3_fast(image_url):
    """步驟 4: 使用 Veo 3.1 Fast 生成動畫"""
    # 這裡假設 Veo 3.1 Fast 接受 image_url 和 prompt
    input_args = {
        "image": image_url,
        # 這個 prompt 控制相機運動，可以寫死或讓用戶選
        "prompt": "Slow cinematic camera pan, festive golden particles floating, glowing lights, 4k resolution",
        # "duration": 3 # 如果模型支援指定秒數可加上
    }
    
    output = replicate.run(
        MODEL_VIDEO_GEN,
        input=input_args
    )
    return str(output)

def process_video_final(veo_video_path):
    """步驟 4後半: 合成最終影片"""
    
    # 檢查根目錄下的素材
    if not os.path.exists("intro.mp4") or not os.path.exists("outro.mp4"):
        st.error("錯誤：在根目錄找不到 intro.mp4 或 outro.mp4。")
        return None

    # 1. 載入片段
    clip_intro = VideoFileClip("intro.mp4")
    clip_veo = VideoFileClip(veo_video_path)
    clip_outro = VideoFileClip("outro.mp4")
    
    # 2. 強制統一尺寸為 1080x1920 (9:16)，避免合成錯誤
    target_res = (1080, 1920)
    # 使用 lambda 函數進行安全 resize，避免黑邊問題 (object-fit: cover 效果)
    def resize_cover(clip):
        return clip.resize(height=target_res[1]).crop(x_center=clip.w/2, width=target_res[0])

    try:
        clip_intro_resized = resize_cover(clip_intro)
        clip_veo_resized = resize_cover(clip_veo)
        clip_outro_resized = resize_cover(clip_outro)
    except Exception as e:
        st.warning(f"Resize 出現小問題，嘗試強制拉伸: {e}")
        clip_intro_resized = clip_intro.resize(newsize=target_res)
        clip_veo_resized = clip_veo.resize(newsize=target_res)
        clip_outro_resized = clip_outro.resize(newsize=target_res)

    # 3. 拼接
    final_clip = concatenate_videoclips([clip_intro_resized, clip_veo_resized, clip_outro_resized], method="compose")
    
    # 4. 處理音樂
    if os.path.exists("bgm.mp3"):
        bgm = AudioFileClip("bgm.mp3")
        # 調整音樂長度以配合影片
        if bgm.duration < final_clip.duration:
             bgm = bgm.loop(duration=final_clip.duration)
        else:
             bgm = bgm.subclip(0, final_clip.duration)
        
        # 設定音量並合併 (保留影片原聲+背景音樂)
        bgm = bgm.volumex(0.6)
        final_audio = CompositeAudioClip([final_clip.audio, bgm]) if final_clip.audio else bgm
        final_clip = final_clip.set_audio(final_audio)
    
    # 5. 輸出到暫存檔
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    # 使用 medium preset 平衡速度與品質
    final_clip.write_videofile(tfile.name, codec="libx264", audio_codec="aac", preset="medium", fps=24, verbose=False, logger=None)
    
    # 清理記憶體
    clip_intro.close()
    clip_veo.close()
    clip_outro.close()
    if os.path.exists("bgm.mp3"): bgm.close()
    
    return tfile.name

# --- UI 主流程 ---

st.title("🧧 CNY 活動祝賀視頻系統")
st.markdown("流程：上傳照片 -> 生成賀圖 -> 確認 -> 生成影片")

# 步驟 1：客人上傳相片
uploaded_file = st.file_uploader("1. 請上傳一張您的照片 (不限比例)", type=['jpg', 'png', 'jpeg'])

if uploaded_file is not None:
    st.image(uploaded_file, caption="您的原始照片", width=200)
    
    # CNY Prompt 建議
    default_cny_prompt = "A festive Chinese New Year portrait based on the person in the image, wearing traditional elegant red and gold Tang suit clothing, joyful expression, holding a red envelope (lai see), background filled with glowing red lanterns, golden confetti bokeh, luxurious festive atmosphere, warm cinematic lighting, vertical 9:16 composition."
    cny_prompt = st.text_area("調整賀圖提示詞 (Prompt)", default_cny_prompt, height=150)

    # 步驟 2：使用 NANO BANANA PRO 生成
    if st.button("2. 開始生成 CNY 賀圖預覽"):
        with st.spinner(f"正在呼叫 {MODEL_IMG_GEN} 模型進行圖生圖，請稍候..."):
            try:
                # 這裡關鍵：把上傳的檔案物件直接傳給函數
                img_url = generate_cny_image_with_banana(uploaded_file, cny_prompt)
                st.session_state['generated_img_url'] = img_url
                st.success("賀圖生成成功！請在下方確認。")
            except Exception as e:
                st.error(f"生成失敗，請檢查模型權限或參數。\n錯誤訊息: {e}")

# 步驟 3：客人 Confirm OK
if 'generated_img_url' in st.session_state:
    st.subheader("3. 確認預覽圖")
    st.image(st.session_state['generated_img_url'], caption="AI 生成的 CNY 賀圖 (9:16)", width=300)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("不滿意，清除重試"):
            del st.session_state['generated_img_url']
            st.experimental_rerun()
    
    with col2:
        confirm_btn = st.button("4. 確認 OK - 開始製作最終視頻 (VEO 3)")

    # 步驟 4：Animate (VEO 3 FAST) & Combine
    if confirm_btn:
        video_placeholder = st.empty()
        with video_placeholder.container():
            with st.spinner("啟動 VEO 3.1 FAST 生成動畫中 (這需要一點時間)..."):
                try:
                    # A. 呼叫 Veo 3
                    veo_url = animate_with_veo_3_fast(st.session_state['generated_img_url'])
                    st.info("VEO 動畫生成完畢，正在下載...")
                    
                    # B. 下載 Veo 影片到本地 temp
                    local_veo_path = download_file(veo_url, "temp_veo.mp4")
                    
                    # C. 合成最終影片
                    st.info("正在進行最終合成 (拼接 Intro/Outro/音樂)...")
                    final_video_path = process_video_final(local_veo_path)
                    
                    if final_video_path:
                        # 步驟 5：完成，比客用
                        st.success("5. 視頻製作完成！")
                        st.video(final_video_path)
                        
                        # 提供下載按鈕
                        with open(final_video_path, "rb") as file:
                            st.download_button(
                                label="下載您的祝賀視頻 (.mp4)",
                                data=file,
                                file_name="my_cny_greeting.mp4",
                                mime="video/mp4"
                            )
                    
                    # 清理暫存檔
                    os.remove(local_veo_path)
                    
                except Exception as e:
                    st.error(f"視頻製作過程發生錯誤: {e}")
