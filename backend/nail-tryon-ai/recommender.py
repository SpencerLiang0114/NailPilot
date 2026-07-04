import json


# ==========================
# 读取商品库
# ==========================
def load_products(file_path="products.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================
# 标签重合度
# ==========================
def overlap_score(tags1, tags2):

    if not tags1 or not tags2:
        return 0

    overlap = len(set(tags1) & set(tags2))
    union = len(set(tags1) | set(tags2))

    return overlap / union


# ==========================
# 推荐理由生成
# ==========================
def generate_reason(current_product, candidate):

    reasons = []

    if set(current_product["color"]) & set(candidate["color"]):
        reasons.append("同色系")

    if set(current_product["style"]) & set(candidate["style"]):
        reasons.append("同风格")

    if set(current_product["shape"]) & set(candidate["shape"]):
        reasons.append("相似甲型")

    if candidate.get("trend_score", 0) >= 80:
        reasons.append("热门趋势款")

    if not reasons:
        return "与你当前试戴款风格接近"

    return "、".join(reasons)


# ==========================
# 单个商品评分
# ==========================
def calculate_score(current_product, candidate):

    color_score = overlap_score(
        current_product["color"],
        candidate["color"]
    ) * 35

    style_score = overlap_score(
        current_product["style"],
        candidate["style"]
    ) * 30

    shape_score = overlap_score(
        current_product["shape"],
        candidate["shape"]
    ) * 15

    decoration_score = overlap_score(
        current_product["decoration"],
        candidate["decoration"]
    ) * 10

    texture_score = overlap_score(
        current_product["texture"],
        candidate["texture"]
    ) * 5

    trend_score = candidate.get(
        "trend_score", 50
    ) * 0.03

    popularity_score = candidate.get(
        "popularity_score", 50
    ) * 0.02

    total_score = (
        color_score +
        style_score +
        shape_score +
        decoration_score +
        texture_score +
        trend_score +
        popularity_score
    )

    return round(total_score, 2)


# ==========================
# 主推荐函数
# ==========================
def recommend_products(
    current_product_id,
    products,
    top_k=8
):

    print("=" * 50)
    print("收到的ID:", repr(current_product_id))
    print("商品总数:", len(products))

    print("前10个商品ID:")

    for p in products[:10]:
        print(repr(p["id"]))

    current_product = None

    for p in products:

        if str(p["id"]).strip() == str(current_product_id).strip():

            current_product = p

            print("找到商品:", p["name"])

            break

    if current_product is None:

        print("没有找到匹配商品")

        raise ValueError("当前商品不存在")

    results = []

    for candidate in products:

        if candidate["id"] == current_product_id:
            continue

        score = calculate_score(
            current_product,
            candidate
        )

        reason = generate_reason(
            current_product,
            candidate
        )

        results.append({
            "id": candidate["id"],
            "name": candidate["name"],
            "image": candidate["image"],
            "score": score,
            "reason": reason
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]


# ==========================
# 测试运行
# ==========================
if __name__ == "__main__":

    products = load_products("products.json")

    # 模拟用户当前试戴商品
    current_product_id = "nail_003"

    recommendations = recommend_products(
        current_product_id=current_product_id,
        products=products,
        top_k=8
    )

    print("\n推荐结果：\n")

    for item in recommendations:
        print(
            f"{item['name']} "
            f"| Score={item['score']} "
            f"| {item['reason']}"
        )
