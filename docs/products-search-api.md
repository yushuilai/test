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
| `keyword` | string | 是 | - | 搜索关键词，对商品名做**子串匹配**（`商品名包含 keyword 即命中`） |
| `limit` | integer | 否 | 20 | 返回条数上限，取值范围 1 ~ 100 |
| `offset` | integer | 否 | 0 | 分页偏移，跳过前 N 条，非负整数 |

### 参数约束

1. `keyword` 为**空字符串**或**缺失**时，返回 `400`。
2. `keyword` 模糊匹配语义为**子串匹配（substring）**：`keyword` 是商品名的连续子串即命中，如 `keyword="耳机"` 命中「无线蓝牙耳机」。
3. `limit` 按以下顺序处理（优先级从高到低）：
   - `limit` 缺失 → 按默认值 `20`；
   - `limit` 为非法值（非数字字符串如 `abc`、负数如 `-1`、零 `0`、浮点数如 `1.5`）→ 按默认值 `20`；
   - `limit` 为大于 `100` 的正整数 → **钳制为 `100`**；
   - `limit` 为 `1 ~ 100` 的正整数 → 按原值。
4. `offset` 处理：
   - `offset` 缺失或非法（非数字、负数、浮点数）→ 按默认值 `0`；
   - `offset` 为合法非负整数 → 按原值；
   - `offset` 超过命中总数时，返回空 `items`（`total` 仍为命中总数）。

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
| `items` | array | 当前页商品列表（`[offset, offset + limit)` 区间） |
| `items[].id` | number | 商品 ID |
| `items[].name` | string | 商品名 |
| `items[].price` | number | 价格，**保留两位小数**（如 `199.00`，建议服务端序列化时格式化） |
| `items[].stock` | number | 库存 |
| `total` | number | 命中的总条数（**不受分页影响**，用于前端计算总页数） |

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
- **不引入外部依赖**：子串匹配、分页限制均在应用内实现，不依赖额外搜索中间件或第三方库。

## 测试覆盖（pytest，后端实现时执行）

| 用例 | 场景 | 预期 |
| --- | --- | --- |
| 1 | 正常命中 | 传入合法 `keyword`，返回匹配商品，`total` 正确，`price` 保留两位小数 |
| 2 | 空关键词 | `keyword` 为空或缺失，返回 `400` |
| 3 | limit 越界/非法 | `limit=999` 被钳制为 `100`；`limit=abc`/`-1`/`1.5`/`0` 按默认值 `20` |
| 4 | 无结果 | 合法 `keyword` 但无匹配，返回 `200` 且 `items=[]`、`total=0` |
| 5 | 分页偏移 | `offset=10&limit=20` 返回第 11~30 条，`total` 为命中总数 |
| 6 | offset 越界 | `offset` 大于命中总数，返回 `200` 且 `items=[]`、`total` 仍为命中总数 |

## 前端对接约定（预留）

前端登录页后续可在此接口基础上扩展商品搜索页，示例调用：

```ts
const res = await fetch(
  `/products/search?keyword=${encodeURIComponent(keyword)}&limit=20&offset=0`
);
const data = await res.json(); // { items, total }
```

## 边界语义（已确认）

以下两点为本轮明确锁定，后端实现与前端对接均按此执行：

1. `limit=0`：按**非法值**处理，回落到默认值 `20`（不做钳制为 `1`）。
2. `offset` 超出命中总数：返回 `200`，`items=[]`，`total` 仍为命中总数（前端据此渲染「无更多数据」态）。
