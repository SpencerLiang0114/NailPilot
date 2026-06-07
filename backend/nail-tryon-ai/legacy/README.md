import gradio as gr

# 专为美团定制：按钮全宽对齐、手势卡片与上传框上下等高、完美兼容 Gradio 6.0 语法
custom_css = """
/* 1. 页面整体：美团纯白底色 */
body, .gradio-container {
    background-color: #FFFFFF !important;
    border: none !important;
    padding: 20px !important;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif !important;
}

/* 2. 字体颜色规范 */
h1, h2, h3, h4, p, span, label, .markdown-text {
    color: #111111 !important;
}

.brand-title .prose, .brand-title {
    height: auto !important;
    min-height: max-content !important;
    overflow: visible !important;
}

/* 美团 brand 大标题与标语区 */
.brand-title {
    text-align: center !important;
    margin-bottom: 25px !important;
}
.brand-title h1 {
    font-size: 32px !important;
    font-weight: 800 !important;
    letter-spacing: 1px !important;
    margin-bottom: 8px !important;
}
.brand-subtitle-desc {
    font-size: 14px !important;
    color: #555555 !important;
    background-color: #FFF9D0 !important;
    display: inline-block !important;
    padding: 6px 16px !important;
    border-radius: 20px !important;
    font-weight: 500 !important;
    line-height: 1.5 !important;
}

/* 3. 步骤提示词样式 */
.step-title {
    margin-bottom: 10px !important;
    margin-top: 10px !important;
}
.step-title h4 {
    font-size: 16px !important;
    font-weight: 700 !important;
    display: flex !important;
    align-items: center !important;
}

/* 4. 左侧主输入框：浅黄色柔和渐变 */
.gradio-container .gr-file-drop, .gradio-container .image-container, .yellow-gradient-box {
    border: 2px dashed #FFC000 !important; 
    background: linear-gradient(to bottom, #FFFBE6 0%, #FFFFFF 100%) !important; 
    border-radius: 12px !important;
}

/* 5. 右侧展示框：等高对齐 */
.right-deep-gradient-box {
    border: 2px dashed #FFB000 !important; 
    background: linear-gradient(to bottom, #FFF4B8 0%, #FFFDF0 100%) !important; 
    border-radius: 12px !important;
    padding: 10px !important;
    min-height: 650px !important; 
    height: 650px !important;
    display: flex !important;
    flex-direction: column !important;
}
.right-deep-gradient-box div[data-testid="image"],
.right-deep-gradient-box .image-container {
    flex-grow: 1 !important;
    min-height: 100% !important;
    height: 100% !important;
    background-color: transparent !important;
}

/* 6. 放大手势卡片，并强行将其物理高度锁死，与左侧上传照片框上下绝对对齐 */
.gesture-card-box {
    border: 2px dashed #FFC000 !important;
    background-color: #FFFFFF !important;
    border-radius: 12px !important;
    padding: 12px 8px !important;
    text-align: center !important;
    max-width: 135px !important; 
    min-width: 135px !important;
    /* 物理高度精准对齐左侧上传框的上下边缘 */
    height: 222px !important;
    min-height: 222px !important;
    max-height: 222px !important;
    margin: 0 auto !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    align-items: center !important;
}

/* 稍微放大卡片内部的图片显示，让比例更好看 */
.gesture-card-box .image-container, 
.gesture-card-box .image-container .preview,
.gesture-card-box .image-container img,
.gesture-card-box div[data-testid="image"] {
    max-width: 110px !important;   
    max-height: 110px !important;  
    min-height: 110px !important;
    height: 110px !important;
    width: 110px !important;
    margin: 0 auto !important;
    object-fit: contain !important;
    background-color: transparent !important; 
}

/* 右栏展示区容器 */
.output-container-relative {
    position: relative !important;
}

/* 7. 右下角专属美团品牌水印 */
.meituan-watermark {
    position: absolute !important;
    right: 25px !important;
    bottom: 25px !important;
    background: rgba(255, 192, 0, 0.95) !important; 
    color: #111111 !important;
    font-weight: 900 !important;
    font-size: 13px !important;
    padding: 5px 12px !important;
    border-radius: 6px !important;
    letter-spacing: 1px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    z-index: 10 !important;
    pointer-events: none !important; 
}

/* 8. 强行让核心试戴按钮横向撑满100%，左右对齐最外层边界线 */
.action-btn {
    background-color: #FFC000 !important;
    color: #111111 !important;
    font-weight: bold !important;
    font-size: 16px !important;
    border-radius: 25px !important;
    border: None !important;
    padding: 14px 0 !important;
    width: 100% !important; 
    max-width: 100% !important;
    display: block !important;
    box-shadow: 0 4px 12px rgba(255, 192, 0, 0.2) !important;
}

/* 控制按钮行的边距 */
.btn-row {
    margin-top: 20px !important;
    padding: 0 !important;
}
"""

