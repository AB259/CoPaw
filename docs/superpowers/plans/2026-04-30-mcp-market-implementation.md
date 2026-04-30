# MCP Market Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `D:\workspace\copaw1\CoPaw` 中补完“我的 MCP”页面与“应用市场 -> MCP”子 Tab，并复用现有 market 骨架实现 MCP 上传、分发、删除、测试连接和市场统计。

**Architecture:** 本次实现分为三条主线：本地 MCP 管理、市场 MCP 后端扩展、市场与我的 MCP 前端落地。后端复用现有 `marketplace` 的 `models.py / fs.py / schemas.py / service.py / routers` 分层；前端复用现有 `Market` 页面骨架与 `MyMCP` 入口，MCP 市场与本地页分别使用各自独立的数据 hooks 和弹窗组件。

**Tech Stack:** FastAPI, Pydantic, Python marketplace service/fs layer, React, TypeScript, Ant Design, pytest

---

## File Structure

### Existing files to modify

- `src/swe/config/config.py`
  责任：扩展 `MCPClientConfig` 的市场来源元数据字段。
- `market/src/market/marketplace/models.py`
  责任：扩展 `MarketItem`，支持 `item_type="mcp"` 与 `client_key`。
- `market/src/market/marketplace/fs.py`
  责任：新增市场 MCP 目录、读写、复制到用户本地的文件系统工具。
- `market/src/market/marketplace/schemas.py`
  责任：新增 MCP 市场请求/响应模型。
- `market/src/market/marketplace/service.py`
  责任：新增 MCP 市场发布、上传、分发、删除、查询、统计方法。
- `market/src/market/app/routers/__init__.py`
  责任：注册新的 MCP browse / market 路由。
- `console/src/api/modules/market.ts`
  责任：新增 MCP 市场 API 客户端。
- `console/src/pages/Market/MarketSkills.tsx`
  责任：将当前 MCP 占位分支替换为真实 MCP 市场视图。
- `console/src/pages/Market/useMarket.ts`
  责任：拆分或复用成支持 MCP 市场数据流。
- `console/src/pages/MyMCP/index.tsx`
  责任：将当前占位页替换为正式页面。

### New backend files

- `src/swe/app/routers/my_mcp.py`
  责任：本地 MCP 的列表、详情、创建、更新、删除、启停、测试、发布。
- `market/src/market/app/routers/mcp_browse.py`
  责任：市场 MCP 列表、详情。
- `market/src/market/app/routers/mcp_market.py`
  责任：市场 MCP 上传、分发、测试连接、删除。

### New frontend files

- `console/src/api/modules/myMcp.ts`
  责任：本地 MCP 页面 API 封装。
- `console/src/pages/MyMCP/useMyMCP.ts`
  责任：本地 MCP 页面状态与请求管理。
- `console/src/pages/MyMCP/components/MyMCPList.tsx`
  责任：左侧列表。
- `console/src/pages/MyMCP/components/MyMCPDetail.tsx`
  责任：右侧详情。
- `console/src/pages/MyMCP/components/EditMCPModal.tsx`
  责任：创建/编辑弹窗。
- `console/src/pages/MyMCP/components/PublishMCPModal.tsx`
  责任：发布到市场弹窗。
- `console/src/pages/Market/MarketMCP.tsx`
  责任：MCP 市场主视图。
- `console/src/pages/Market/useMarketMCP.ts`
  责任：MCP 市场数据与交互状态。
- `console/src/pages/Market/MCPDetailDrawer.tsx`
  责任：MCP 市场详情抽屉。
- `console/src/pages/Market/UploadMCPModal.tsx`
  责任：上传连接器弹窗。

### New / updated tests

- `market/tests/unit/marketplace/test_mcp_market.py`
- `market/tests/unit/marketplace/test_mcp_browse.py`
- `market/tests/unit/marketplace/test_mcp_fs.py`
- `tests/unit/app/routers/test_my_mcp.py`

---

### Task 1: Extend MCP config model and local router contracts

**Files:**
- Modify: `src/swe/config/config.py`
- Create: `src/swe/app/routers/my_mcp.py`
- Test: `tests/unit/app/routers/test_my_mcp.py`

- [ ] **Step 1: Write the failing router tests**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from swe.app.routers.my_mcp import router


