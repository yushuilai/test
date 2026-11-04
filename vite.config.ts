/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    // Windows 上 forks 池并发写模块缓存临时文件会偶发 EPERM，串行执行规避
    fileParallelism: false,
  },
});
