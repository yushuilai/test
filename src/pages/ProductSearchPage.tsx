import { useState } from 'react';
import { Input, Table, Alert, Card, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  searchProducts,
  formatPrice,
  type Product,
  type ProductSearchResult,
} from '../api/products';

export type SearchFn = (
  keyword: string,
  limit?: number,
  offset?: number,
) => Promise<ProductSearchResult>;

interface ProductSearchPageProps {
  /** 搜索函数，默认调用真实接口，便于测试时注入 mock */
  search?: SearchFn;
}

const defaultSearch: SearchFn = (keyword, limit, offset) =>
  searchProducts(keyword, { limit, offset });

export default function ProductSearchPage({
  search = defaultSearch,
}: ProductSearchPageProps) {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const columns: ColumnsType<Product> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '商品名', dataIndex: 'name', key: 'name' },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (value: number) => `¥${formatPrice(value)}`,
    },
    { title: '库存', dataIndex: 'stock', key: 'stock' },
  ];

  const handleSearch = async (value: string) => {
    const keyword = value.trim();
    if (!keyword) {
      setError('请输入商品关键词');
      setItems([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await search(keyword, 20, 0);
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : '搜索失败，请稍后重试');
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="search-container">
      <Card className="search-card">
        <Typography.Title level={4} className="search-title">
          商品搜索
        </Typography.Title>
        <Input.Search
          placeholder="输入商品名关键词"
          enterButton="搜索"
          size="large"
          allowClear
          loading={loading}
          onSearch={handleSearch}
        />
        {error && (
          <Alert
            type="error"
            showIcon
            message={error}
            style={{ marginTop: 12 }}
          />
        )}
        <Table<Product>
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={false}
          locale={{ emptyText: '暂无匹配商品' }}
          style={{ marginTop: 16 }}
        />
        {total > 0 && (
          <Typography.Text type="secondary">共 {total} 条结果</Typography.Text>
        )}
      </Card>
    </div>
  );
}