with gr.Blocks() as demo:
    
    # 顶部大标题 + 中英文功能宣称区
    with gr.Row(elem_classes="brand-title"):
        with gr.Column():
            gr.Markdown("# 美团 AI 美甲试戴")
            gr.Markdown("### MEITUAN VIRTUAL NAILART SALON")
            gr.Markdown("<div class='brand-subtitle-desc'>💡 无法想象实际上手效果，担心肤色不搭、手型不配？试试AI试戴！</div>")
        
    # 核心双栏排版
    with gr.Row():
        # 左栏：输入与示意区
        with gr.Column(scale=14):
            
            # 第一步
            with gr.Column(elem_classes="step-title"):
                gr.Markdown("<h4><span style='color:#FFC000; margin-right:8px;'>●</span>STEP 1: SELECT NAIL ART / 选择美甲款式</h4>")
            with gr.Column(elem_classes="yellow-gradient-box"):
                nail_input = gr.Image(label="Upload nail design", type="pil", sources=["upload"])
            
            gr.HTML("<div style='margin-top: 15px;'></div>")
            
            # 第二步
            with gr.Column(elem_classes="step-title"):
                gr.Markdown("<h4><span style='color:#FFC000; margin-right:8px;'>●</span>STEP 2: UPLOAD HAND PHOTO / 上传手部照片</h4>")
            
            # 手部上传 + 上下完美等高的左右对齐布局
            with gr.Row():
                with gr.Column(scale=10, elem_classes="yellow-gradient-box"):
                    hand_input = gr.Image(label="Upload your hand photo", type="pil", sources=["upload"])
                
                # 【已纠正】示意图一：对应你的 posture_a.png -> 手心朝上
                with gr.Column(scale=2, elem_classes="gesture-card-box"):
                    gr.Markdown("<b style='color:#111; font-size:11px;'>POSTURE A</b>")
                    gr.Image(
                        "/Users/weichu/Desktop/posture_a.png", 
                        value="/Users/weichu/Desktop/posture_a.png",
                        interactive=False,
                        show_label=False
                    )
                    gr.Markdown("<span style='font-size:10px; color:#555; font-weight:bold;'>手心朝上</span>")
                
                # 【已纠正】示意图二：对应你的 posture_b.png -> 手背朝上
                with gr.Column(scale=2, elem_classes="gesture-card-box"):
                    gr.Markdown("<b style='color:#111; font-size:11px;'>POSTURE B</b>")
                    gr.Image(
                        "/Users/weichu/Desktop/posture_b.png", 
                        value="/Users/weichu/Desktop/posture_b.png",
                        interactive=False,
                        show_label=False
                    )
                    gr.Markdown("<span style='font-size:10px; color:#555; font-weight:bold;'>手背朝上</span>")
            
            # 下方全宽大按钮行
            with gr.Row(elem_classes="btn-row"):
                submit_btn = gr.Button("START TRY-ON / 开始试戴", elem_classes="action-btn")
            
        # 右栏：展示区
        with gr.Column(scale=11, elem_classes="output-container-relative"):
            # 第三步
            with gr.Column(elem_classes="step-title"):
                gr.Markdown("<h4><span style='color:#FFC000; margin-right:8px;'>●</span>STEP 3: TRY-ON RESULT / 试戴效果臻选</h4>")
            
            with gr.Column(elem_classes="right-deep-gradient-box"):
                image_output = gr.Image(label="Your preview will appear here", interactive=False)
            
            # 右下角美团标志水印
            gr.HTML("<div class='meituan-watermark'>美团 Meituan</div>")

# 将 css 完美注入 launch 运行
demo.launch(
    css=custom_css,
    server_name="127.0.0.1", 
    server_port=7995, 
    share=True
)
