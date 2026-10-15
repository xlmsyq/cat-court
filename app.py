"""猫猫法庭 (Cat Court) — 一只奶牛猫法官帮情侣 / 朋友 / 同事化解小矛盾。

开源版：不依赖任何内部平台，只需要一个 Anthropic API Key（或任意
Anthropic Messages 协议兼容的网关）。

启动：
    export ANTHROPIC_API_KEY=sk-ant-xxx
    # 可选：export ANTHROPIC_BASE_URL=https://your-gateway/v1
    # 可选：export CAT_COURT_MODEL=claude-sonnet-4-20250514
    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/")
MODEL = os.getenv("CAT_COURT_MODEL", "claude-sonnet-4-20250514")


async def llm_chat(messages: list[dict], max_tokens: int = 3000) -> str:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="未配置 ANTHROPIC_API_KEY")
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"{BASE_URL}/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": MODEL, "max_tokens": max_tokens, "messages": messages},
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"LLM error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        return data["content"][0]["text"]
    except Exception:
        raise HTTPException(status_code=502, detail=f"LLM 响应格式异常: {str(data)[:200]}")


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(status_code=502, detail="猫猫法官打盹了，判决书没写完整，请重试")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="猫猫法官爪子抖了，判决书解析失败，请重试")


SYSTEM_RULES = """你是「猫猫法官」，一只穿黑白法袍的奶牛猫（tuxedo cat），
在「猫猫法庭」审理情侣之间的小矛盾。你的目标不是分出输赢，而是让两个人和好。

铁律：
1. 语气俏皮、温柔、有幽默感，像一只有点傲娇但很懂事的猫。可以用「喵」「本喵」「肉垫」等词，但不要每句都用。
2. 判决必须真的有洞察：先讲清双方冲突的「本质」（往往是需求语言不同：一方要情绪回应，一方要独处恢复），
   再讲责任占比。责任占比允许不对等（例如 90 : 10），但要说明理由，且必须给「占比小」的一方也留台阶。
3. 严禁说教、严禁贴「有毒关系」「PUA」「分手吧」这类标签；严禁诊断精神疾病。
4. 罪名要用可爱条款体，例如「根据《神圣的共享零食亲密小甜心条款》第三条」。轻罪/重罪都要写得让人想笑，不能羞辱人。
5. 和解方案必须具体、可当场执行、可以直接复制发给对方；至少一条包含身体接触或食物分享。
6. 如果一方正在生病 / 状态很差，判决要照顾现实约束，给出「低能耗版」的补偿方式。
7. 只输出 JSON，不要输出任何解释文字。"""

SCHEMA_HINT = """输出严格符合下面结构的 JSON（全部中文，除 key 外）：
{
  "case_no": "喵字第 XXXX 号",
  "title": "一句话案由，不超过 20 字",
  "essence": "冲突本质分析，120-200 字，点名双方各自真正在意的东西",
  "party_a_core": "A 真正的需求，一句话",
  "party_b_core": "B 真正的需求，一句话",
  "blame": {"a": 数字, "b": 数字},          // 两数之和必须等于 100
  "charges": [
    {"party": "A 或 B 的名字", "level": "重罪/轻罪/微罪", "clause": "《XX条款》第X条", "text": "罪名描述，30 字内"}
  ],
  "verdict": "正式判决措辞，80-150 字，带一点庄严的搞笑感",
  "reconcile_steps": [
    {"step": 1, "title": "步骤标题", "detail": "具体怎么做，40 字内", "owner": "A 名字 / B 名字 / 双方"}
  ],
  "message_to_partner": "可以直接复制发给对方的一段话，第一人称，80-140 字，softening 且不指责",
  "intimacy_delta": 数字,                   // 完成全部和解步骤后亲密指数预计增加，3-12
  "tasks": [
    {"title": "提升亲密指数的小任务", "points": 数字}   // 3-4 条，points 1-5
  ],
  "cat_note": "猫猫法官的庭后碎碎念，一句话，可爱收尾"
}
charges 给 2-4 条（双方都要有），reconcile_steps 给 3-4 条。"""

class Party(BaseModel):
    name: str = ""
    statement: str = ""


class JudgeRequest(BaseModel):
    party_a: Party
    party_b: Party
    appeal: Optional[str] = None
    previous_verdict: Optional[dict] = None


app = FastAPI(title="猫猫法庭 Cat Court")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/whoami")
def whoami() -> JSONResponse:
    # 开源版不做鉴权；自己部署时可在此接入你自己的登录体系
    return JSONResponse({"name": "", "userId": "", "email": ""})


@app.post("/api/judge")
async def judge(req: JudgeRequest) -> JSONResponse:
    a_name = (req.party_a.name or "甲方").strip()[:12]
    b_name = (req.party_b.name or "乙方").strip()[:12]
    a_text = (req.party_a.statement or "").strip()[:2000]
    b_text = (req.party_b.statement or "").strip()[:2000]
    if len(a_text) < 5 or len(b_text) < 5:
        raise HTTPException(status_code=400, detail="两边都要说几句，本喵才好断案")

    prompt = f"""【原告/甲方】{a_name} 的陈述：
{a_text}

【被告/乙方】{b_name} 的陈述：
{b_text}
"""
    if req.appeal:
        prev = json.dumps(req.previous_verdict or {}, ensure_ascii=False)[:2500]
        prompt += f"""
【上诉状】有一方对上一次判决不服，申诉理由：
{(req.appeal or '').strip()[:1200]}

【上一次判决摘要】
{prev}

请重新审理：认真回应申诉理由，责任占比可以调整（也可以维持，但要说明为什么维持），
case_no 后面加「二审」二字，verdict 里要提到「经二审重新审理」。
"""
    prompt += "\n" + SCHEMA_HINT + f"\n注意：charges/reconcile_steps 里的名字请使用「{a_name}」和「{b_name}」。"

    raw = await llm_chat([{"role": "user", "content": SYSTEM_RULES + "\n\n" + prompt}])
    return JSONResponse(_normalize(_extract_json(raw)))


def _normalize(v: dict) -> dict:
    blame = v.get("blame") or {}
    try:
        a = int(blame.get("a", 50))
        b = int(blame.get("b", 50))
    except Exception:
        a, b = 50, 50
    total = a + b
    if total != 100 and total > 0:
        a = round(a * 100 / total)
        b = 100 - a
    v["blame"] = {"a": max(0, min(100, a)), "b": max(0, min(100, b))}
    try:
        v["intimacy_delta"] = max(1, min(20, int(v.get("intimacy_delta", 6))))
    except Exception:
        v["intimacy_delta"] = 6
    tasks = v.get("tasks") or []
    clean = []
    for t in tasks[:5]:
        if not isinstance(t, dict):
            continue
        try:
            pts = max(1, min(8, int(t.get("points", 2))))
        except Exception:
            pts = 2
        clean.append({"title": str(t.get("title", "抱一下"))[:40], "points": pts})
    if not clean:
        clean = [
            {"title": "给对方一个 10 秒以上的拥抱", "points": 3},
            {"title": "一起吃一份想吃很久的零食", "points": 2},
            {"title": "说一句「刚才那样我其实是想…」", "points": 3},
        ]
    v["tasks"] = clean
    return v
