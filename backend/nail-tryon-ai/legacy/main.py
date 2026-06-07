import io
import os
import gradio as gr
import requests
from PIL import Image

# 📡 后端 API 服务器的本地点火大门
BACKEND_URL = "http://127.0.0.1:8000"


# ==========================================
# 🔄 💡 核心函数 1：从后端拉取 74 款美甲商品数据库
# ==========================================
def load_initial_gallery():
    try:
        # 向 FastAPI 请求美甲列表数据
        res = requests.get(f"{BACKEND_URL}/api/initial_products", timeout=5)
        if res.status_code == 200 and res.json().get("success"):
            products = res.json().get("products", [])
            # ✨ 核心修正：直接使用 p.get("image") 的网络URL，绝不在前面强行拼接 BACKEND_URL
            return [(p.get("image", ""), f"[{p['id']}] {p['name']}") for p in products]
    except Exception as e:
        print(f"❌ 前端获取美甲商品库列表失败，请确认 api.py 是否已提前启动: {e}")
    return []


# ==========================================
# 🔄 💡 核心函数 2：当用户点击画廊里的美甲时触发
# ==========================================
def on_nail_selected(evt: gr.SelectData):
    """
    evt.value: 选中的美甲图片的 URL 链接
    evt.caption: 选中的美甲标题，例如 "[nail_001] 奶油裸色极简短甲"
    """
    img_url = evt.value if isinstance(evt.value, str) else evt.value.get("image", {}).get("url", "")
    title = evt.caption if evt.caption else ""

    # 🕵️‍♂️ 从标题中把硬核的 product_id 抠出来
    product_id = ""
    if "[" in title and "]" in title:
        product_id = title.split("]")[0].replace("[", "").strip()

    print(f"🎯 [前端激活] 用户在网页上选中了美甲！ID: {product_id} | URL: {img_url}")

    # 去网络上拉取这张图，展示在下方的“选中的美甲款式”预览框中
    try:
        response = requests.get(img_url, timeout=5)
        if response.status_code == 200:
            selected_image = Image.open(io.BytesIO(response.content))
            # 返回两个值：一个给预览框，一个存进隐藏的 State 变量里
            return selected_image, product_id
    except Exception as e:
        print(f"❌ 前端加载选中的美甲缩略图失败: {e}")

    return None, product_id


# ==========================================
# 🚀 💡 核心函数 3：点击“开始 AI 全自动试戴”大按钮时触发
# ==========================================
def predict_interface(hand_image, product_id):
    """
    hand_image: 用户在网页上上传的自己手部照片 (PIL Image 格式)
    product_id: 隐藏记录的当前选中的美甲编号 (字符串)
    """
    if hand_image is None:
        gr.Warning("✋ 请先上传一张您的手部照片！")
        return None
    if not product_id:
        gr.Warning("💅 请先在上方挑选一款您心仪的美甲款式！")
        return None

    print(f"\n🌐 [前端发射] 正在打包数据，向 FastAPI 请求试戴。美甲目标ID: {product_id}...")

    # 把用户传上来的手部图片转为二进制流
    hand_buf = io.BytesIO()
    hand_image.save(hand_buf, format="PNG")
    hand_buf.seek(0)

    # 构建标准的 Form-Data 表单数据
    files = {
        "hand_file": ("user_hand.png", hand_buf, "image/png"),
    }
    data = {
        "product_id": product_id  # 把选中的美甲ID带过去，供后端执行“偷梁换柱”
    }

    try:
        # 4090 跑 13 步算法耗时较长，这里 timeout 设为 120 秒，防止网页超时死掉
        response = requests.post(f"{BACKEND_URL}/api/nail_tryon", files=files, data=data, timeout=120)
        if response.status_code == 200:
            print("✨ [前端接收] 后端 13 步流水线完美跑完，成功拿到最终效果图！")
            return Image.open(io.BytesIO(response.content))
        else:
            print(f"❌ 后端接口报错，状态码: {response.status_code}")
            gr.Error("算法运行期间发生内部错误，请检查后端控制台！")
    except Exception as e:
        print(f"❌ 无法连接到 FastAPI 后端服务器: {e}")
        gr.Error("连接后端算法服务器超时，请确保 api.py 正在运行！")

    return hand_image


# ==========================================
# 🎨 💡 界面制服：定制“美团黄/小象黄”高颜值视觉皮肤
# ==========================================
custom_css = """
body, .gradio-container { background-color: #FAFAFA !important; }
.yellow-box { border: 2px dashed #FFC000 !important; background-color: #FFFDF0 !important; border-radius: 14px !important; padding: 15px; }
.action-btn { background-color: #FFC000 !important; color: #111111 !important; font-weight: bold !important; font-size: 18px !important; border-radius: 30px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; }
.action-btn:hover { background-color: #E6AE00 !important; cursor: pointer; }
"""

# ==========================================
# 🏗️ 💡 骨架搭建：使用最新的 Blocks 构建交互页面
# ==========================================
with gr.Blocks(css=custom_css, title="美团AI虚拟美甲沙龙") as demo:
    gr.Markdown("# 💅 美团 AI 美甲虚拟试戴沙龙 <span style='font-size:14px; color:#666;'>[4090 算法联动版]</span>")
    gr.Markdown(
        "🌟 **使用说明**：在上方精选美甲库中点击选中一款款式，在下方上传您的手部照片，点击黄金按钮，后台将全自动为您触发 13 步深度大模型融合算法进行佩戴展示。")

    # 🛠️ 创建一个隐藏的文本框，专门用来在网页后台偷偷记录用户当前选中的 product_id
    current_product_id = gr.State(value="")

    # 🎪 区域一：74款热门美甲大画廊
    with gr.Row():
        initial_gallery = gr.Gallery(
            label="✨ 美团热销·个性化美甲款式推荐库",
            columns=5,
            rows=2,
            height=320,
            type="filepath"
        )

    # 🎪 区域二：操作台与画布展示
    with gr.Row():
        # 左侧输入控制台（采用美团黄虚线包裹）
        with gr.Column(elem_classes="yellow-box", scale=1):
            nail_preview = gr.Image(label="📌 当前选中的美甲款式预览", type="pil", interactive=False, height=180)
            hand_input = gr.Image(label="✋ 上传您的干净手部照片", type="pil", height=240)
            submit_btn = gr.Button("开始 AI 全自动试戴", elem_classes="action-btn")

        # 右侧高清大图输出
        with gr.Column(scale=1):
            image_output = gr.Image(label="🔮 4090 管道实时渲染试戴效果图", type="pil", interactive=False, height=490)

    # ==========================================
    # ⚡ 💡 链路绑定：让网页上的动作具有生命力
    # ==========================================
    # 1. 网页刚一打开，自动向后端拉取美甲商品信息填满画廊
    demo.load(fn=load_initial_gallery, outputs=initial_gallery)

    # 2. 当用户在画廊里选中某张图时，自动更新预览框，并将 ID 塞进后台变量里
    initial_gallery.select(fn=on_nail_selected, outputs=[nail_preview, current_product_id])

    # 3. 点击一键试戴大按钮，把手部照片和选中的美甲 ID 快递给后端，并在右侧输出最终的 a13_natural_tryon.png
    submit_btn.click(
        fn=predict_interface,
        inputs=[hand_input, current_product_id],
        outputs=image_output
    )

# 🏁 点火启动前端网页系统
if __name__ == "__main__":
    # 锁定运行在 7999 端口
    demo.launch(server_name="127.0.0.1", server_port=7999, share=False)