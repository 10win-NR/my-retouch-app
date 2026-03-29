import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import base64

# =======================================================
# 🚨 Streamlitバグ回避 ＆ サーバーメモリ対策パッチ
# =======================================================
import streamlit_drawable_canvas

def custom_image_to_url(image, width, clamp, channels, output_format, image_id, *args, **kwargs):
    buffered = io.BytesIO()
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

streamlit_drawable_canvas.st_image.image_to_url = custom_image_to_url
from streamlit_drawable_canvas import st_canvas

# ==========================================
# 基本設定とUI
# ==========================================
st.set_page_config(page_title="🕊️ My Personal Retouch V2", page_icon="🕊️")
st.title("🕊️ 私だけの美肌アプリ Ver.2")
st.markdown("### ~ 気になるところを指でなぞってね ~")

def smooth_skin_flat(image, factor):
    if factor == 0:
        return image
    alpha = 1.0 - (factor / 200.0)
    beta = int((1.0 - alpha) * 128)
    low_contrast = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    d = int(5 + (25 * factor / 100))
    sigma = int(20 + (150 * factor / 100))
    smoothed = cv2.bilateralFilter(low_contrast, d, sigma, sigma)
    return smoothed

# 写真アップロード
uploaded_file = st.file_uploader("写真を選んでね", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 念のためプログラム側でも20MB以上の巨大ファイルを弾く
    if uploaded_file.size > 20 * 1024 * 1024:
        st.error("⚠️ ファイルサイズが20MBを超えています。もう少し容量の小さい画像を選んでください。")
    else:
        original_image = Image.open(uploaded_file).convert("RGB")
        
        # 🚨 【メモリ対策】無料サーバーが爆発しないよう、最大1000pxに自動縮小
        MAX_SIZE = 1000
        if max(original_image.width, original_image.height) > MAX_SIZE:
            ratio = MAX_SIZE / max(original_image.width, original_image.height)
            new_size = (int(original_image.width * ratio), int(original_image.height * ratio))
            image = original_image.resize(new_size, Image.Resampling.LANCZOS)
        else:
            image = original_image.copy()

        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # UI改善：サイドバーを廃止し、画像のすぐ上に設定（ツールバー）を配置
        st.markdown("---")
        st.markdown("#### ✨ ペンと加工の調整")
        stroke_width = st.slider("ペンの太さ", 5, 100, 30)
        smooth_factor = st.slider("美肌（のっぺり具合）", 0, 100, 60)
        st.write("👇 写真の美肌にしたい部分を指で塗りつぶしてね")

        # スマホ画面に収まりやすい幅に調整
        canvas_width = 350
        canvas_height = int(canvas_width * (image.height / image.width))

        # お絵かきキャンバスの配置
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0.5)",
            stroke_width=stroke_width,
            stroke_color="rgba(255, 255, 255, 0.5)",
            background_image=image,
            update_streamlit=True,
            height=canvas_height,
            width=canvas_width,
            drawing_mode="freedraw",
            key="canvas_v2",
        )

        if canvas_result.image_data is not None:
            mask = canvas_result.image_data[:, :, 3]

            if np.any(mask):
                mask_resized = cv2.resize(mask, (img_bgr.shape[1], img_bgr.shape[0]))
                blur_size = int(max(img_bgr.shape[1], img_bgr.shape[0]) * 0.05)
                if blur_size % 2 == 0: blur_size += 1
                mask_blurred = cv2.GaussianBlur(mask_resized, (blur_size, blur_size), 0)

                mask_normalized = mask_blurred / 255.0
                mask_stack = np.dstack([mask_normalized, mask_normalized, mask_normalized])

                img_flat_skin = smooth_skin_flat(img_bgr, smooth_factor)
                result_bgr = (img_flat_skin * mask_stack + img_bgr * (1.0 - mask_stack)).astype(np.uint8)

                st.markdown("---")
                st.write("✨ 処理結果")
                st.image(Image.fromarray(cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)), use_column_width=True)

                is_success, buffer = cv2.imencode(".png", result_bgr)
                if is_success:
                    st.download_button("この写真を保存する 🕊️", data=io.BytesIO(buffer).getvalue(),
                                       file_name="my_best_self_v2.png", mime="image/png")
