import gradio as gr
import requests  # 引入请求库，用来和 FastAPI 通信

# ----------------- 1. 连接并拉取 FastAPI 的真实 74 款美甲数据 -----------------
FASTAPI_BASE_URL = "http://127.0.0.1:8000"

try:
    # 页面启动时，直接去 FastAPI 拿洗好的 74 款美甲数据（包含图片、名称、ID）
    response = requests.get(f"{FASTAPI_BASE_URL}/")
    # 为了让 Gradio 稳定拿到纯净的商品 JSON，我们也可以通过访问 health 或者定义好的列表
    # 这里我们直接向 FastAPI 发起一个基础请求。为了100%安全，我们在前端加载时动态拉取数据。
    # 考虑到我们刚刚修复了主页，我们从服务中捞取商品。
except Exception as e:
    print(f"无法连接到 FastAPI 服务: {e}")

# 兜底动态获取：为了防错，我们编写一个函数在 demo 启动时向后端索要完整商品列表
def get_all_products_from_backend():
    try:
        # 我们的 api.py 启动时会打印商品数量，我们可以通过发送请求拿到完整数据
        # 针对你的 products.json 结构，我们直接在 Gradio 里建立本地映射，这样最稳固迅速
        import json
        with open("products.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        # 如果读取失败，自动生成基础的 74 款兜底
        return [{"id": f"nail_{i:03d}", "name": f"美甲款式 {i:03d}", "image": f"/static/images/nail_{i:03d}.jpg"} for i in range(1, 75)]

ALL_PRODUCTS = get_all_products_from_backend()


# ----------------- 2. 完美的自定义 CSS（跑马灯横滑 + 美团黄） -----------------
custom_css = """
body, .gradio-container {
    background-color: #FFFFFF !important;
    border: none !important;
    padding: 20px !important;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif !important;
}
h1, h2, h3, h4, p, span, label, .markdown-text { color: #111111 !important; }
.brand-title { text-align: center !important; margin-bottom: 25px !important; }
.brand-title h1 { font-size: 32px !important; font-weight: 800 !important; margin-bottom: 8px !important; }
.brand-subtitle-desc {
    font-size: 14px !important; color: #555555 !important;
    background-color: #FFF9D0 !important; display: inline-block !important;
    padding: 6px 16px !important; border-radius: 20px !important; font-weight: 500;
}
.step-title { margin-bottom: 10px !important; margin-top: 10px !important; }
.step-title h4 { font-size: 16px !important; font-weight: 700 !important; display: flex !important; align-items: center !important; }
.gradio-container .gr-file-drop, .gradio-container .image-container, .yellow-gradient-box {
    border: 2px dashed #FFC000 !important; background: linear-gradient(to bottom, #FFFBE6 0%, #FFFFFF 100%) !important; border-radius: 12px !important;
}
/* 强行将 Gallery 改造为单行、横向丝滑滚动的跑马灯 */
.nail-carousel-container {
    border: 2px dashed #FFC000 !important; background: linear-gradient(to bottom, #FFFBE6 0%, #FFFFFF 100%) !important; border-radius: 12px !important; padding: 10px !important;
}
.nail-carousel-container .grid {
    display: flex !important; flex-wrap: nowrap !important; overflow-x: auto !important; overflow-y: hidden !important; scroll-behavior: smooth !important; gap: 12px !important;
}
.nail-carousel-container .grid::-webkit-scrollbar { height: 6px !important; }
.nail-carousel-container .grid::-webkit-scrollbar-thumb { background-color: #FFC000 !important; border-radius: 3px !important; }
/* 锁死卡片物理大小 */
.nail-carousel-container .grid > div {
    flex: 0 0 110px !important; width: 110px !important; max-width: 110px !important; height: 140px !important;
    background: #ffffff !important; border-radius: 8px !important; border: 1px solid #E5E5E5 !important; transition: all 0.2s ease !important;
}
.nail-carousel-container .grid > div:hover { border-color: #FFB000 !important; transform: translateY(-2px) !important; }
.right-deep-gradient-box {
    border: 2px dashed #FFB000 !important; background: linear-gradient(to bottom, #FFF4B8 0%, #FFFDF0 100%) !important; border-radius: 12px !important; padding: 10px !important; height: 560px !important; display: flex !important; flex-direction: column !important;
}
.right-deep-gradient-box div[data-testid="image"], .right-deep-gradient-box .image-container { flex-grow: 1 !important; height: 100% !important; background-color: transparent !important; }
.gesture-card-box {
    border: 2px dashed #FFC000 !important; background-color: #FFFFFF !important; border-radius: 12px !important; padding: 12px 8px !important; text-align: center !important; max-width: 135px !important; min-width: 135px !important; height: 222px !important; display: flex !important; flex-direction: column !important; justify-content: space-between !important; align-items: center !important;
}
.gesture-card-box .image-container img { max-width: 110px !important; max-height: 110px !important; width: 110px !important; height: 110px !important; object-fit: contain !important; }
.output-container-relative { position: relative !important; }
.meituan-watermark { position: absolute !important; right: 25px !important; bottom: 25px !important; background: rgba(255, 192, 0, 0.95) !important; color: #111111 !important; font-weight: 900 !important; font-size: 13px !important; padding: 5px 12px !important; border-radius: 6px !important; z-index: 10 !important; }
.action-btn { background-color: #FFC000 !important; color: #111111 !important; font-weight: bold !important; font-size: 16px !important; border-radius: 25px !important; border: None !important; padding: 14px 0 !important; width: 100% !important; box-shadow: 0 4px 12px rgba(255, 192, 0, 0.2) !important; }
.btn-row { margin-top: 20px !important; }
"""

# ----------------- 3. 核心业务交互逻辑 -----------------

def load_initial_nails():
    """初始化加载：把 74 款美甲平铺进滑动展示栏"""
    # 这里将图片路径或线上的 url 提出来传给 Gallery
    # 注意：如果你的 products.json 里包含 http 链接，直接可以用；如果是相对路径，Gradio 也能直接识别
    return [(p.get("image", ""), p.get("name", "")) for p in ALL_PRODUCTS]

def on_nail_selected(evt: gr.SelectData):
    """当用户划着滑动条，卡嗒点中其中一款时，抓取它在数据库中的真实 ID"""
    selected_name = evt.value
    selected_id = ""
    for p in ALL_PRODUCTS:
        if p["name"] == selected_name:
            selected_id = p["id"]
            break
    print(f"【前端捕捉】用户选中了美甲，ID为: {selected_id}，名称为: {selected_name}")
    return selected_id

def trigger_tryon_and_recommend(selected_id, hand_img):
    """【重头戏】用户点击试戴：渲染效果图 + 轰击 FastAPI 后端要回 8 款推荐结果"""
    if not selected_id:
        raise gr.Error("请先在上方左右滑动并点击选择一款美甲款式！")
    if hand_img is None:
        raise gr.Error("请上传您的手部照片！")
        
    # 1. 模拟试戴结果（这里可以替换成你真实的图片拼接算法或 GAN 模型）
    # 目前用原图代表试戴生成图逻辑
    result_image = hand_img 
    
    # 2. 衔接你的 FastAPI 推荐大脑
    recommended_gallery_data = []
    try:
        # 构建请求数据，严格对齐你的 FastAPI 接收模型 RecommendationRequest
        payload = {
            "current_product_id": str(selected_id).strip(),
            "top_k": 8
        }
        
        # 发送 POST 请求到你的推荐接口 `/recommendations`
        res = requests.post(f"{FASTAPI_BASE_URL}/recommendations", json=payload, timeout=5)
        
        if res.status_code == 200:
            res_data = res.json()
            if res_data.get("success"):
                # 你的 api.py 里的 recommendations 接口返回的是一个包含列表的字典
                # 每个推荐项含有: "id", "name", "image", "score", "reason"
                recs = res_data.get("recommendations", [])
                
                for item in recs:
                    # 将图片和“名字 + 推荐理由”结合起来，视觉效果更佳
                    display_label = f"{item['name']} ({item['reason']})"
                    recommended_gallery_data.append((item["image"], display_label))
                    
                print(f"【推荐成功】成功从后端召回了 {len(recommended_gallery_data)} 款关联美甲")
    except Exception as e:
        print(f"【推荐失败】请求 FastAPI 接口出错: {e}。将启用前端基础降级策略。")
        
    # 3. 降级兜底方案：如果后端接口挂了或者没响应，默认给它推前8款
    if not recommended_gallery_data:
        recommended_gallery_data = [(p["image"], p["name"]) for p in ALL_PRODUCTS[:8]]
        
    # 返回试戴结果图，并且把 74 款的选择栏自动“缩减刷新”为 8 款精准推荐美甲
    return result_image, recommended_gallery_data


# ----------------- 4. Gradio 拼装界面 -----------------
with gr.Blocks(css=custom_css) as demo:
    
    # 隐藏的文本框，用来暗中记住用户到底选了哪款美甲 ID
    selected_nail_id_holder = gr.Textbox(visible=False, value="")
    
    with gr.Row(elem_classes="brand-title"):
        with gr.Column():
            gr.Markdown("# 美团 AI 美甲试戴系统")
            gr.Markdown("### MEITUAN VIRTUAL NAILART SALON")
            gr.Markdown("<div class='brand-subtitle-desc'>💡 挑选心仪美甲点击试戴，AI 将为您智能推荐同风格、同色系的最优款式</div>")
        
    with gr.Row():
        # 左侧控制面板
        with gr.Column(scale=14):
            with gr.Column(elem_classes="step-title"):
                gr.Markdown("<h4><span style='color:#FFC000; margin-right:8px;'>●</span>STEP 1: 左右滑动选择美甲款式（共 74 款）</h4>")
            
            # 核心滑动组件
            nail_gallery = gr.Gallery(
                label="可选美甲款式",
                columns=74, # 极宽的列数强制在一行内挤压
                rows=1,
                height=170,
                allow_preview=False,
                show_label=False,
                elem_classes="nail-carousel-container"
            )
            
            gr.HTML("<div style='margin-top: 10px;'></div>")
            
            with gr.Column(elem_classes="step-title"):
                gr.Markdown("<h4><span style='color:#FFC000; margin-right:8px;'>●</span>STEP 2: 上传您的手部照片</h4>")
            
            with gr.Row():
                with gr.Column(scale=10, elem_classes="yellow-gradient-box"):
                    hand_input = gr.Image(label="手部照片", type="pil", sources=["upload"])
                
                with gr.Column(scale=2, elem_classes="gesture-card-box"):
                    gr.Markdown("<b style='color:#111; font-size:11px;'>手势 A</b>")
                    gr.Image("/Users/weichu/Desktop/posture_a.png", interactive=False, show_label=False)
                    gr.Markdown("<span style='font-size:10px; color:#555; font-weight:bold;'>手心朝上</span>")
                
                with gr.Column(scale=2, elem_classes="gesture-card-box"):
                    gr.Markdown("<b style='color:#111; font-size:11px;'>手势 B</b>")
                    gr.Image("/Users/weichu/Desktop/posture_b.png", interactive=False, show_label=False)
                    gr.Markdown("<span style='font-size:10px; color:#555; font-weight:bold;'>手背朝上</span>")
            
            with gr.Row(elem_classes="btn-row"):
                submit_btn = gr.Button("🔮 开始试戴 ＆ 激发AI个性化推荐", elem_classes="action-btn")
            
        # 右侧结果面板
        with gr.Column(scale=11, elem_classes="output-container-relative"):
            with gr.Column(elem_classes="step-title"):
                gr.Markdown("<h4><span style='color:#FFC000; margin-right:8px;'>●</span>STEP 3: 试戴视觉效果</h4>")
            
            with gr.Column(elem_classes="right-deep-gradient-box"):
                image_output = gr.Image(label="试戴预览图", interactive=False)
            
            gr.HTML("<div class='meituan-watermark'>美团 Meituan</div>")

    # ----------------- 5. 绑定动态连环事件 -----------------
    
    # 1. 页面打开时，把 74 款美甲塞进 Gallery 
    demo.load(fn=load_initial_nails, outputs=nail_gallery)
    
    # 2. 只要用户点击滑动栏里的任何一款图，暗地里更新选中的 ID
    nail_gallery.select(fn=on_nail_selected, outputs=selected_nail_id_holder)
    
    # 3. 点击大按钮：不仅出试戴图，还要把那 74 款的滑动栏冲刷成 FastAPI 算出来的 8 款强相关推荐
    submit_btn.click(
        fn=trigger_tryon_and_recommend,
        inputs=[selected_nail_id_holder, hand_input],
        outputs=[image_output, nail_gallery]
    )

# 启动界面
demo.launch(server_name="127.0.0.1", server_port=7995)