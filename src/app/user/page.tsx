"use client";

/* eslint-disable @next/next/no-img-element */
import Link from "next/link";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Check,
  ImageIcon,
  Loader2,
  Sparkles,
  Upload,
  WandSparkles
} from "lucide-react";

type NailProduct = {
  id: string;
  name: string;
  image: string;
  reason?: string;
  score?: number;
};

type ProductsResponse = {
  success: boolean;
  products?: NailProduct[];
  error?: string;
};

type RecommendationsResponse = {
  success: boolean;
  recommendations?: NailProduct[];
  error?: string;
};

export default function UserTryOnPage() {
  const [allNails, setAllNails] = useState<NailProduct[]>([]);
  const [displayedNails, setDisplayedNails] = useState<NailProduct[]>([]);
  const [selectedNailId, setSelectedNailId] = useState("");
  const [handFile, setHandFile] = useState<File | null>(null);
  const [handPreviewUrl, setHandPreviewUrl] = useState("");
  const [resultImageUrl, setResultImageUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [error, setError] = useState("");
  const [recommendationNotice, setRecommendationNotice] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProducts() {
      setLoadingProducts(true);
      setError("");

      try {
        const response = await fetch("/api/user/initial-products", { cache: "no-store" });
        const data = (await response.json()) as ProductsResponse;

        if (!response.ok || !data.success || !data.products) {
          throw new Error(data.error ?? "美甲款式加载失败");
        }

        if (active) {
          setAllNails(data.products);
          setDisplayedNails(data.products);
        }
      } catch (loadError) {
        if (active) {
          const message = loadError instanceof Error ? loadError.message : "美甲款式加载失败";
          setError(message);
        }
      } finally {
        if (active) {
          setLoadingProducts(false);
        }
      }
    }

    loadProducts();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (handPreviewUrl) {
        URL.revokeObjectURL(handPreviewUrl);
      }
    };
  }, [handPreviewUrl]);

  useEffect(() => {
    return () => {
      if (resultImageUrl) {
        URL.revokeObjectURL(resultImageUrl);
      }
    };
  }, [resultImageUrl]);

  const selectedNail = useMemo(
    () => allNails.find((nail) => nail.id === selectedNailId),
    [allNails, selectedNailId]
  );

  function handleHandFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setHandFile(file);
    setError("");

    if (handPreviewUrl) {
      URL.revokeObjectURL(handPreviewUrl);
    }

    setHandPreviewUrl(file ? URL.createObjectURL(file) : "");
  }

  async function handleTryOn() {
    if (!selectedNailId || !handFile) {
      setError("请先选择一款美甲并上传手部照片。");
      return;
    }

    setLoading(true);
    setError("");
    setRecommendationNotice("");

    const formData = new FormData();
    formData.append("product_id", selectedNailId);
    formData.append("hand_file", handFile);

    try {
      const tryOnResponse = await fetch("/api/user/nail-tryon", {
        method: "POST",
        body: formData
      });

      const contentType = tryOnResponse.headers.get("content-type") ?? "";
      if (!tryOnResponse.ok || !contentType.startsWith("image/")) {
        const detail = contentType.includes("application/json")
          ? ((await tryOnResponse.json()) as { error?: string }).error
          : await tryOnResponse.text();
        throw new Error(detail || "试戴生成失败");
      }

      const resultBlob = await tryOnResponse.blob();
      if (resultImageUrl) {
        URL.revokeObjectURL(resultImageUrl);
      }
      setResultImageUrl(URL.createObjectURL(resultBlob));

      const recResponse = await fetch("/api/user/recommendations", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({
          current_product_id: selectedNailId,
          top_k: 8
        })
      });
      const recData = (await recResponse.json()) as RecommendationsResponse;

      if (!recResponse.ok || !recData.success || !recData.recommendations?.length) {
        setRecommendationNotice("推荐加载失败，请稍后重试。");
        return;
      }

      setDisplayedNails(recData.recommendations);
      setRecommendationNotice("已根据当前试戴款更新 8 款个性化推荐。");
    } catch (tryOnError) {
      const message = tryOnError instanceof Error ? tryOnError.message : "试戴生成失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="user-tryon-shell">
      <nav className="user-tryon-nav" aria-label="User side navigation">
        <Link className="user-back-link" href="/">
          <ArrowLeft size={16} />
          Back to Portal
        </Link>
        <span>MEITUAN VIRTUAL NAILART SALON</span>
      </nav>

      <header className="user-tryon-header">
        <p className="portal-badge">User Side</p>
        <h1>AI 美甲试戴沙龙</h1>
        <div className="user-tip">
          <Sparkles size={16} />
          挑选心仪美甲并上传手部照片，AI 将生成试戴效果并推荐同风格款式
        </div>
      </header>

      <section className="tryon-workspace" aria-label="AI manicure try-on workflow">
        <div className="tryon-left-panel">
          <section className="tryon-step" aria-labelledby="nail-picker-title">
            <div className="tryon-step-heading">
              <span aria-hidden="true" />
              <h2 id="nail-picker-title">
                STEP 1: 左右滑动选择美甲款式（共 {displayedNails.length || allNails.length} 款）
              </h2>
            </div>

            <div className="nail-carousel" aria-busy={loadingProducts}>
              {loadingProducts ? (
                <div className="nail-carousel-empty">
                  <Loader2 size={24} className="spin" />
                  正在加载美甲款式
                </div>
              ) : (
                displayedNails.map((nail) => {
                  const selected = nail.id === selectedNailId;
                  return (
                    <button
                      className={`nail-option${selected ? " nail-option-selected" : ""}`}
                      key={nail.id}
                      type="button"
                      onClick={() => {
                        setSelectedNailId(nail.id);
                        setError("");
                      }}
                      aria-pressed={selected}
                    >
                      <span className="nail-option-image">
                        <img src={nail.image} alt={nail.name} />
                        {selected ? (
                          <span className="nail-check" aria-hidden="true">
                            <Check size={14} />
                          </span>
                        ) : null}
                      </span>
                      <span className="nail-option-name">{nail.name}</span>
                      {nail.reason ? <span className="nail-option-reason">{nail.reason}</span> : null}
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <section className="tryon-step" aria-labelledby="hand-upload-title">
            <div className="tryon-step-heading">
              <span aria-hidden="true" />
              <h2 id="hand-upload-title">STEP 2: 上传您的手部照片</h2>
            </div>

            <div className="hand-upload-grid">
              <label className="hand-upload-box">
                <input accept="image/*" type="file" onChange={handleHandFileChange} />
                {handPreviewUrl ? (
                  <img src={handPreviewUrl} alt="已上传的手部照片预览" />
                ) : (
                  <span>
                    <Upload size={34} />
                    <strong>将图像拖放到此处</strong>
                    <em>或点击上传</em>
                  </span>
                )}
              </label>

              <div className="gesture-card">
                <img className="gesture-hand" src="/handpose-a.jpg" alt="" aria-hidden="true" />
                <strong>手势 A</strong>
                <span>手心朝上</span>
              </div>

              <div className="gesture-card">
                <img className="gesture-hand" src="/handpose-b.jpg" alt="" aria-hidden="true" />
                <strong>手势 B</strong>
                <span>手背朝上</span>
              </div>
            </div>
          </section>

          <button
            className="tryon-action"
            type="button"
            onClick={handleTryOn}
            disabled={loading || loadingProducts}
          >
            {loading ? <Loader2 size={20} className="spin" /> : <WandSparkles size={20} />}
            {loading ? "AI 正在生成试戴效果" : "开始试戴 & 激发 AI 个性化推荐"}
          </button>

          {error ? <p className="tryon-message tryon-message-error">{error}</p> : null}
          {recommendationNotice ? (
            <p className="tryon-message tryon-message-success">{recommendationNotice}</p>
          ) : null}
        </div>

        <aside className="tryon-result-panel" aria-labelledby="tryon-result-title">
          <div className="tryon-step-heading">
            <span aria-hidden="true" />
            <h2 id="tryon-result-title">STEP 3: 试戴视觉效果</h2>
          </div>

          <div className="result-preview">
            <div className="result-preview-label">
              <ImageIcon size={15} />
              试戴预览图
            </div>
            {resultImageUrl ? (
              <img src={resultImageUrl} alt="AI 美甲试戴效果" />
            ) : (
              <div className="result-placeholder">
                <ImageIcon size={42} />
                <span>生成后的试戴图会显示在这里</span>
              </div>
            )}
            <div className="meituan-watermark">美团 Meituan</div>
          </div>

          <div className="selected-summary">
            <span>当前款式</span>
            <strong>{selectedNail ? selectedNail.name : "尚未选择"}</strong>
          </div>
        </aside>
      </section>
    </main>
  );
}
