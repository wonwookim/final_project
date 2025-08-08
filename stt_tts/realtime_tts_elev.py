import os
import aiohttp
import asyncio
import tempfile
import pygame
from dotenv import load_dotenv
from enum import Enum

# ✅ .env에서 API 키 로드
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# 🎙️ 면접관 목소리
class InterviewerVoice(Enum):
    HYUK = "ZJCNdZEjYwkOElxugmW2"
    SALANG = "mYk0rAapHek2oTw18z8x"
    NOBEL_BUTLER = "YBRudLRm83BV5Mazcr42"

# 🤖 지원자 성별
class CandidateGender(Enum):
    FEMALE = "uyVNoMrVvroE5JXeeUSJakg"  
    MALE = "H8ObVvroE5JXeeUSJakg"       

# ✅ ElevenLabs TTS API
class ElevenLabsTTS:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech_stream(self, text: str, voice_id: str) -> bytes:
        """텍스트 → 음성(MP3) 변환"""
        url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as r:
                if r.status != 200:
                    raise Exception(f"TTS API 오류: {r.status}")
                return await r.read()

# ✅ 비동기 오디오 재생기
class AsyncAudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.queue = asyncio.Queue()
        self.play_task = None

    async def add_audio(self, audio_bytes: bytes):
        """임시파일에 저장 후 큐에 추가"""
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp.write(audio_bytes)
        temp.close()
        await self.queue.put(temp.name)

    async def _play_loop(self):
        """큐에서 파일 꺼내서 재생"""
        while True:
            path = await self.queue.get()
            if path is None:
                break
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
            finally:
                os.remove(path)  # ✅ 재생 끝나면 삭제
            self.queue.task_done()

    def start(self):
        if not self.play_task:
            self.play_task = asyncio.create_task(self._play_loop())

    async def stop(self):
        """재생 중단 및 정리"""
        await self.queue.put(None)
        if self.play_task:
            await self.play_task

# ✅ LLM → TTS → 재생 시스템
class RealtimeLLMToTTS:
    def __init__(self, api_key: str, gender: CandidateGender = CandidateGender.FEMALE):
        self.tts = ElevenLabsTTS(api_key)
        self.player = AsyncAudioPlayer()
        self.gender = gender

    async def speak_interviewer(self, text: str, interviewer: InterviewerVoice):
        print(f"🎤 [면접관 {interviewer.name}] {text}")
        audio = await self.tts.text_to_speech_stream(text, interviewer.value)
        await self.player.add_audio(audio)

    async def speak_candidate(self, text: str):
        print(f"🤖 [춘식이] {text}")
        audio = await self.tts.text_to_speech_stream(text, self.gender.value)
        await self.player.add_audio(audio)

    def set_gender(self, gender: CandidateGender):
        self.gender = gender

    def start_playback(self):
        self.player.start()

    async def stop_playback(self):
        await self.player.stop()

# ✅ 테스트 실행
async def test():
    tts = RealtimeLLMToTTS(ELEVENLABS_API_KEY)
    tts.start_playback()
    try:
        await tts.speak_interviewer("안녕하세요, 자기소개 부탁드립니다.", InterviewerVoice.HYUK)
        await asyncio.sleep(1)
        await tts.speak_candidate("안녕하세요, 저는 문제 해결을 좋아하는 개발자입니다.")
        await asyncio.sleep(1)
        tts.set_gender(CandidateGender.MALE)
        await tts.speak_candidate("저는 남성 춘식이입니다. 반갑습니다.")
        await asyncio.sleep(2)
    finally:
        await tts.stop_playback()

if __name__ == "__main__":
    asyncio.run(test())
