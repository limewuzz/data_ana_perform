# Backend (FastAPI + JWT)

## 开发启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
export APP_JWT_SECRET='change-me'
uvicorn app.main:app --reload
```

默认使用 SQLite：`backend/app.db`。

## 默认模型

项目启动后会自动同步并只保留下面两条默认模型配置：

- `model_id`: `kimi-k2.6`
  `provider`: `kimi`
  默认 `base_url`: `https://api.moonshot.cn/v1`
- `model_id`: `mimo-v2.5-pro`
  `provider`: `xiaomimimo`
  默认 `base_url`: `https://token-plan-cn.xiaomimimo.com/v1`

启动前配置环境变量：

```bash
export APP_JWT_SECRET='change-me'
export APP_KIMI_API_KEY='your-kimi-token'
export APP_XIAOMIMIMO_API_KEY='your-token'
```

如果需要覆盖网关地址，也可以额外设置：

```bash
export APP_KIMI_BASE_URL='https://api.moonshot.cn/v1'
export APP_XIAOMIMIMO_BASE_URL='https://token-plan-cn.xiaomimimo.com/v1'
```

项目会在启动时自动清理其他默认模型配置，只保留 `kimi-k2.6` 和 `mimo-v2.5-pro`。

## 最小流程（curl）

```bash
BASE=http://127.0.0.1:8000

TOKEN=$(curl -sS -X POST $BASE/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"a@b.com","password":"pass","role":"annotator"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

TASK_ID=$(curl -sS -X POST $BASE/api/tasks \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"prompt":"hi","model_ids":["kimi-k2.6","mimo-v2.5-pro"]}' | python3 - <<'PY'
import sys, json
obj=json.load(sys.stdin)
print(obj["id"])
PY
)

RESP_IDS=$(curl -sS $BASE/api/tasks/$TASK_ID -H "authorization: Bearer $TOKEN" | python3 - <<'PY'
import sys, json
obj=json.load(sys.stdin)
ids=[r["id"] for r in obj["responses"][:2]]
print(ids[0], ids[1])
PY
)
R1=$(echo $RESP_IDS | awk '{print $1}')
R2=$(echo $RESP_IDS | awk '{print $2}')

curl -sS -X POST $BASE/api/annotations \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"task_id\":$TASK_ID,\"ranking_groups\":[[$R1,$R2]],\"scores\":{\"$R1\":5,\"$R2\":3}}"

curl -sS -X POST $BASE/api/export \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"format":"dpo","tie_handling":"random"}'
```

## 测试

```bash
cd backend
export APP_JWT_SECRET='test-secret'
pytest -q
```
