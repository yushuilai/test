import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoginPage from './LoginPage';

// antd 的部分响应式组件依赖 window.matchMedia，jsdom 默认未实现，这里做最小 polyfill
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

describe('LoginPage', () => {
  it('渲染用户名、密码输入框与登录按钮', () => {
    render(<LoginPage />);

    expect(screen.getByPlaceholderText('用户名')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('密码')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /登\s*录/ })).toBeInTheDocument();
    expect(screen.getByText('记住我')).toBeInTheDocument();
  });

  it('空表单提交时显示校验错误', async () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByRole('button', { name: /登\s*录/ }));

    expect(await screen.findByText('请输入用户名')).toBeInTheDocument();
    expect(await screen.findByText('请输入密码')).toBeInTheDocument();
  });

  it('填写账号密码后提交，调用 onFinish 并携带表单值', async () => {
    const onFinish = vi.fn();
    render(<LoginPage onFinish={onFinish} />);

    fireEvent.change(screen.getByPlaceholderText('用户名'), {
      target: { value: 'admin' },
    });
    fireEvent.change(screen.getByPlaceholderText('密码'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /登\s*录/ }));

    await waitFor(() =>
      expect(onFinish).toHaveBeenCalledWith(
        expect.objectContaining({ username: 'admin', password: '123456' }),
      ),
    );
  });
});