def test_list_my_mcp_returns_source_fields(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api/my-mcp")

    monkeypatch.setattr(
        "swe.app.routers.my_mcp.list_my_mcp_clients",
        lambda request: [
            {
                "client_key": "weather-tool",
                "name": "Weather Tool",
                "description": "",
                "transport": "stdio",
                "enabled": True,
                "source": "marketplace:item-1",
                "market_client_key": "weather-tool",
                "created_at": "2026-04-30T00:00:00+00:00",
                "updated_at": "2026-04-30T00:00:00+00:00",
            }
        ],
    )

    client = TestClient(app)
    resp = client.get("/api/my-mcp")

    assert resp.status_code == 200
    assert resp.json()[0]["source"] == "marketplace:item-1"


def test_publish_my_mcp_returns_per_client_result(monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api/my-mcp")

    monkeypatch.setattr(
        "swe.app.routers.my_mcp.publish_my_mcp_clients",
        lambda request, body: {
            "results": [
                {
                    "client_key": "weather-tool",
                    "item_id": "item-1",
                    "success": True,
                }
            ]
        },
    )

    client = TestClient(app)
    resp = client.post(
        "/api/my-mcp/publish",
        json={"client_keys": ["weather-tool"], "category_id": 1, "bbk_ids": ["100"]},
    )

    assert resp.status_code == 200
    assert resp.json()["results"][0]["item_id"] == "item-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest tests/unit/app/routers/test_my_mcp.py -v`

Expected: FAIL with import errors or missing router endpoints.

- [ ] **Step 3: Add MCP config fields and router skeleton**

```python
# src/swe/config/config.py
class MCPClientConfig(BaseModel):
    name: str
    description: str = ""
    enabled: bool = True
    transport: Literal["stdio", "streamable_http", "sse"] = "stdio"
    url: str = ""
    headers: Dict[str, str] = {}
    command: str = ""
    args: List[str] = []
    env: Dict[str, str] = {}
    cwd: str = ""
    source: str = ""
    market_client_key: str = ""
    distributed_by: str = ""
    lazy_load: bool = False
    created_at: str = ""
    updated_at: str = ""
```

```python
# src/swe/app/routers/my_mcp.py
router = APIRouter()


@router.get("")
async def list_my_mcp(request: Request):
    return list_my_mcp_clients(request)


@router.post("/publish")
async def publish_my_mcp(request: Request, body: PublishMCPRequest):
    return publish_my_mcp_clients(request, body)
```

- [ ] **Step 4: Implement local MCP CRUD and publish contract**

```python
class PublishMCPRequest(BaseModel):
    client_keys: list[str]
    category_id: int | None = None
    bbk_ids: list[str] = Field(default_factory=list)


class PublishMCPResponse(BaseModel):
    results: list[dict]


def _mark_received_client(
    client: MCPClientConfig,
    *,
    item_id: str,
    client_key: str,
    operator_id: str,
) -> MCPClientConfig:
    updated = client.model_copy(deep=True)
    updated.source = f"marketplace:{item_id}"
    updated.market_client_key = client_key
    updated.distributed_by = operator_id
    return updated
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/python -m pytest tests/unit/app/routers/test_my_mcp.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/swe/config/config.py src/swe/app/routers/my_mcp.py tests/unit/app/routers/test_my_mcp.py
git commit -m "feat(mcp): add my mcp router contracts"
```

### Task 2: Extend marketplace models and filesystem for MCP items

**Files:**
- Modify: `market/src/market/marketplace/models.py`
- Modify: `market/src/market/marketplace/fs.py`
- Test: `market/tests/unit/marketplace/test_mcp_fs.py`

- [ ] **Step 1: Write the failing filesystem tests**

```python
from market.marketplace.fs import (
    get_mcp_dir,
    save_market_mcp_config,
    copy_mcp_to_user,
)


def test_get_mcp_dir_uses_item_id(tmp_path):
    result = get_mcp_dir(tmp_path / "market", "src_a", "item-1")
    assert result == tmp_path / "market" / "src_a" / "mcp" / "item-1"


def test_copy_mcp_to_user_sets_market_source(tmp_path):
    marketplace_root = tmp_path / "market"
    swe_root = tmp_path / "swe"

    save_market_mcp_config(
        marketplace_root=marketplace_root,
        source_id="src_a",
        item_id="item-1",
        client_key="weather-tool",
        config={"name": "Weather Tool", "command": "npx", "args": ["-y", "pkg"]},
    )

    copy_mcp_to_user(
        marketplace_root=marketplace_root,
        source_id="src_a",
        item_id="item-1",
        swe_root=swe_root,
        user_id="alice",
        client_key="weather-tool",
        distributed_by="admin",
    )

    data = (swe_root / "alice" / "workspaces" / "default" / "agent.json").read_text()
    assert "marketplace:item-1" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_fs.py -v`

Expected: FAIL because MCP fs helpers do not exist yet.

- [ ] **Step 3: Extend market models**

```python
# market/src/market/marketplace/models.py
class MarketItem(BaseModel):
    item_id: str
    item_type: str = "skill"
    name: str
    description: str = ""
    version: str = "1.0.0"
    creator_id: str
    creator_name: str = ""
    category_id: Optional[int] = None
    bbk_ids: list[str] = Field(default_factory=list)
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    client_key: str | None = None
```

- [ ] **Step 4: Add MCP fs helpers**

```python
def get_mcp_dir(marketplace_root: Path, source_id: str, item_id: str) -> Path:
    _validate_path_segment(source_id, "source_id")
    _validate_path_segment(item_id, "item_id")
    return get_marketplace_dir(marketplace_root, source_id) / "mcp" / item_id


def save_market_mcp_config(
    *,
    marketplace_root: Path,
    source_id: str,
    item_id: str,
    client_key: str,
    config: dict,
) -> None:
    mcp_dir = get_mcp_dir(marketplace_root, source_id, item_id)
    mcp_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(
        mcp_dir / "mcp.json",
        {"client_key": client_key, "config": config},
    )
```

```python
def copy_mcp_to_user(
    *,
    marketplace_root: Path,
    source_id: str,
    item_id: str,
    swe_root: Path,
    user_id: str,
    client_key: str,
    distributed_by: str,
    agent_id: str = DEFAULT_AGENT_ID,
) -> None:
    from swe.config.config import AgentConfig, MCPClientConfig, load_agent_config, save_agent_config

    market_data = json.loads(
        (get_mcp_dir(marketplace_root, source_id, item_id) / "mcp.json").read_text(encoding="utf-8")
    )
    config = MCPClientConfig.model_validate(market_data["config"])
    config.source = f"marketplace:{item_id}"
    config.market_client_key = client_key
    config.distributed_by = distributed_by

    agent = load_agent_config(agent_id, tenant_id=user_id)
    if agent.mcp is None:
        agent.mcp = MCPConfig(clients={})
    enabled_before = agent.mcp.clients.get(client_key).enabled if client_key in agent.mcp.clients else None
    agent.mcp.clients[client_key] = config
    if enabled_before is not None:
        agent.mcp.clients[client_key].enabled = enabled_before
    save_agent_config(agent_id, agent, tenant_id=user_id)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_fs.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add market/src/market/marketplace/models.py market/src/market/marketplace/fs.py market/tests/unit/marketplace/test_mcp_fs.py
git commit -m "feat(market): add mcp marketplace fs helpers"
```

### Task 3: Add MCP marketplace schemas and service methods

**Files:**
- Modify: `market/src/market/marketplace/schemas.py`
- Modify: `market/src/market/marketplace/service.py`
- Test: `market/tests/unit/marketplace/test_mcp_market.py`

- [ ] **Step 1: Write the failing service tests**

```python
from market.marketplace.schemas import PublishMCPRequest, DistributeRequest


async def test_publish_mcp_reuses_existing_item_id(app):
    svc = app.state.marketplace
    req = PublishMCPRequest(
        client_key="weather-tool",
        name="Weather Tool",
        description="",
        creator_id="u1",
        creator_name="Alice",
        category_id=1,
        bbk_ids=["100"],
        mcp_json={"client_key": "weather-tool", "config": {"name": "Weather Tool"}},
    )
    first = await svc.publish_mcp("src_a", req)
    second = await svc.publish_mcp("src_a", req)

    assert first.item_id == second.item_id


async def test_distribute_mcp_returns_count(app):
    svc = app.state.marketplace
    result = await svc.distribute_mcp(
        "src_a",
        "item-1",
        operator_id="admin",
        operator_name="Admin",
        req=DistributeRequest(target_type="user_id", target_values=["alice"]),
    )

    assert result.distributed_count == 1
    assert result.item_id == "item-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_market.py -v`

Expected: FAIL because MCP schemas/service APIs are missing.

- [ ] **Step 3: Add MCP marketplace schemas**

```python
class PublishMCPRequest(BaseModel):
    client_key: str
    name: str
    description: str = ""
    creator_id: str
    creator_name: str = ""
    category_id: Optional[int] = None
    bbk_ids: list[str] = Field(default_factory=list)
    mcp_json: dict = Field(default_factory=dict)


class MarketMCPResponse(BaseModel):
    item_id: str
    client_key: str
    name: str
    description: str
    creator_id: str
    creator_name: str
    category_id: Optional[int]
    bbk_ids: list[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    call_count: int = 0
    user_count: int = 0
```

- [ ] **Step 4: Implement MCP service methods**

```python
async def publish_mcp(self, source_id: str, req: PublishMCPRequest) -> MarketItem:
    items = load_index(self.marketplace_root, source_id)
    existing = next(
        (i for i in items if i.item_type == "mcp" and i.client_key == req.client_key),
        None,
    )
    now = datetime.now(timezone.utc).isoformat()
    if existing is not None:
        existing.name = req.name
        existing.description = req.description
        existing.creator_id = req.creator_id
        existing.creator_name = req.creator_name
        existing.category_id = req.category_id
        existing.bbk_ids = req.bbk_ids
        existing.updated_at = now
        item = existing
    else:
        item = MarketItem(
            item_id=str(uuid.uuid4()),
            item_type="mcp",
            client_key=req.client_key,
            name=req.name,
            description=req.description,
            creator_id=req.creator_id,
            creator_name=req.creator_name,
            category_id=req.category_id,
            bbk_ids=req.bbk_ids,
            created_at=now,
            updated_at=now,
        )
        items.append(item)

    save_market_mcp_config(
        marketplace_root=self.marketplace_root,
        source_id=source_id,
        item_id=item.item_id,
        client_key=req.client_key,
        config=req.mcp_json,
    )
    save_index(self.marketplace_root, source_id, items)
    return item
```

```python
async def distribute_mcp(
    self,
    source_id: str,
    item_id: str,
    operator_id: str,
    operator_name: str,
    req: DistributeRequest,
) -> DistributeResponse:
    item = next(
        (i for i in load_index(self.marketplace_root, source_id) if i.item_type == "mcp" and i.item_id == item_id),
        None,
    )
    if item is None:
        raise ValueError(f"Item {item_id} not found in source {source_id}")

    target_users = await self._resolve_target_users(source_id, req)
    count = 0
    for user in target_users:
        copy_mcp_to_user(
            marketplace_root=self.marketplace_root,
            source_id=source_id,
            item_id=item_id,
            swe_root=self.swe_root,
            user_id=user["tenant_id"],
            client_key=item.client_key or "",
            distributed_by=operator_id,
        )
        count += 1

    return DistributeResponse(distributed_count=count, item_id=item_id)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_market.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add market/src/market/marketplace/schemas.py market/src/market/marketplace/service.py market/tests/unit/marketplace/test_mcp_market.py
git commit -m "feat(market): add mcp marketplace service"
```

### Task 4: Add MCP marketplace routers and register them

**Files:**
- Create: `market/src/market/app/routers/mcp_browse.py`
- Create: `market/src/market/app/routers/mcp_market.py`
- Modify: `market/src/market/app/routers/__init__.py`
- Test: `market/tests/unit/marketplace/test_mcp_browse.py`

- [ ] **Step 1: Write the failing router tests**

```python
def test_list_market_mcp(client, app):
    resp = client.get("/market/mcp", headers={"X-Source-Id": "src_a", "X-Bbk-Id": "100"})
    assert resp.status_code == 200


def test_delete_market_mcp_returns_204(client):
    resp = client.delete(
        "/market/mcp/item-1",
        headers={"X-Source-Id": "src_a", "X-Manager": "true"},
    )
    assert resp.status_code == 204
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_browse.py -v`

Expected: FAIL because MCP routers are not registered.

- [ ] **Step 3: Add browse router**

```python
router = APIRouter()


@router.get("/market/mcp", response_model=list[MarketMCPResponse])
async def list_mcp(
    request: Request,
    category_id: int | None = None,
    x_source_id: str | None = Header(default=None, alias="X-Source-Id"),
    x_bbk_id: str | None = Header(default=None, alias="X-Bbk-Id"),
):
    source_id = require_source_id(x_source_id)
    user_bbk_id = x_bbk_id or "100"
    return await request.app.state.marketplace.list_mcp(source_id, user_bbk_id, category_id=category_id)
```

- [ ] **Step 4: Add market router and register both**

```python
@router.post("/market/mcp/upload")
async def upload_mcp(
    request: Request,
    file: UploadFile,
    name: str = Form(""),
    description: str = Form(""),
):
    ...


@router.delete("/market/mcp/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp(...):
    ...
```

```python
# market/src/market/app/routers/__init__.py
from .mcp_browse import router as mcp_browse_router
from .mcp_market import router as mcp_market_router
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_browse.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add market/src/market/app/routers/mcp_browse.py market/src/market/app/routers/mcp_market.py market/src/market/app/routers/__init__.py market/tests/unit/marketplace/test_mcp_browse.py
git commit -m "feat(market): add mcp market routers"
```

### Task 5: Add frontend API clients for MyMCP and Market MCP

**Files:**
- Create: `console/src/api/modules/myMcp.ts`
- Modify: `console/src/api/modules/market.ts`

- [ ] **Step 1: Add MyMCP API module**

```ts
import { request } from "../request";

export interface MyMCPListItem {
  client_key: string;
  name: string;
  description: string;
  transport: "stdio" | "streamable_http" | "sse";
  enabled: boolean;
  source: string;
  market_client_key?: string;
  created_at: string;
  updated_at: string;
}

export const myMcpApi = {
  list: () => request<MyMCPListItem[]>("/my-mcp"),
  detail: (clientKey: string) => request(`/my-mcp/${encodeURIComponent(clientKey)}`),
  publish: (payload: { client_keys: string[]; category_id?: number; bbk_ids?: string[] }) =>
    request("/my-mcp/publish", { method: "POST", body: JSON.stringify(payload) }),
};
```

- [ ] **Step 2: Add Market MCP API methods**

```ts
export interface MarketMCPItem {
  item_id: string;
  client_key: string;
  name: string;
  description: string;
  creator_id: string;
  creator_name: string;
  category_id: number | null;
  bbk_ids: string[];
  created_at: string | null;
  updated_at: string | null;
  call_count: number;
  user_count: number;
}

export const marketApi = {
  ...marketApi,
  listMarketMcp: async (sourceId: string, bbkId: string, categoryId?: number) => { ... },
  getMarketMcpDetail: async (sourceId: string, itemId: string, bbkId: string) => { ... },
  distributeMcp: async (sourceId: string, itemId: string, userId: string, userName: string, data: DistributeRequest) => { ... },
  deleteMcp: async (sourceId: string, itemId: string, userId: string, userName: string) => { ... },
};
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `npm --prefix console run build`

Expected: PASS without type errors in `myMcp.ts` and `market.ts`.

- [ ] **Step 4: Commit**

```bash
git add console/src/api/modules/myMcp.ts console/src/api/modules/market.ts
git commit -m "feat(console): add my mcp and market mcp api clients"
```

### Task 6: Implement MyMCP page

**Files:**
- Modify: `console/src/pages/MyMCP/index.tsx`
- Create: `console/src/pages/MyMCP/useMyMCP.ts`
- Create: `console/src/pages/MyMCP/components/MyMCPList.tsx`
- Create: `console/src/pages/MyMCP/components/MyMCPDetail.tsx`
- Create: `console/src/pages/MyMCP/components/EditMCPModal.tsx`
- Create: `console/src/pages/MyMCP/components/PublishMCPModal.tsx`

- [ ] **Step 1: Build page hook**

```ts
export function useMyMCP() {
  const [items, setItems] = useState<MyMCPListItem[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);

  const refresh = useCallback(async () => {
    const data = await myMcpApi.list();
    setItems(data);
  }, []);

  return { items, selectedKey, setSelectedKey, detail, setDetail, refresh };
}
```

- [ ] **Step 2: Replace placeholder page with master-detail layout**

```tsx
export default function MyMCPPage() {
  const { items, selectedKey, setSelectedKey, detail, refresh } = useMyMCP();

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <MyMCPList items={items} selectedKey={selectedKey} onSelect={setSelectedKey} />
      <MyMCPDetail detail={detail} />
    </div>
  );
}
```

- [ ] **Step 3: Add create/edit/publish modals**

```tsx
<EditMCPModal
  open={editOpen}
  initialValue={detail}
  onSuccess={() => {
    setEditOpen(false);
    void refresh();
  }}
/>

<PublishMCPModal
  open={publishOpen}
  clientKeys={selectedKeys}
  onSuccess={() => {
    setPublishOpen(false);
    void refresh();
  }}
/>
```

- [ ] **Step 4: Run frontend build**

Run: `npm --prefix console run build`

Expected: PASS and `console/src/pages/MyMCP` has no type errors.

- [ ] **Step 5: Commit**

```bash
git add console/src/pages/MyMCP
git commit -m "feat(console): implement my mcp page"
```

### Task 7: Implement Market MCP tab

**Files:**
- Modify: `console/src/pages/Market/MarketSkills.tsx`
- Create: `console/src/pages/Market/MarketMCP.tsx`
- Create: `console/src/pages/Market/useMarketMCP.ts`
- Create: `console/src/pages/Market/MCPDetailDrawer.tsx`
- Create: `console/src/pages/Market/UploadMCPModal.tsx`

- [ ] **Step 1: Build MCP market hook**

```ts
export function useMarketMCP(sourceId: string, bbkId: string) {
  const [items, setItems] = useState<MarketMCPItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<MarketMCPDetail | null>(null);

  const refresh = useCallback(async () => {
    const data = await marketApi.listMarketMcp(sourceId, bbkId);
    setItems(data);
  }, [sourceId, bbkId]);

  return { items, selectedItem, setSelectedItem, refresh };
}
```

- [ ] **Step 2: Replace MCP placeholder branch**

```tsx
{activeResourceType === "skill" ? (
  <SkillsBranch ... />
) : (
  <MarketMCP
    sourceId={sourceId}
    bbkId={bbkId}
    userId={userId}
    userName={userName}
    isManager={isManager}
  />
)}
```

- [ ] **Step 3: Add MCP detail / distribute / upload interactions**

```tsx
<MCPDetailDrawer
  open={detailOpen}
  item={selectedItem}
  onDistribute={() => setDistributeOpen(true)}
  onDelete={handleDelete}
/>

<UploadMCPModal
  open={uploadOpen}
  onSuccess={() => {
    setUploadOpen(false);
    void refresh();
  }}
/>
```

- [ ] **Step 4: Run frontend build**

Run: `npm --prefix console run build`

Expected: PASS and Market page compiles with MCP tab enabled.

- [ ] **Step 5: Commit**

```bash
git add console/src/pages/Market
git commit -m "feat(console): implement market mcp tab"
```

### Task 8: Final verification and docs sync

**Files:**
- Modify: `docs/superpowers/specs/2026-04-29-mcp-marketplace-design.md` (only if implementation forced a contract rename)
- Test: `tests/unit/app/routers/test_my_mcp.py`
- Test: `market/tests/unit/marketplace/test_mcp_fs.py`
- Test: `market/tests/unit/marketplace/test_mcp_market.py`
- Test: `market/tests/unit/marketplace/test_mcp_browse.py`

- [ ] **Step 1: Run backend MCP tests**

Run:

```bash
venv/bin/python -m pytest tests/unit/app/routers/test_my_mcp.py -v
venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_fs.py -v
venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_market.py -v
venv/bin/python -m pytest market/tests/unit/marketplace/test_mcp_browse.py -v
```

Expected: PASS

- [ ] **Step 2: Run frontend build**

Run: `npm --prefix console run build`

Expected: PASS

- [ ] **Step 3: Smoke-check critical flows manually**

Run through:

```text
1. 打开 /my-mcp，确认不再是空白占位页
2. 创建本地 MCP，查看详情
3. 发布到市场
4. 打开 /market，切换到 MCP Tab
5. 查看 MCP 详情并测试连接
6. 执行分发并确认 distributed_count 返回
7. 删除市场条目后重新打开详情，确认得到友好错误
```

- [ ] **Step 4: Sync spec only if contract changed**

```md
- 如果实现中保持了 `DELETE /market/mcp/{item_id} -> 204`
- 如果实现中保持了 `source="marketplace:{item_id}"`
- 如果实现中保持了 `DistributeResponse { distributed_count, item_id }`
```

- [ ] **Step 5: Final commit**

```bash
git add src/swe/app/routers/my_mcp.py src/swe/config/config.py market/src/market/marketplace market/src/market/app/routers console/src/api/modules console/src/pages/MyMCP console/src/pages/Market tests/unit/app/routers market/tests/unit/marketplace docs/superpowers/specs/2026-04-29-mcp-marketplace-design.md
git commit -m "feat(mcp): implement my mcp and marketplace mcp flows"
```

