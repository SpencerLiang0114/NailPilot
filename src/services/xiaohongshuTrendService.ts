import "server-only";
import { createHash } from "crypto";
import type { NormalizedXhsTrend } from "@/types/manicureHotspots";

type JsonRecord = Record<string, unknown>;

const DEFAULT_XHS_API_BASE_URL = "";
const DEFAULT_XHS_HOT_SEARCH_ENDPOINT = "";
const DEFAULT_XHS_KEYWORD_SEARCH_ENDPOINT = "";

interface XhsApiConfig {
  baseUrl: string;
  token: string;
  hotSearchEndpoint: string;
  keywordSearchEndpoint?: string;
  method: "GET" | "POST";
  authHeader: string;
  authScheme?: string;
  extraHeaders: Record<string, string>;
  hotSearchPageSize: string;
}

export class XhsApiConfigMissingError extends Error {
  code = "XHS_API_CONFIG_MISSING";

  constructor(message: string) {
    super(message);
    this.name = "XhsApiConfigMissingError";
  }
}

export class XhsApiRequestError extends Error {
  code = "XHS_API_REQUEST_FAILED";

  constructor(message: string) {
    super(message);
    this.name = "XhsApiRequestError";
  }
}

export async function fetchXhsHotTrends(): Promise<NormalizedXhsTrend[]> {
  const config = getXhsApiConfig();
  const payload = await requestXhsApi(config, config.hotSearchEndpoint, {
    num: config.hotSearchPageSize
  });

  return normalizeXhsResponse(payload);
}

export async function fetchXhsKeywordTrends(
  keyword: string
): Promise<NormalizedXhsTrend[]> {
  const config = getXhsApiConfig();

  if (!config.keywordSearchEndpoint) {
    return [];
  }

  const payload = await requestXhsApi(config, config.keywordSearchEndpoint, {
    keyword,
    page: "1",
    sort_type: "popularity_descending",
    note_type: "不限",
    time_filter: "一周内",
    source: "explore_feed",
    ai_mode: "0"
  });

  return normalizeXhsResponse(payload);
}

function getXhsApiConfig(): XhsApiConfig {
  const baseUrl =
    process.env.XHS_API_BASE_URL?.trim() || DEFAULT_XHS_API_BASE_URL;
  const token = process.env.XHS_API_TOKEN?.trim();
  const hotSearchEndpoint =
    process.env.XHS_HOT_SEARCH_ENDPOINT?.trim() ||
    DEFAULT_XHS_HOT_SEARCH_ENDPOINT;

  if (!baseUrl || !token || !hotSearchEndpoint) {
    throw new XhsApiConfigMissingError(
      "Missing Xiaohongshu API configuration. Please configure XHS_API_BASE_URL, XHS_API_TOKEN, and XHS_HOT_SEARCH_ENDPOINT."
    );
  }

  return {
    baseUrl,
    token,
    hotSearchEndpoint,
    keywordSearchEndpoint:
      process.env.XHS_KEYWORD_SEARCH_ENDPOINT?.trim() ||
      DEFAULT_XHS_KEYWORD_SEARCH_ENDPOINT,
    method: parseMethod(process.env.XHS_API_METHOD),
    authHeader: process.env.XHS_API_AUTH_HEADER?.trim() || "X-API-Key",
    authScheme: parseAuthScheme(process.env.XHS_API_AUTH_SCHEME),
    extraHeaders: parseExtraHeaders(process.env.XHS_API_EXTRA_HEADERS),
    hotSearchPageSize: positiveIntegerString(
      process.env.XHS_HOT_SEARCH_PAGE_SIZE,
      "50"
    )
  };
}

async function requestXhsApi(
  config: XhsApiConfig,
  endpoint: string,
  query?: Record<string, string>
): Promise<unknown> {
  const url = buildUrl(config.baseUrl, endpoint);
  const headers = new Headers({
    Accept: "application/json",
    ...config.extraHeaders
  });
  headers.set(
    config.authHeader,
    config.authScheme
      ? `${config.authScheme} ${config.token}`
      : config.token
  );

  const init: RequestInit = {
    method: config.method,
    headers,
    cache: "no-store"
  };

  if (config.method === "GET") {
    Object.entries(query ?? {}).forEach(([key, value]) => {
      url.searchParams.set(key, value);
    });
  } else if (query) {
    headers.set("Content-Type", "application/json");
    init.body = JSON.stringify(query);
  }

  const response = await fetch(url, init);

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new XhsApiRequestError(
      `Xiaohongshu API request failed with ${response.status} ${response.statusText}${body ? `: ${body.slice(0, 240)}` : ""}`
    );
  }

  return response.json();
}

