"""
finger_direction_detector.py (v2 - 修复SAM3 API)
============================================================
1. SAM3分割整个手部区域 (使用正确的 SAM3SemanticPredictor API)
2. 去除美甲并修补指尖
3. 检测手指关键点并计算手指方向向量
4. 输出: 修复后的手部图像 + 手指方向可视化 + 方向角度数据(CSV)

用法:
  conda activate meijia
  python s7_finger_direction_detectorV3.py
  python s7_finger_direction_detectorV3.py --single a8
"""

import os
import sys
import json
import glob as glob_mod
import argparse
import cv2
import numpy as np
import torch
from PIL import Image
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

from math import asin, degrees, sqrt

# 修复SSL证书问题
if "SSL_CERT_FILE" in os.environ:
    if not os.path.exists(os.environ["SSL_CERT_FILE"]):
        del os.environ["SSL_CERT_FILE"]
        os.environ.pop("REQUESTS_CA_BUNDLE", None)

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

def lkGetP2Pangle(x1, y1, x2, y2):
    """0-360° 逆时针：0°=右 90°=上 180°=左 270°=下"""
    dx = x2 - x1
    dy = y2 - y1
    Length = sqrt(dx ** 2 + dy ** 2)
    if Length == 0: return 0.0
    if y1 == y2 and dx > 0: return 0.0
    if x1 == x2 and dy < 0: return 90.0
    if y1 == y2 and dx < 0: return 180.0
    if x1 == x2 and dy > 0: return 270.0
    deg = degrees(asin(abs(dy) / Length))
    if dx > 0 and dy < 0:      return deg
    elif dx < 0 and dy < 0:    return 180 - deg
    elif dx < 0 and dy > 0:    return 180 + deg
    else:                       return 360 - deg


@dataclass
class Config:
    input_dir: str = "./s6_hands_natural"
    output_dir: str = "./s7_hands_finger_direction"
    json_dir: str = "./s7_hands_direction"
    sam3_checkpoint: str = "./sys/sam3_weights/sam3.pt"
    bpe_path: str = "./sys/bpe/bpe_simple_vocab_16e6.txt.gz"

    mp_min_detection_confidence: float = 0.3
    mp_min_tracking_confidence: float = 0.3
    # 手指定义: MediaPipe 21关键点索引
    finger_tips: List[int] = field(default_factory=lambda: [4, 8, 12, 16, 20])
    finger_bases: List[int] = field(default_factory=lambda: [3, 7, 11, 15, 19])
    finger_names: List[str] = field(default_factory=lambda: ["thumb", "index", "middle", "ring", "pinky"])

# ============================================================
# SAM3 手部分割器 (使用正确的API)
# ============================================================
class HandSegmentor:
    def __init__(self, config: Config):
        self.config = config
        print("  加载 SAM3 模型中...")
        from ultralytics.models.sam import SAM3SemanticPredictor
        overrides = dict(
            conf=0.25,
            task="segment",
            mode="predict",
            model=config.sam3_checkpoint,
            half=False,
            save=False,
        )
        self.predictor = SAM3SemanticPredictor(
            overrides=overrides, bpe_path=config.bpe_path
        )
        print("  SAM3 模型加载完成")

    def set_image(self, img_bgr: np.ndarray):
        """设置当前图像"""
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self.predictor.set_image(img_rgb)

    def segment_hand(self, img_bgr: np.ndarray) -> Optional[np.ndarray]:
        """
        用SAM3分割整个手部区域
        返回二值mask (0/255)
        """
        self.set_image(img_bgr)
        
        hand_prompts = ["hand", "human hand", "palm", "fingers", "hand with fingers"]
        best_mask = None
        best_area = 0

        for prompt in hand_prompts:
            try:
                results = self.predictor(text=[prompt])
                if not results or results[0].masks is None:
                    continue
                
                for mt in results[0].masks.data:
                    mask = mt.cpu().numpy()
                    mask_bin = (mask > 0.5).astype(np.uint8) * 255
                    # 缩放到原图尺寸
                    h, w = img_bgr.shape[:2]
                    mask_resized = cv2.resize(mask_bin, (w, h), interpolation=cv2.INTER_NEAREST)
                    
                    area = cv2.countNonZero(mask_resized)
                    if area > best_area:
                        best_area = area
                        best_mask = mask_resized
            except Exception as e:
                continue

        if best_mask is not None:
            # 形态学闭运算填充孔洞
            kernel = np.ones((15, 15), np.uint8)
            best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_CLOSE, kernel)
            # 形态学开运算去除小噪点
            kernel = np.ones((5, 5), np.uint8)
            best_mask = cv2.morphologyEx(best_mask, cv2.MORPH_OPEN, kernel)

        return best_mask

