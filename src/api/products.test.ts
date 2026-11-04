import { describe, it, expect, vi } from 'vitest';
import {
  normalizeLimit,
  normalizeOffset,
  formatPrice,
  searchProducts,
  DEFAULT_LIMIT,
  MAX_LIMIT,
} from './products';

describe('normalizeLimit', () => {
  it('缺失/空/非法值回落默认 20', () => {
    expect(normalizeLimit(undefined)).toBe(DEFAULT_LIMIT);
    expect(normalizeLimit(null)).toBe(DEFAULT_LIMIT);
    expect(normalizeLimit('')).toBe(DEFAULT_LIMIT);
    expect(normalizeLimit('abc')).toBe(DEFAULT_LIMIT);
    expect(normalizeLimit('-1')).toBe(DEFAULT_LIMIT);
    expect(normalizeLimit('0')).toBe(DEFAULT_LIMIT);
    expect(normalizeLimit('1.5')).toBe(DEFAULT_LIMIT);
  });

  it('大于 100 的正整数钳制为 100', () => {
    expect(normalizeLimit('999')).toBe(MAX_LIMIT);
    expect(normalizeLimit(101)).toBe(MAX_LIMIT);
  });

  it('1~100 的正整数按原值', () => {
    expect(normalizeLimit('20')).toBe(20);
    expect(normalizeLimit(1)).toBe(1);
    expect(normalizeLimit(100)).toBe(100);
  });
});

describe('normalizeOffset', () => {
  it('缺失/非法值回落 0', () => {
    expect(normalizeOffset(undefined)).toBe(0);
    expect(normalizeOffset('abc')).toBe(0);
    expect(normalizeOffset('-1')).toBe(0);
    expect(normalizeOffset('1.5')).toBe(0);
  });

  it('合法非负整数按原值', () => {
    expect(normalizeOffset('10')).toBe(10);
    expect(normalizeOffset(0)).toBe(0);
    expect(normalizeOffset(25)).toBe(25);
  });
});

describe('formatPrice', () => {
  it('保留两位小数', () => {
    expect(formatPrice(199)).toBe('199.00');
    expect(formatPrice(19.5)).toBe('19.50');
    expect(formatPrice(19.99)).toBe('19.99');
  });
});

describe('searchProducts', () => {
  const okFetch = (payload: unknown) =>
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });

  it('正常命中：拼接 keyword/limit/offset 并解析 JSON', async () => {
    const fetchFn = okFetch({
      items: [{ id: 1, name: '无线蓝牙耳机', price: 199, stock: 32 }],
      total: 1,
    });
    const data = await searchProducts(
      '耳机',
      { limit: 20, offset: 0 },
      fetchFn as unknown as typeof fetch,
    );
    expect(fetchFn).toHaveBeenCalledWith(
      '/products/search?keyword=%E8%80%B3%E6%9C%BA&limit=20&offset=0',
    );
    expect(data.total).toBe(1);
    expect(data.items[0].name).toBe('无线蓝牙耳机');
  });

  it('limit 越界钳制 100、非法回落 20', async () => {
    const fetchFn = okFetch({ items: [], total: 0 });
    await searchProducts('x', { limit: 999 }, fetchFn as unknown as typeof fetch);
    expect(fetchFn).toHaveBeenCalledWith(
      '/products/search?keyword=x&limit=100&offset=0',
    );
    await searchProducts(
      'x',
      { limit: 'abc' },
      fetchFn as unknown as typeof fetch,
    );
    expect(fetchFn).toHaveBeenCalledWith(
      '/products/search?keyword=x&limit=20&offset=0',
    );
  });

  it('400 抛 keyword 不能为空', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ code: 400, message: 'keyword 不能为空' }),
    });
    await expect(
      searchProducts('', {}, fetchFn as unknown as typeof fetch),
    ).rejects.toThrow('keyword 不能为空');
  });

  it('其他非 2xx 抛请求失败', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    await expect(
      searchProducts('x', {}, fetchFn as unknown as typeof fetch),
    ).rejects.toThrow('HTTP 500');
  });
});