function normalizeXhsResponse(payload: unknown): NormalizedXhsTrend[] {
  return collectCandidateItems(payload)
    .map((item, index) => normalizeXhsTrend(item, index))
    .filter((item): item is NormalizedXhsTrend => Boolean(item));
}

function normalizeXhsTrend(
  item: unknown,
  index: number
): NormalizedXhsTrend | null {
  const rawRecord = asRecord(item);
  if (!rawRecord) {
    return null;
  }
  const record = flattenKnownXhsRecord(rawRecord);

  const keyword =
    firstString(record, [
      "keyword",
      "word",
      "query",
      "name",
      "title",
      "display_title",
      "note_card_title",
      "noteTitle"
    ]) || "";
  const title =
    firstString(record, [
      "title",
      "display_title",
      "note_card_title",
      "noteTitle",
      "note_title",
      "desc",
      "name",
      "keyword",
      "word",
      "content"
    ]) || keyword;

  if (!title && !keyword) {
    return null;
  }

  const tags = uniqueStrings([
    ...extractTags(record.tags),
    ...extractTags(record.hashtags),
    ...extractTags(record.topics),
    ...extractTags(record.topic),
    ...extractTags(record.category),
    ...extractTags(record.categories),
    ...extractTags(record.tag_list),
    ...extractTags(record.tagList)
  ]);

  const id =
    firstString(record, [
      "id",
      "noteId",
      "note_id",
      "itemId",
      "item_id",
      "noteIdStr",
      "note_id_str"
    ]) ||
    createHash("sha1")
      .update(JSON.stringify({ title, keyword, index }))
      .digest("hex")
      .slice(0, 16);

  return {
    id,
    keyword: keyword || title,
    title,
    description: firstString(record, [
      "description",
      "desc",
      "summary",
      "content",
      "noteContent",
      "note_content",
      "noteDesc",
      "note_desc"
    ]),
    heatScore: firstNumber(record, [
      "heatScore",
      "hotScore",
      "hot_score",
      "heat",
      "hotValue",
      "hot_value",
      "popularity",
      "hot",
      "viewCount",
      "view_count",
      "score"
    ]),
    rank: firstNumber(record, ["rank", "ranking", "index", "position", "order"]),
    sourceUrl: firstString(record, [
      "sourceUrl",
      "source_url",
      "url",
      "link",
      "shareUrl",
      "share_url",
      "webUrl",
      "web_url",
      "noteUrl",
      "note_url"
    ]),
    tags,
    imageUrls: extractImageUrls(record),
    publishTime: normalizeTime(
      record.publishTime ??
        record.publish_time ??
        record.createTime ??
        record.create_time ??
        record.createdAt ??
        record.created_at ??
        record.time ??
        record.timestamp
    ),
    likeCount: firstNumber(record, [
      "likeCount",
      "like_count",
      "likes",
      "liked_count",
      "likedCount"
    ]),
    collectCount: firstNumber(record, [
      "collectCount",
      "collect_count",
      "favorites",
      "favoriteCount",
      "favorite_count",
      "collected_count",
      "collectedCount"
    ]),
    commentCount: firstNumber(record, [
      "commentCount",
      "comment_count",
      "comments",
      "commented_count",
      "commentedCount"
    ]),
    shareCount: firstNumber(record, [
      "shareCount",
      "share_count",
      "shares",
      "shared_count",
      "sharedCount"
    ]),
    raw: item
  };
}

function flattenKnownXhsRecord(record: JsonRecord): JsonRecord {
  const nestedRecords = [
    record.note,
    record.note_card,
    record.noteCard,
    record.card,
    record.item,
    record.target,
    record.inspiration,
    record.data
  ]
    .map(asRecord)
    .filter((value): value is JsonRecord => Boolean(value));
  const interactRecords = [record.interact_info, record.interactInfo];

  for (const nestedRecord of nestedRecords) {
    interactRecords.push(
      nestedRecord.interact_info,
      nestedRecord.interactInfo,
      nestedRecord.statistics,
      nestedRecord.stats
    );
  }

  return {
    ...nestedRecords.reduce<JsonRecord>(
      (merged, nestedRecord) => ({ ...merged, ...nestedRecord }),
      {}
    ),
    ...interactRecords
      .map(asRecord)
      .filter((value): value is JsonRecord => Boolean(value))
      .reduce<JsonRecord>(
        (merged, nestedRecord) => ({ ...merged, ...nestedRecord }),
        {}
      ),
    ...record
  };
}

