import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
import base64

# =======================================================
# 🚨 Streamlit最新版バグ突破 ＆ 超軽量化パッチ
# =======================================================
import streamlit_drawable_canvas

def custom_image_to_url(image, width, clamp, channels, output_format, image_id, *args, **kwargs):
    buffered = io.BytesIO()
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    # アルファチャンネル等のエラーを防ぐためRGBに統一
    if image.mode != "RGB":
        image = image.convert("RGB")
    # PNGではなくJPEGで圧縮してBase64化（真っ黒フリーズ対策の要！）
    image.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

streamlit_drawable_canvas.st_image.image_to_url = custom_image_to_url
from streamlit_drawable_canvas import st_canvas

# ==========================================
# 基本設定とUI
# ==========================================
st.set_page_config(page_title="🕊️ My Personal Retouch", page_icon="🕊️")
st.title("🕊️ 私だけの美肌アプリ")
st.markdown("### ~ 気になるところを指でなぞってね ~")

# ==========================================
# 画像処理ロジック（OpenCV）
# ==========================================
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

# ==========================================
# メイン処理
# ==========================================
st.sidebar.header("✨ ペンと加工の調整")
stroke_width = st.sidebar.slider("ペンの太さ", 5, 100, 30)
smooth_factor = st.sidebar.slider("美肌（のっぺり具合）", 0, 100, 60)

uploaded_file = st.file_uploader("写真を選んでね", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 画像の読み込み
    original_image = Image.open(uploaded_file).convert("RGB")
    
    # --- キャンバス用に画像を軽くする（ブラウザの真っ黒化を防ぐ） ---
    CANVAS_MAX_WIDTH = 700
    width, height = original_image.size
    ratio = CANVAS_MAX_WIDTH / width
    
    if ratio < 1.0:
        canvas_width = CANVAS_MAX_WIDTH
        canvas_height = int(height * ratio)
        bg_image = original_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    else:
        canvas_width = width
        canvas_height = height
        bg_image = original_image.copy()

    # --- OpenCVでの裏側処理用は「高画質」をキープ ---
    img_array = np.array(original_image)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    st.write("👇 写真の美肌にしたい部分を指（マウス）で塗りつぶしてね")

    # お絵かきキャンバスの配置
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0.5)",
        stroke_width=stroke_width,
        stroke_color="rgba(255, 255, 255, 0.5)",
        background_image=bg_image,  # 軽量化した画像を渡す
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="freedraw",
        key="canvas_ultimate",
    )

    # キャンバスに何か描かれたら処理を実行
    if canvas_result.image_data is not None:
        mask = canvas_result.image_data[:, :, 3]

        if np.any(mask):
            # マスクを高画質な元画像サイズに引き伸ばす
            mask_resized = cv2.resize(mask, (img_bgr.shape[1], img_bgr.shape[0]))
            blur_size = int(max(img_bgr.shape[1], img_bgr.shape[0]) * 0.05)
            if blur_size % 2 == 0: blur_size += 1
            mask_blurred = cv2.GaussianBlur(mask_resized, (blur_size, blur_size), 0)

            mask_normalized = mask_blurred / 255.0
            mask_stack = np.dstack([mask_normalized, mask_normalized, mask_normalized])

            # 美肌処理と合成
            img_flat_skin = smooth_skin_flat(img_bgr, smooth_factor)
            result_bgr = (img_flat_skin * mask_stack + img_bgr * (1.0 - mask_stack)).astype(np.uint8)

            st.write("✨ 処理結果")
            st.image(Image.fromarray(cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)), use_column_width=True)

            # 保存
            is_success, buffer = cv2.imencode(".png", result_bgr)
            if is_success:
                st.download_button("この写真を保存する 🕊️", data=io.BytesIO(buffer).getvalue(),
                                   file_name="my_best_self.png", mime="image/png")
