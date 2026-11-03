# 商品搜索接口文档

> 说明：本接口为后端预留接口，当前项目仅交付前端（React / Ant Design）。
> 本文档用于约定前后端契约，后端实现与 pytest 单测由后端同学后续按此文档落地。

## 基本信息

| 项 | 值 |
| --- | --- |
| 接口名称 | 商品搜索 |
| 请求方法 | GET |
| 请求路径 | `/products/search` |
| Content-Type | 无需请求体 |
| 响应格式 | `application/json` |

## 请求参数（Query String）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `keyword` | string | 是 | - | 搜索关键词，对商品名做模糊匹配 |
| `limit` | integer | 否 | 20 | 返回条数上限，取值范围 1 ~ 100 |

### 参数约束

1. `keyword` 为**空字符串**或**缺失**时，返回 `400`。
2. `limit` 越界时**钳制（clamp）到合法区间**，而非报错：
   - `limit < 1` → 按 `1` 处理；
   - `limit > 100` → 按 `100` 处理；
   - `limit` 非数字或非法 → 按默认值 `20` 处理（可与后端确认后统一，见「待确认」）。

## 响应结构

### 成功响应（200）

```json
{
  "items": [
    {
      "id": 1001,
      "name": "无线蓝牙耳机",
      "price": 199.00,
      "stock": 32
    }
  ],
  "total": 1
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `items` | array | 商品列表 |
| `items[].id` | number | 商品 ID |
| `items[].name` | string | 商品名 |
| `items[].price` | number | 价格，**保留两位小数**（如 `199.00`，建议服务端序列化时格式化） |
| `items[].stock` | number | 库存 |
| `total` | number | 命中的总条数 |

### 错误响应（400）

当 `keyword` 为空或缺失时：

```json
{
  "code": 400,
  "message": "keyword 不能为空"
}
```

## 性能要求

- 单次查询 **P95 < 100ms**。
- **不引入外部依赖**：模糊匹配、分页限制均在应用内实现，不依赖额外搜索中间件或第三方库。

## 测试覆盖（pytest，后端实现时执行）

| 用例 | 场景 | 预期 |
| --- | --- | --- |
| 1 | 正常命中 | 传入合法 `keyword`，返回匹配商品，`total` 正确，`price` 保留两位小数 |
| 2 | 空关键词 | `keyword` 为空或缺失，返回 `400` |
| 3 | limit 越界 | `limit=999` 被钳制为 `100`；`limit=0` 被钳制为 `1` |
| 4 | 无结果 | 合法 `keyword` 但无匹配，返回 `200` 且 `items=[]`、`total=0` |

## 前端对接约定（预留）

前端登录页后续可在此接口基础上扩展商品搜索页，示例调用：

```ts
const res = await fetch(
  `/products/search?keyword=${encodeURIComponent(keyword)}&limit=20`
);
const data = await res.json(); // { items, total }
```

## 待确认（open questions）

1. `limit` 传入非数字（如 `abc`、`-1`、浮点数）时的处理：报 `400` 还是按默认值 `20` 处理？
2. 模糊匹配的具体语义：子串匹配、前缀匹配，还是分词匹配？
3. 是否支持分页偏移参数（如 `offset`/`page`）？