function collectCandidateItems(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  const record = asRecord(payload);
  if (!record) {
    return [];
  }

  const likelyArrayKeys = [
    "data",
    "items",
    "list",
    "result",
    "records",
    "rows",
    "trends",
    "hotSearches",
    "hot_searches",
    "notes",
    "feeds",
    "feed",
    "results",
    "inspirations",
    "note_list",
    "noteList",
    "items_list",
    "itemsList"
  ];

  for (const key of likelyArrayKeys) {
    const value = record[key];
    if (Array.isArray(value)) {
      return value;
    }
    const nested = asRecord(value);
    if (nested) {
      const nestedItems = collectCandidateItems(nested);
      if (nestedItems.length > 0) {
        return nestedItems;
      }
    }
  }

  if (firstString(record, ["title", "keyword", "word", "name"])) {
    return [record];
  }

  return [];
}

function buildUrl(baseUrl: string, endpoint: string): URL {
  if (/^https?:\/\//i.test(endpoint)) {
    return new URL(endpoint);
  }

  return new URL(endpoint.replace(/^\//, ""), `${baseUrl.replace(/\/$/, "")}/`);
}

function parseMethod(method: string | undefined): "GET" | "POST" {
  return method?.toUpperCase() === "POST" ? "POST" : "GET";
}

function parseAuthScheme(value: string | undefined): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const normalized = value.trim();

  return normalized && normalized.toLowerCase() !== "none"
    ? normalized
    : undefined;
}

function positiveIntegerString(value: string | undefined, fallback: string): string {
  const parsed = Number(value);

  return Number.isInteger(parsed) && parsed > 0 ? String(parsed) : fallback;
}

function parseExtraHeaders(value: string | undefined): Record<string, string> {
  if (!value) {
    return {};
  }

  try {
    const parsed = JSON.parse(value) as unknown;
    const parsedRecord = asRecord(parsed);
    if (!parsedRecord) {
      return {};
    }

    return Object.fromEntries(
      Object.entries(parsedRecord).filter(
        (entry): entry is [string, string] => typeof entry[1] === "string"
      )
    );
  } catch {
    return {};
  }
}

function extractTags(value: unknown): string[] {
  if (!value) {
    return [];
  }
  if (typeof value === "string") {
    return [value];
  }
  if (Array.isArray(value)) {
    return value
      .flatMap((entry) => {
        if (typeof entry === "string") {
          return entry;
        }
        const record = asRecord(entry);
        return record
          ? firstString(record, ["name", "title", "tag", "keyword"]) ?? []
          : [];
      })
      .filter(Boolean);
  }
  const record = asRecord(value);
  return record
    ? [firstString(record, ["name", "title", "tag"])].filter(isString)
    : [];
}

function extractImageUrls(record: JsonRecord): string[] | undefined {
  const values = [
    record.imageUrls,
    record.image_urls,
    record.images,
    record.pictures,
    record.cover,
    record.image
  ];

  const urls = values.flatMap((value) => collectUrls(value));

  return urls.length > 0 ? uniqueStrings(urls) : undefined;
}

function collectUrls(value: unknown): string[] {
  if (!value) {
    return [];
  }
  if (typeof value === "string" && /^https?:\/\//i.test(value)) {
    return [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap((entry) => collectUrls(entry));
  }
  const record = asRecord(value);
  if (!record) {
    return [];
  }

  return ["url", "src", "originUrl", "origin_url", "thumbnail", "thumb"].flatMap(
    (key) => collectUrls(record[key])
  );
}

function normalizeTime(value: unknown): string | undefined {
  if (typeof value === "string") {
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? value : new Date(parsed).toISOString();
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    const milliseconds = value > 10_000_000_000 ? value : value * 1000;
    return new Date(milliseconds).toISOString();
  }

  return undefined;
}

function firstString(record: JsonRecord, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      return String(value);
    }
  }

  return undefined;
}

function firstNumber(record: JsonRecord, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string") {
      const normalized = Number(value.replace(/[,\s]/g, ""));
      if (Number.isFinite(normalized)) {
        return normalized;
      }
    }
  }

  return undefined;
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(
    new Set(values.map((value) => value.trim()).filter((value) => value.length > 0))
  );
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function asRecord(value: unknown): JsonRecord | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : null;
}
