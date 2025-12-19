import streamlit as st
import replicate
import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import tempfile

# 設定頁面
st.set_page_config(page_title="CNY Video Gen", page_icon="🧧")

# --- 1. 安全設定：從 Streamlit Secrets 讀取 Key ---
if 'REPLICATE_API_TOKEN' in st.secrets:
    os.environ["REPLICATE_API_TOKEN"] = st.secrets["REPLICATE_API_TOKEN"]
else:
    st.error("未設定 API Token，請在 Streamlit Secrets 設定 REPLICATE_API_TOKEN")
    st.stop()

# 模型設定 (請確保你有權限使用這些模型)
MODEL_IMG_GEN = "black-forest-labs/flux-schnell" 
MODEL_VIDEO_GEN = "google/veo-2" # 注意：Veo 3 可能還沒公開 API，暫用 Veo 2 或 minimax/video-01 替代，如你有 Veo 3 權限請改回

# --- 輔助函數 ---

def download_file(url, local_filename):
    """下載檔案"""
    r = requests.get(url)
    with open(local_filename, 'wb') as f:
        f.write(r.content)
    return local_filename

def generate_cny_image(prompt):
    """生成圖片"""
    output = replicate.run(
        MODEL_IMG_GEN,
        input={"prompt": prompt, "aspect_ratio": "9:16"}
    )
    # Flux 通常回傳 list of output objects (URLs)
    return output[0] if isinstance(output, list) else output

def animate_with_veo(image_url):
    """生成影片"""
    # 注意：不同模型的 input 參數不同，這裡是通用邏輯
    output = replicate.run(
        MODEL_VIDEO_GEN,
        input={
            "image": image_url,
            "prompt": "Cinematic camera pan, festive lights moving, 4k high quality",
        }
    )
    return output

def process_video(veo_video_path):
    """合成影片 (使用 tempfile 避免路徑問題)"""
    
    # 檢查 Assets 是否存在
    if not os.path.exists("assets/intro.mp4"):
        st.error("找不到 assets/intro.mp4，請上傳！")
        return None

    # 載入 Intro / Outro
    clip_intro = VideoFileClip("assets/intro.mp4")
    clip_outro = VideoFileClip("assets/outro.mp4")
    clip_veo = VideoFileClip(veo_video_path)
    
    # 統一尺寸
    target_res = (1080, 1920)
    clip_intro = clip_intro.resize(newsize=target_res)
    clip_outro = clip_outro.resize(newsize=target_res)
    clip_veo = clip_veo.resize(newsize=target_res)
    
    # 合成
    final_clip = concatenate_videoclips([clip_intro, clip_veo, clip_outro])
    
    # 加入音樂 (如果有)
    if os.path.exists("assets/bgm.mp3"):
        bgm = AudioFileClip("assets/bgm.mp3")
        # 循環音樂直到影片結束
        if bgm.duration < final_clip.duration:
             bgm = bgm.loop(duration=final_clip.duration)
        else:
             bgm = bgm.subclip(0, final_clip.duration)
        
        final_clip = final_clip.set_audio(bgm)
    
    # 輸出到暫存檔
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    final_clip.write_videofile(tfile.name, codec="libx264", audio_codec="aac", temp_audiofile='temp-audio.m4a', remove_temp=True, logger=None)
    
    return tfile.name

# --- UI 介面 ---

st.title("🧧 賀年視頻生成器")

cny_prompt = st.text_area("提示詞", "Chinese New Year atmosphere, red lanterns, gold sparkles, happy beautiful woman looking at camera, 9:16 vertical")

if st.button("1. 生成預覽圖"):
    with st.spinner("AI 正在繪圖..."):
        try:
            img_url = generate_cny_image(cny_prompt)
            st.session_state['img_url'] = img_url
            st.success("生成成功！")
        except Exception as e:
            st.error(f"錯誤: {e}")

if 'img_url' in st.session_state:
    st.image(st.session_state['img_url'], width=300, caption="預覽圖")
    
    if st.button("2. 確認並製作影片 (約需2分鐘)"):
        with st.spinner("製作中... (合成影片需要一點時間)"):
            try:
                # 1. 下載圖片
                local_img = download_file(st.session_state['img_url'], "temp_img.png")
                
                # 2. 生成動畫
                st.info("正在呼叫 Video AI 模型...")
                veo_url = animate_with_veo(st.session_state['img_url'])
                local_video = download_file(veo_url, "temp_video.mp4")
                
                # 3. 合成
                st.info("正在進行 FFmpeg 合成...")
                final_path = process_video(local_video)
                
                if final_path:
                    st.success("完成！")
                    st.video(final_path)
            except Exception as e:
                st.error(f"製作失敗: {e}")