# ============================================================
# 指甲检测与去除
# ============================================================
class NailRemover:
    def __init__(self, config: Config):
        self.config = config
        from ultralytics.models.sam import SAM3SemanticPredictor
        overrides = dict(
            conf=0.25,
            task="segment",
            mode="predict",
            model=config.sam3_checkpoint,
            half=False,
            save=False,
        )
        self.predictor = SAM3SemanticPredictor(
            overrides=overrides, bpe_path=config.bpe_path
        )
        self.nail_prompts = ["nail", "fingernail", "nail polish", "fingernails"]

    def set_image(self, img_bgr: np.ndarray):
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self.predictor.set_image(img_rgb)

    def detect_nails(self, img_bgr: np.ndarray) -> List[np.ndarray]:
        """用SAM3检测指甲区域，返回mask列表"""
        self.set_image(img_bgr)
        nail_masks = []
        h, w = img_bgr.shape[:2]

        for prompt in self.nail_prompts:
            try:
                results = self.predictor(text=[prompt])
                if not results or results[0].masks is None:
                    continue
                
                for mt in results[0].masks.data:
                    mask = mt.cpu().numpy()
                    mask_bin = (mask > 0.5).astype(np.uint8) * 255
                    mask_resized = cv2.resize(mask_bin, (w, h), interpolation=cv2.INTER_NEAREST)
                    nail_masks.append(mask_resized)
            except Exception as e:
                continue

        # 合并所有指甲mask
        if nail_masks:
            combined = np.zeros_like(nail_masks[0])
            for m in nail_masks:
                combined = cv2.bitwise_or(combined, m)
            # 膨胀一下，确保完全覆盖美甲
            kernel = np.ones((7, 7), np.uint8)
            combined = cv2.dilate(combined, kernel, iterations=1)
            return [combined]
        return []

    @staticmethod
    def inpaint_nails(img_bgr: np.ndarray, nail_mask: np.ndarray) -> np.ndarray:
        """用OpenCV TELEA算法修补指甲区域"""
        result = img_bgr.copy()
        result = cv2.inpaint(result, nail_mask, 3, cv2.INPAINT_TELEA)
        return result

