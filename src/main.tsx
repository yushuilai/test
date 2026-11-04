import React from 'react';
import ReactDOM from 'react-dom/client';
import { Tabs } from 'antd';
import LoginPage from './pages/LoginPage';
import ProductSearchPage from './pages/ProductSearchPage';
import './index.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <Tabs
      defaultActiveKey="search"
      centered
      items={[
        { key: 'login', label: '登录', children: <LoginPage /> },
        { key: 'search', label: '商品搜索', children: <ProductSearchPage /> },
      ]}
    />
  </React.StrictMode>,
);
