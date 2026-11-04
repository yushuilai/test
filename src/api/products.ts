export interface Product {
  id: number;
  name: string;
  price: number;
  stock: number;
}

export interface ProductSearchResult {
  items: Product[];
  total: number;
}

export interface SearchOptions {
  limit?: unknown;
  offset?: unknown;
}

export const DEFAULT_LIMIT = 20;
export const MAX_LIMIT = 100;
export const DEFAULT_OFFSET = 0;

/**
 * 归一化 limit：缺失/非法值（非数字、负数、0、浮点数）回落默认 20；大于 100 的正整数钳制为 100。
 * 与 docs/products-search-api.md 的契约保持一致。
 */
export function normalizeLimit(raw: unknown): number {
  const num = toNumber(raw);
  if (num === null || !Number.isInteger(num) || num <= 0) {
    return DEFAULT_LIMIT;
  }
  return num > MAX_LIMIT ? MAX_LIMIT : num;
}

/**
 * 归一化 offset：缺失/非法值（非数字、负数、浮点数）回落 0；合法非负整数按原值。
 */
export function normalizeOffset(raw: unknown): number {
  const num = toNumber(raw);
  if (num === null || !Number.isInteger(num) || num < 0) {
    return DEFAULT_OFFSET;
  }
  return num;
}

/** 价格展示：保留两位小数（如 199 -> "199.00"）。 */
export function formatPrice(price: number): string {
  return price.toFixed(2);
}

/**
 * 调用 GET /products/search（后端预留接口）。
 * keyword 为空时由后端返回 400，这里统一抛出「keyword 不能为空」。
 */
export async function searchProducts(
  keyword: string,
  options: SearchOptions = {},
  fetchFn: typeof fetch = fetch,
): Promise<ProductSearchResult> {
  const limit = normalizeLimit(options.limit);
  const offset = normalizeOffset(options.offset);
  const params = new URLSearchParams({
    keyword,
    limit: String(limit),
    offset: String(offset),
  });
  const res = await fetchFn(`/products/search?${params.toString()}`);

  if (res.status === 400) {
    throw new Error('keyword 不能为空');
  }
  if (!res.ok) {
    throw new Error(`请求失败：HTTP ${res.status}`);
  }
  return (await res.json()) as ProductSearchResult;
}

function toNumber(raw: unknown): number | null {
  if (raw === undefined || raw === null) {
    return null;
  }
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (trimmed === '') {
      return null;
    }
    const n = Number(trimmed);
    return Number.isNaN(n) ? null : n;
  }
  if (typeof raw === 'number') {
    return Number.isNaN(raw) ? null : raw;
  }
  return null;
}
