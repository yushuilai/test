import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProductSearchPage from './ProductSearchPage';

beforeEach(() => {
  window.matchMedia =
    window.matchMedia ||
    function matchMedia(query: string): MediaQueryList {
      return {
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      } as MediaQueryList;
    };
});

describe('ProductSearchPage', () => {
  it('渲染搜索框与空态提示', () => {
    render(<ProductSearchPage search={vi.fn()} />);

    expect(screen.getByPlaceholderText('输入商品名关键词')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /搜\s*索/ })).toBeInTheDocument();
    expect(screen.getByText('暂无匹配商品')).toBeInTheDocument();
  });

  it('空关键词：不调用搜索，显示错误提示', async () => {
    const search = vi.fn();
    render(<ProductSearchPage search={search} />);

    fireEvent.click(screen.getByRole('button', { name: /搜\s*索/ }));

    expect(await screen.findByText('请输入商品关键词')).toBeInTheDocument();
    expect(search).not.toHaveBeenCalled();
  });

  it('正常命中：展示商品名与两位小数价格', async () => {
    const search = vi.fn().mockResolvedValue({
      items: [
        { id: 1, name: '无线蓝牙耳机', price: 199, stock: 32 },
        { id: 2, name: '有线耳机', price: 19.5, stock: 8 },
      ],
      total: 2,
    });
    render(<ProductSearchPage search={search} />);

    fireEvent.change(screen.getByPlaceholderText('输入商品名关键词'), {
      target: { value: '耳机' },
    });
    fireEvent.click(screen.getByRole('button', { name: /搜\s*索/ }));

    expect(await screen.findByText('无线蓝牙耳机')).toBeInTheDocument();
    expect(screen.getByText('¥199.00')).toBeInTheDocument();
    expect(screen.getByText('¥19.50')).toBeInTheDocument();
    expect(screen.getByText('共 2 条结果')).toBeInTheDocument();
    await waitFor(() =>
      expect(search).toHaveBeenCalledWith('耳机', 20, 0),
    );
  });

  it('无结果：展示空态', async () => {
    const search = vi.fn().mockResolvedValue({ items: [], total: 0 });
    render(<ProductSearchPage search={search} />);

    fireEvent.change(screen.getByPlaceholderText('输入商品名关键词'), {
      target: { value: '不存在' },
    });
    fireEvent.click(screen.getByRole('button', { name: /搜\s*索/ }));

    expect(await screen.findByText('暂无匹配商品')).toBeInTheDocument();
  });

  it('后端 400：展示错误信息', async () => {
    const search = vi.fn().mockRejectedValue(new Error('keyword 不能为空'));
    render(<ProductSearchPage search={search} />);

    fireEvent.change(screen.getByPlaceholderText('输入商品名关键词'), {
      target: { value: 'x' },
    });
    fireEvent.click(screen.getByRole('button', { name: /搜\s*索/ }));

    expect(await screen.findByText('keyword 不能为空')).toBeInTheDocument();
  });
});
