"""Audio Playback Server - 接收音频并通过系统扬声器播放."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import numpy as np
import sounddevice as sd  # type: ignore[import-untyped]
from fastapi import FastAPI, Request

app = FastAPI()

# 创建保存目录
os.makedirs("logs", exist_ok=True)

# 播放速度倍率
PLAYBACK_SPEED = 1.25


def pcm_to_numpy(pcm_bytes: bytes) -> np.ndarray:
    """将 PCM16 字节转换为 numpy 数组."""
    # PCM16 是 16 位有符号整数，小端序
    audio_data = np.frombuffer(pcm_bytes, dtype=np.int16)
    # 转换为浮点数 [-1.0, 1.0]
    audio_float = audio_data.astype(np.float32) / 32768.0
    return audio_float


def play_audio(audio_data: np.ndarray, sample_rate: int, speed: float = 1.0) -> None:
    """播放音频数据.

    Args:
        audio_data: numpy 数组格式的音频数据
        sample_rate: 原始采样率
        speed: 播放速度倍率 (1.0 = 正常速度, 1.25 = 1.25倍速)
    """
    # 调整采样率以改变播放速度
    # 提高采样率 = 加速播放
    adjusted_sample_rate = int(sample_rate * speed)

    try:
        # 使用 sounddevice 播放音频（非阻塞）
        sd.play(audio_data, samplerate=adjusted_sample_rate)
        # 注意：不调用 sd.wait()，这样可以非阻塞播放
    except Exception as e:
        print(f"   ❌ 播放失败: {e}")


@app.post("/audio")
async def receive_audio(request: Request, uid: str, sample_rate: int) -> dict[str, Any]:
    """接收音频数据并播放.

    参数:
    - uid: 用户/设备ID
    - sample_rate: 采样率（通常是16000 Hz）
    """
    _ = uid  # 保留参数用于 API 兼容性

    # 获取原始音频字节 (PCM格式)
    audio_bytes = await request.body()

    # 计算音频时长
    duration = len(audio_bytes) / (sample_rate * 2)  # 2字节 per sample
    size_kb = len(audio_bytes) / 1024

    # 打印日志（带毫秒时间戳）
    timestamp = datetime.now(tz=UTC).strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] 📼 收到音频: {size_kb:.1f}KB, {duration:.1f}秒")

    # 转换为 numpy 数组
    audio_data = pcm_to_numpy(audio_bytes)

    # 播放音频（1.25倍速）
    print(f"[{timestamp}] 🔊 播放中 ({PLAYBACK_SPEED}x 倍速)...")
    play_audio(audio_data, sample_rate, speed=PLAYBACK_SPEED)

    return {
        "status": "success",
        "bytes_received": len(audio_bytes),
        "duration_seconds": round(duration, 2),
        "playback_speed": PLAYBACK_SPEED,
    }


@app.get("/")
async def root() -> dict[str, Any]:
    """健康检查接口."""
    return {
        "status": "running",
        "service": "Audio Playback Server",
        "version": "1.0",
        "playback_speed": f"{PLAYBACK_SPEED}x",
        "endpoints": {
            "/": "服务状态",
            "/audio": "接收并播放音频（POST）",
        },
    }


def main() -> None:
    """启动服务器."""
    import uvicorn  # noqa: PLC0415

    print("=" * 70)
    print("🔊  Audio Playback Server v1.0")
    print("=" * 70)
    print("📡 本地地址: http://localhost:8000")
    print("🌐 公网地址: 请使用 ngrok http 8000 获取")
    print("")
    print(f"🎵 播放速度: {PLAYBACK_SPEED}x 倍速")
    print("")
    print("📝 功能:")
    print("   - 接收并播放音频: POST /audio")
    print("   - 查看状态: GET /")
    print("")
    print("💡 依赖:")
    print("   - pip install sounddevice numpy")
    print("=" * 70)

    # 启动服务器
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