# ============================================================
# 手指方向检测器
# ============================================================
class FingerDirectionDetector:
    def __init__(self, config: Config):
        self.config = config
        self.mp_hands = None
        self.hands = None
        self._init_mediapipe()

    def _init_mediapipe(self):
        """初始化MediaPipe Hands"""
        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=True,
                max_num_hands=2,
                min_detection_confidence=self.config.mp_min_detection_confidence,
                min_tracking_confidence=self.config.mp_min_tracking_confidence
            )
            print("  MediaPipe Hands 初始化成功")
        except Exception as e:
            print(f"  MediaPipe 初始化失败: {e}")
            self.hands = None

    def _make_hands(self, conf: float):
        """用指定置信度创建 MediaPipe Hands 实例"""
        import mediapipe as mp
        mp_hands = mp.solutions.hands
        return mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=conf,
            min_tracking_confidence=conf,
        )

    def detect_with_mediapipe(self, img_bgr: np.ndarray) -> Optional[Dict]:
        """
        用MediaPipe检测手部关键点，计算手指方向
        自适应策略：按置信度从高到低重试，再尝试 CLAHE 增强后重试
        返回: {'finger_name': {'tip': (x,y), 'base': (x,y), 'angle': float, 'vector': (dx,dy)}}
        """
        if self.hands is None:
            return None

        confs = [0.3, 0.25, 0.2, 0.15, 0.1]
        images_to_try = [("original", img_bgr)]

        for conf in confs:
            for label, img in images_to_try:
                hands = self._make_hands(conf) if conf != 0.3 else self.hands
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                results = hands.process(img_rgb)
                if hands != self.hands:
                    hands.close()

                if results and results.multi_hand_landmarks:
                    return self._extract_finger_data(results, img_bgr.shape[:2])

            # 第一轮（原图）失败后，第二轮尝试 CLAHE 增强对比度
            if conf == 0.3:
                lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                l2 = clahe.apply(l)
                enhanced = cv2.merge([l2, a, b])
                enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                images_to_try.append(("clahe", enhanced_bgr))

        return None

    def _extract_finger_data(self, results, img_shape):
        """从 MediaPipe results 中提取手指方向数据"""
        hand_landmarks = results.multi_hand_landmarks[0]
        h, w = img_shape

        finger_data = {}
        for tip_idx, base_idx, name in zip(
                self.config.finger_tips, self.config.finger_bases, self.config.finger_names):
            tip = hand_landmarks.landmark[tip_idx]
            base = hand_landmarks.landmark[base_idx]

            tip_x, tip_y = int(tip.x * w), int(tip.y * h)
            base_x, base_y = int(base.x * w), int(base.y * h)

            dx = tip_x - base_x
            dy = tip_y - base_y
            #angle = np.degrees(np.arctan2(-dy, dx))
           # angle = lkGetP2Pangle(tip_x, tip_y,base_x, base_y)
            angle = lkGetP2Pangle(base_x, base_y,tip_x, tip_y)



            finger_data[name] = {
                'tip': (tip_x, tip_y),
                'base': (base_x, base_y),
                'vector': (dx, dy),
                'angle': angle,
            }

        # 质量检查：如果各手指方向向量长度平均值 < 20 像素，说明检测不可靠
        vec_lens = [np.sqrt(d['vector'][0]**2 + d['vector'][1]**2)
                    for d in finger_data.values()]
        avg_len = np.mean(vec_lens) if vec_lens else 0
        if avg_len < 20:
            return None

        return finger_data

    def detect_with_contour(self, hand_mask: np.ndarray, img_bgr: np.ndarray) -> Dict:
        """
        用凸缺陷 + 距离变换检测手指方向（MediaPipe失败时的备选方案）
        1. 凸缺陷找指谷（valley）
        2. 相邻谷点之间的凸包顶点 = 指尖
        3. 两个谷点的中点 = 指根
        4. 方向 = 指根 → 指尖
        """
        # 二值化
        bi = (hand_mask > 127).astype(np.uint8) * 255

        # 找轮廓
        contours, _ = cv2.findContours(bi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {}
        hand = max(contours, key=cv2.contourArea)

        # 掌心：腐蚀后找最大连通域质心（比距离变换更鲁棒）
        kernel_palm = np.ones((max(1, bi.shape[0]//30), max(1, bi.shape[1]//30)), np.uint8)
        palm_core = cv2.erode(bi, kernel_palm)
        if cv2.countNonZero(palm_core) > 0:
            M = cv2.moments(palm_core)
            pc_x = int(M['m10'] / M['m00'])
            pc_y = int(M['m01'] / M['m00'])
        else:
            # 备选：用轮廓质心
            M = cv2.moments(bi)
            pc_x = int(M['m10'] / M['m00'])
            pc_y = int(M['m01'] / M['m00'])

        # 凸缺陷
        hull_idx = cv2.convexHull(hand, returnPoints=False)
        if hull_idx.ndim > 1:
            hull_idx = hull_idx.ravel()
        defects = cv2.convexityDefects(hand, hull_idx)
        if defects is None:
            return {}

        # 收集深度足够的谷点
        valleys = []
        for i in range(defects.shape[0]):
            s, e, f, d = defects[i, 0]
            depth = d / 256
            if depth > 10:  # 深度阈值
                far = hand[f][0]
                valleys.append((int(far[0]), int(far[1])))
        if len(valleys) < 2:
            return {}

        # 按角度（相对掌心）排序 → 逆时针绕手掌一圈
        valleys.sort(key=lambda v: np.arctan2(v[1] - pc_y, v[0] - pc_x))

        # 凸包点（坐标）
        hull_pts = hand[hull_idx].reshape(-1, 2)
        nh = len(hull_pts)

        # 找到每个谷点在 hull_pts 中的最近索引
        valley_idx = []
        for vx, vy in valleys:
            dists = np.sqrt((hull_pts[:, 0] - vx)**2 + (hull_pts[:, 1] - vy)**2)
            valley_idx.append(int(np.argmin(dists)))

        # 对每对相邻谷点之间的凸包段，找到离掌心最远的点 = 指尖
        n = len(valleys)
        finger_data = {}
        used_tips = []

        for i in range(n):
            v1 = np.array(valleys[i])
            v2 = np.array(valleys[(i + 1) % n])

            # 两个谷点的中点 = 指根
            root = ((v1 + v2) / 2).astype(int)

            # 谷点 i 到谷点 i+1 之间的凸包片段
            s_idx = valley_idx[i]
            e_idx = valley_idx[(i + 1) % n]

            if s_idx <= e_idx:
                seg = hull_pts[s_idx:e_idx+1]
            else:
                seg = np.vstack([hull_pts[s_idx:], hull_pts[:e_idx+1]])

            if len(seg) < 2:
                continue

            # 这段中离掌心最远的点 = 指尖
            dists = np.sqrt((seg[:, 0] - pc_x)**2 + (seg[:, 1] - pc_y)**2)
            best_local = seg[np.argmax(dists)]
            tip_pt = tuple(best_local)

            if tip_pt not in used_tips:
                used_tips.append(tip_pt)
                dx = int(tip_pt[0] - root[0])
                dy = int(tip_pt[1] - root[1])
                length = np.sqrt(dx**2 + dy**2)
                if length > 25:
                    angle = np.degrees(np.arctan2(-dy, dx)) % 360
                    finger_data[f"finger_{len(finger_data)+1}"] = {
                        'tip': (int(tip_pt[0]), int(tip_pt[1])),
                        'base': (int(root[0]), int(root[1])),
                        'vector': (dx, dy),
                        'angle': float(angle),
                    }

        if len(finger_data) < 2:
            return {}

        # 按掌心距离取最远的5个
        sorted_by_dist = sorted(
            finger_data.items(),
            key=lambda kv: np.sqrt((kv[1]['tip'][0]-pc_x)**2 + (kv[1]['tip'][1]-pc_y)**2),
            reverse=True)
        top5 = dict(sorted_by_dist[:5])

        # 按 x 从左到右排序 → 拇指→小指
        sorted_items = sorted(top5.items(), key=lambda kv: kv[1]['tip'][0])
        finger_names = ["thumb", "index", "middle", "ring", "pinky"]
        result = {}
        for i, (old_key, data) in enumerate(sorted_items):
            name = finger_names[i] if i < 5 else old_key
            result[name] = data

        return result

    def detect_with_repaired_mask(self, img_bgr: np.ndarray, hand_mask: np.ndarray) -> Optional[Dict]:
        """
        用修复后的手部 mask 抠图（中性灰背景），再喂 MediaPipe 检测关键点
        对 mask 有断开的图先修复再抠图
        """
        h, w = img_bgr.shape[:2]

        bi = (hand_mask > 127).astype(np.uint8) * 255 if hand_mask is not None else None
        if bi is None or cv2.countNonZero(bi) == 0:
            return None

        # 检查是否有多段（断开）
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bi, connectivity=8)
        if num_labels > 2:
            areas = [(i, stats[i, cv2.CC_STAT_AREA]) for i in range(1, num_labels)]
            areas.sort(key=lambda x: x[1], reverse=True)
            palm_label = areas[0][0]
            palm = (labels == palm_label).astype(np.uint8) * 255
            from scipy.ndimage import convolve

            for idx in range(1, len(areas)):
                small = (labels == areas[idx][0]).astype(np.uint8) * 255
                skel = cv2.ximgproc.thinning(small, cv2.ximgproc.THINNING_ZHANGSUEN)
                skel_pts = np.column_stack(np.where(skel > 0))
                if len(skel_pts) < 5:
                    continue

                k = np.array([[1,1,1],[1,0,1],[1,1,1]], dtype=np.uint8)
                n = convolve((skel > 0).astype(float), k, mode='constant', cval=0)
                end_pts = np.column_stack(np.where((n == 1) & (skel > 0)))
                if len(end_pts) < 2:
                    continue

                py, px = np.where(palm > 0)
                pcx, pcy = px.mean(), py.mean()
                ep = min(end_pts, key=lambda p: (p[1]-pcx)**2 + (p[0]-pcy)**2)
                sc = np.mean(np.where(small > 0), axis=1).astype(int)
                dx = pcx - sc[1]; dy = pcy - sc[0]
                direction = np.array([dx, dy], dtype=float)
                norm = np.linalg.norm(direction)
                if norm < 1: continue
                direction /= norm

                x0, y0 = int(ep[1]), int(ep[0])
                prev_x, prev_y = x0, y0
                for step in range(1, 300):
                    x = int(x0 + direction[0] * step * 2)
                    y = int(y0 + direction[1] * step * 2)
                    if x < 0 or x >= w or y < 0 or y >= h: break
                    cv2.line(bi, (prev_x, prev_y), (x, y), 255, 3)
                    prev_x, prev_y = x, y
                    if palm[y, x] > 0: break

            bi = cv2.morphologyEx(bi, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

        # 中性灰背景抠图 → MediaPipe
        bg = np.full((h, w, 3), (128, 128, 128), dtype=np.uint8)
        cropped = np.where(cv2.merge([bi, bi, bi]) > 0, img_bgr, bg)
        return self.detect_with_mediapipe(cropped)

    def visualize_fingers(self, img_bgr: np.ndarray, finger_data: Dict, method: str = "mediapipe") -> np.ndarray:
        """可视化手指方向和关键点"""
        vis = img_bgr.copy()

        # 颜色映射
        colors = {
            'thumb': (255, 0, 0),    # 蓝色
            'index': (0, 255, 0),     # 绿色
            'middle': (0, 0, 255),    # 红色
            'ring': (255, 255, 0),    # 青色
            'pinky': (255, 0, 255),   # 紫色
        }

        for name, data in finger_data.items():
            # 获取基础名称（去掉 _0 等后缀）
            base_name = name.split('_')[0] if '_' in name else name
            color = colors.get(base_name, (255, 255, 255))

            tip = data['tip']
            base = data['base']

            # 画方向箭头
            cv2.arrowedLine(vis, base, tip, color, 2, tipLength=0.3)

            # 标记指尖
            cv2.circle(vis, tip, 5, color, -1)

            # 标记基部
            cv2.circle(vis, base, 3, color, -1)

            # 显示角度
            mid_x = (tip[0] + base[0]) // 2
            mid_y = (tip[1] + base[1]) // 2
            angle_text = f"{data['angle']:.0f}°"
            cv2.putText(vis, angle_text, (mid_x, mid_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # 添加方法标签
        method_text = {"mediapipe": "Method: MediaPipe", "sam3": "Method: SAM3", "contour": "Method: Contour", "mediapipe_repaired": "Method: MP+Repair"}.get(method, f"Method: {method}")
        cv2.putText(vis, method_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return vis

# ============================================================
# 主处理流程
# ============================================================
def process_single_image(img_path: str, config: Config, 
                         hand_segmentor: HandSegmentor,
                         nail_remover: NailRemover, 
                         direction_detector: FingerDirectionDetector):
    """处理单张图像"""
    img_name = os.path.splitext(os.path.basename(img_path))[0]
    # 从 s6_hands_natural 读取时去掉 _natural 后缀
    base_name = img_name.replace("_natural", "")
    print(f"\n处理: {base_name} (原图: {img_name})")

    # 1. 读取图像
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        print(f"  无法读取图像: {img_path}")
        return None

    results = {'image_name': base_name, 'success': False, 'method': None, 'finger_data': None}

    # 2. SAM3分割整个手部
    print("  步骤1: SAM3分割手部区域...")
    hand_mask = hand_segmentor.segment_hand(img_bgr)

    if hand_mask is None:
        print("  SAM3未能分割手部，尝试自动分割...")
        # 尝试自动分割（不带prompt）
        try:
            from ultralytics import SAM
            sam_model = SAM(config.sam3_checkpoint)
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            results_auto = sam_model.predict(img_rgb, conf=0.25, save=False, verbose=False)
            if results_auto and len(results_auto) > 0:
                r = results_auto[0]
                if hasattr(r, 'masks') and r.masks is not None:
                    # 找到最大的mask作为手部
                    best_area = 0
                    best_mask = None
                    for mt in r.masks.data.cpu().numpy():
                        m = (mt > 0.5).astype(np.uint8) * 255
                        m = cv2.resize(m, (img_bgr.shape[1], img_bgr.shape[0]))
                        area = cv2.countNonZero(m)
                        if area > best_area:
                            best_area = area
                            best_mask = m
                    hand_mask = best_mask
        except Exception as e:
            print(f"  自动分割也失败: {e}")
            return results

    if hand_mask is None:
        print("  无法分割手部区域")
        return results

    # 保存手部mask可视化
    mask_vis = cv2.cvtColor(hand_mask, cv2.COLOR_GRAY2BGR)
    mask_overlay = cv2.addWeighted(img_bgr, 0.7, mask_vis, 0.3, 0)
    cv2.imwrite(os.path.join(config.output_dir, f"{base_name}_hand_mask.png"), mask_overlay)
    print(f"  手部mask已保存 (面积: {cv2.countNonZero(hand_mask)} 像素)")

    # 3. 跳过美甲去除 — 输入已用 SD Inpainting 处理为自然手
    img_hand = cv2.bitwise_and(img_bgr, img_bgr, mask=hand_mask)

    # 4. 检测手指方向 — 多策略
    print("  步骤3: 检测手指方向...")
    
    # 策略A: 自然手图 + MediaPipe
    finger_data = direction_detector.detect_with_mediapipe(img_hand)
    method = "mediapipe"
    source = "natural"

    # 策略B: 如果自然手图失败，试原 hands/ 图（美甲有时提供视觉参照）
    if finger_data is None:
        orig_path = os.path.join("./hands", f"{base_name}.png")
        if os.path.exists(orig_path):
            print("  自然图 MediaPipe 失败，尝试原图...")
            orig_img = cv2.imread(orig_path)
            if orig_img is not None:
                finger_data = direction_detector.detect_with_mediapipe(orig_img)
                if finger_data:
                    source = "original"
                    img_hand = orig_img

    # 策略C: mask修复 + 中性灰背景抠图 → MediaPipe（终极方案）
    if finger_data is None:
        print("  尝试 mask 修复 + 抠图重测 MediaPipe...")
        finger_data = direction_detector.detect_with_repaired_mask(img_bgr, hand_mask)
        method = "mediapipe_repaired"

    if not finger_data:
        print("  无法检测手指方向")
        return results

    # 5. 可视化结果
    vis_src = img_bgr if method == "mediapipe_repaired" else img_hand
    vis_img = direction_detector.visualize_fingers(vis_src, finger_data, method)
    cv2.imwrite(os.path.join(config.output_dir, f"{base_name}_finger_direction.png"), vis_img)
    print(f"  手指方向可视化已保存")

    # 6. 保存方向数据到CSV
    results['success'] = True
    results['method'] = method
    results['finger_data'] = finger_data

    print(f"  成功检测 {len(finger_data)} 个手指方向 (方法: {method}, 源: {source})")
    for name, data in finger_data.items():
        print(f"    {name}: 角度={data['angle']:.1f}°, 向量=({data['vector'][0]},{data['vector'][1]})")

    # 7. 保存方向数据为 JSON（供 S8 visualizeDirections 使用）
    h, w = img_bgr.shape[:2]
    json_data = {
        "image": f"{img_name}.png",
        "size": [w, h],
        "fingers": {},
        "method": method,
    }
    for fname, fdata in finger_data.items():
        tip_x, tip_y = fdata["tip"]
        base_x, base_y = fdata["base"]
        dx, dy = fdata["vector"]
        json_data["fingers"][fname] = {
            "tip": {"x": tip_x, "y": tip_y},
            "dip": {"x": base_x, "y": base_y},
            "direction": {"dx": dx, "dy": dy},
        }
    os.makedirs(config.json_dir, exist_ok=True)
    json_path = os.path.join(config.json_dir, f"{base_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"  → JSON: {json_path}")

    # 8. 保存角度 TXT（大拇指→小拇指，每行一个角度，0-360°）
    order = ["thumb", "index", "middle", "ring", "pinky"]
    angles = []
    for fn in order:
        if fn in finger_data:
            angle = round(finger_data[fn]['angle'], 1)
            angles.append(str(angle))
    if angles:
        txt_path = os.path.join(config.output_dir, f"{img_name}_angle.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(angles) + "\n")
        print(f"  → TXT: {txt_path}")

    return results

def main():
    parser = argparse.ArgumentParser(description="手指方向检测")
    parser.add_argument("--single", type=str, help="处理单张图像 (文件名不含扩展名)")
    args = parser.parse_args()

    config = Config()
    os.makedirs(config.output_dir, exist_ok=True)

    print("=" * 60)
    print("手指方向检测 pipeline")
    print("=" * 60)

    # 初始化各模块
    print("\n初始化模块...")
    hand_segmentor = HandSegmentor(config)
    nail_remover = NailRemover(config)
    direction_detector = FingerDirectionDetector(config)

    # 找到所有图像
    if args.single:
        img_files = [os.path.join(config.input_dir, f"{args.single}.png")]
    else:
        img_files = sorted(glob_mod.glob(os.path.join(config.input_dir, "*.png")))

    print(f"\n找到 {len(img_files)} 张图像")

    # 处理每张图像
    all_results = []
    for img_path in img_files:
        result = process_single_image(img_path, config, hand_segmentor, nail_remover, direction_detector)
        if result:
            all_results.append(result)

    # 保存汇总报告
    report_path = os.path.join(config.output_dir, "finger_direction_report.csv")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("image_name,success,method,num_fingers,details\n")
        for r in all_results:
            if r['success']:
                details = "; ".join([
                    f"{name}:angle={data['angle']:.1f}°"
                    for name, data in r['finger_data'].items()
                ])
                f.write(f"{r['image_name']},True,{r['method']},{len(r['finger_data'])},{details}\n")
            else:
                f.write(f"{r['image_name']},False,,,未检测到手指方向\n")

    print(f"\n汇总报告已保存: {report_path}")
    print("=" * 60)
    print("处理完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
