"""visualizeDirections.py — 在手图上画出指甲方向箭头"""
import os, json, cv2, numpy as np
from pathlib import Path

#SRC  = r"E:\meijia\hands_natural"
SRC  = "./s6_hands_natural"
JSON = "./s7_hands_direction"
OUT  = "./s8_hands_direction_vis"

Path(OUT).mkdir(parents=True, exist_ok=True)

# 五指颜色
COLORS = {"thumb":(0,255,0), "index":(255,0,0), "middle":(0,0,255),
          "ring":(255,0,255), "pinky":(0,255,255)}

for jf in sorted(Path(JSON).glob("*.json")):
    with open(jf) as f: data = json.load(f)
    img_name = data["image"]
    img_path = Path(SRC) / img_name
    if not img_path.exists():
        print(f"  SKIP {img_name} - 无原图")
        continue

    img = cv2.imread(str(img_path))
    for finger, info in data["fingers"].items():
        tip = info["tip"]
        dip = info["dip"]
        dx = info.get("direction", {}).get("dx",
             tip["x"] - dip["x"])
        dy = info.get("direction", {}).get("dy",
             tip["y"] - dip["y"])
        color = COLORS.get(finger, (255,255,255))

        pt_tip = (int(tip["x"]), int(tip["y"]))
        pt_dip = (int(dip["x"]), int(dip["y"]))
        # 延伸方向线
        arrow_len = np.sqrt(dx**2 + dy**2)
        if arrow_len > 0:
            ext_x = int(pt_tip[0] + dx/arrow_len * 60)
            ext_y = int(pt_tip[1] + dy/arrow_len * 60)
        else:
            ext_x, ext_y = pt_tip

        # 画箭头
        cv2.arrowedLine(img, pt_dip, (ext_x, ext_y), color, 2, tipLength=0.3)
        cv2.circle(img, pt_tip, 6, color, -1)
        cv2.circle(img, pt_dip, 4, color, -1)
        cv2.putText(img, finger[:1].upper(), (pt_tip[0]+8, pt_tip[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    out_path = Path(OUT) / img_name
    cv2.imwrite(str(out_path), img)
    print(f"  {img_name}")

print(f"\nDone → {OUT}")
