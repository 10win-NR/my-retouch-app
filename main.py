import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="🕊️ My Personal Retouch", page_icon="🕊️")
st.title("🕊️ 私だけの美肌アプリ")
st.markdown("### ~ 気になるところを指でなぞってね ~")


# ==========================================
# 1. 画像処理ロジック（のっぺり美肌）
# ==========================================
def smooth_skin_flat(image, factor):
    if factor == 0:
        return image

    # コントラストを下げてアラを飛ばす
    alpha = 1.0 - (factor / 200.0)
    beta = int((1.0 - alpha) * 128)
    low_contrast = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

    # 強めの平滑化（ぼかし）
    d = int(5 + (25 * factor / 100))
    sigma = int(20 + (150 * factor / 100))
    smoothed = cv2.bilateralFilter(low_contrast, d, sigma, sigma)
    return smoothed


# ==========================================
# 2. Streamlit UI
# ==========================================

# サイドバー設定
st.sidebar.header("✨ ペンと加工の調整")
stroke_width = st.sidebar.slider("ペンの太さ", 5, 100, 30)
smooth_factor = st.sidebar.slider("美肌（のっぺり具合）", 0, 100, 60)

uploaded_file = st.file_uploader("写真を選んでね", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # 画像の読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # スマホ画面でも塗りやすいように、表示用の幅を固定して高さを計算
    canvas_width = 400
    canvas_height = int(canvas_width * (image.height / image.width))

    st.write("👇 写真の美肌にしたい部分を指（マウス）で塗りつぶしてね")

    # お絵かきキャンバスの配置
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0.5)",
        stroke_width=stroke_width,
        stroke_color="rgba(255, 255, 255, 0.5)",
        background_image=Image.open(uploaded_file),  # ←この1行を必ず入れる！
        update_streamlit=True,
        height=400, # 必要に応じてサイズ調整
        drawing_mode="freedraw",
        key="canvas",
    )

    # キャンバスに何か描かれたら処理を実行
    if canvas_result.image_data is not None:
        # キャンバスの描画データ（RGBA）からアルファチャンネル（透明度）を抽出してマスクにする
        mask = canvas_result.image_data[:, :, 3]

        # 描画されたマスクは表示用サイズ(400px)なので、元の画像の解像度に引き伸ばす
        mask_resized = cv2.resize(mask, (img_bgr.shape[1], img_bgr.shape[0]))

        # マスクの境界をフワッとぼかす（フェザリング）ことで、塗った跡を自然に馴染ませる
        blur_size = int(max(img_bgr.shape[1], img_bgr.shape[0]) * 0.05)
        if blur_size % 2 == 0: blur_size += 1
        mask_blurred = cv2.GaussianBlur(mask_resized, (blur_size, blur_size), 0)

        # 0.0〜1.0の割合に変換
        mask_normalized = mask_blurred / 255.0
        mask_stack = np.dstack([mask_normalized, mask_normalized, mask_normalized])

        # 美肌画像を作成
        img_flat_skin = smooth_skin_flat(img_bgr, smooth_factor)

        # 元画像と美肌画像を、塗ったマスクの形に合わせて合成！
        result_bgr = (img_flat_skin * mask_stack + img_bgr * (1.0 - mask_stack)).astype(np.uint8)

        st.write("✨ 処理結果")
        st.image(Image.fromarray(cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)), use_column_width=True)

        # 保存ボタン
        is_success, buffer = cv2.imencode(".png", result_bgr)
        if is_success:
            st.download_button("この写真を保存する 🕊️", data=io.BytesIO(buffer).getvalue(),
                               file_name="my_best_self.png", mime="image/png")
