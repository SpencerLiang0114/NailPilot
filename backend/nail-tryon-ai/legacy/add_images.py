import json

# 读取商品库
with open("products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

updated = 0

for p in products:

    # 已有 image 的跳过
    if "image" in p and p["image"]:
        continue

    # 没有 image 的补充
    p["image"] = f"/static/images/{p['id']}.jpg"

    updated += 1

# 保存
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(
        products,
        f,
        ensure_ascii=False,
        indent=2
    )

print("补充完成")
print("新增 image 数量：", updated)
