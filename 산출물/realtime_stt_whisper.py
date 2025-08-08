import os
import asyncio
import aiohttp
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from dotenv import load_dotenv

# .env에서 API 키 불러오기
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI Whisper API endpoint
OPENAI_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"

# 오디오 녹음 파라미터
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'

async def speech_to_text_whisper(audio_path: str) -> str:
    """녹음된 오디오 파일을 OpenAI Whisper로 변환"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    form = aiohttp.FormData()
    form.add_field('file', open(audio_path, 'rb'), filename=os.path.basename(audio_path), content_type='audio/wav')
    form.add_field('model', 'whisper-1')
    form.add_field('response_format', 'json')
    form.add_field('language', 'ko')  # 한국어 인식 (필요시 변경)

    async with aiohttp.ClientSession() as session:
        async with session.post(OPENAI_WHISPER_URL, headers=headers, data=form) as resp:
            if resp.status == 200:
                result = await resp.json()
                return result.get('text', '')
            else:
                print(f"Whisper API 오류: {resp.status}")
                return ""

def record_audio_until_stop(output_path: str = "user_input.wav"):
    print("엔터를 누르면 녹음 시작, 답변이 끝나면 다시 엔터를 누르세요.")
    input("▶ 답변을 시작하려면 엔터를 누르세요...")
    print("🎙️ 녹음 중... 답변을 다 하셨으면 엔터를 다시 눌러주세요.")

    audio_list = []

    def callback(indata, frames, time, status):
        audio_list.append(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE, callback=callback)
    with stream:
        input()  # 유저가 엔터 누를 때까지 대기

    audio_np = np.concatenate(audio_list, axis=0)
    write(output_path, SAMPLE_RATE, audio_np)
    print(f"💾 오디오 저장 완료: {output_path}")
    return output_path

async def main():
    print("실시간 음성 입력을 Whisper로 텍스트 변환합니다.")

    num_questions = 15  # 질문 개수만큼 반복, 질문 개수가 변하면 추후에 수정

    for idx in range(num_questions):
        print(f"\n[{idx+1}/{num_questions}] 답변을 녹음하세요.")
        audio_path = record_audio_until_stop(output_path=f"user_input_{idx+1:02d}.wav")
        text = await speech_to_text_whisper(audio_path)
        text = text.strip()
        # 파일에 "번호: 답변" 형태로 (답변이 없으면 번호: )
        with open("recognized_texts_whisper.txt", "a", encoding="utf-8") as f:
            f.write(f"{idx+1}: {text}\n")
        print(f"📝 인식된 텍스트: {text if text else '[공백]'}")

if __name__ == "__main__":
    asyncio.run(main())