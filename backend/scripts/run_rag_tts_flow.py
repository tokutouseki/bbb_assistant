import base64
import datetime
import json
import os
import urllib.request


def post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    query = "琪亚娜的人物介绍"
    rag_resp = post_json(
        "http://127.0.0.1:8000/api/rag/search",
        {"query": query, "mode": "hybrid", "top_k": 5},
        timeout=90,
    )
    results = rag_resp.get("results", [])

    if results:
        lines = []
        for r in results[:3]:
            name = r.get("name", "unknown")
            content = (r.get("content", "") or "").replace("\n", " ").strip()
            lines.append(f"[{name}] {content[:120]}")
        answer = (
            "根据知识库检索结果：琪亚娜是崩坏3核心角色，性格热情、行动力强，并在剧情中持续成长。\n"
            + "\n".join(lines)
        )
    else:
        answer = "知识库未命中，给出简要介绍：琪亚娜是崩坏3主角之一，性格直率勇敢。"

    tts_resp = post_json(
        "http://127.0.0.1:8000/api/audio/tts",
        {"text": answer, "voice_id": "温柔女声", "tts_engine": "qwen3"},
        timeout=180,
    )

    out_dir = r"d:/TokusCode/bbb_assistant/outputs/flow_demo"
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_wav = os.path.join(out_dir, f"kiana_rag_tts_{ts}.wav")
    out_txt = os.path.join(out_dir, f"kiana_rag_reply_{ts}.txt")

    with open(out_wav, "wb") as f:
        f.write(base64.b64decode(tts_resp.get("audio_base64", "")))
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(answer)

    print(f"RAG_TOTAL={len(results)}")
    print(f"TTS_ENGINE={tts_resp.get('tts_engine')}")
    print(f"WAV={out_wav}")
    print(f"TXT={out_txt}")


if __name__ == "__main__":
    main()
