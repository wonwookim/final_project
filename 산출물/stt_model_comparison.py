import os
from dotenv import load_dotenv

# ============================
# 🔹 환경 변수 로드
# ============================
load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_INVOKE_URL = os.getenv("NAVER_INVOKE_URL")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID")
TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
TENCENT_REGION = os.getenv("TENCENT_REGION")  # 기본값: 서울 리전

# ============================
# 🔹 Whisper 변환 함수 (미국)
# ============================
import openai
import os
import re
from dotenv import load_dotenv

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def transcribe_whisper(audio_path, language="ko"):
    try:
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="text"
            )

        text = response.strip()

        # 구두점 제거
        text_no_punct = re.sub(r'[^\w\s\uAC00-\uD7A3]', '', text)

        return text_no_punct

    except Exception as e:
        print(f"OpenAI Whisper API 오류 ({audio_path}): {e}")
        return ""

# ============================
# 🔹 ElevenLabs 변환 함수 (유럽)
# ============================
from elevenlabs import ElevenLabs

def transcribe_elevenlabs(audio_path, language="ko"):
    try:
        client = ElevenLabs(api_key = ELEVENLABS_API_KEY)
        with open(audio_path, "rb") as f:
            resp = client.speech_to_text.convert(
                file=f,
                model_id="scribe_v1",
                language_code=language,
                diarize=False,
                tag_audio_events=False
            )
        # ✅ 응답 객체 안전하게 처리
        if hasattr(resp, "text"):
            text = resp.text.strip()
        elif hasattr(resp, "to_dict"):
            text = resp.to_dict().get("text", "").strip()
        else:
            text = str(resp).strip()

        # 2) 구두점 제거: 알파벳·숫자·언더스코어(\w), 공백(\s), 한글(\uAC00-\uD7A3)만 남김
        text_no_punct = re.sub(r'[^\w\s\uAC00-\uD7A3]', '', text)

        return text_no_punct

    except Exception as e:
        print(f"ElevenLabs 오류 ({audio_path}): {e}")
        return ""


# ============================
# 🔹 Naver Clova STT 변환 함수 (한국)
# ============================
import requests

def transcribe_clova(audio_path):
    url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY":    NAVER_CLIENT_SECRET,
        "Content-Type":           "application/octet-stream",
    }
    params = {"lang": "Kor"}  # 반드시 Kor 대문자로

    with open(audio_path, "rb") as f:
        resp = requests.post(
            url,
            headers=headers,
            params=params,
            data=f,
            timeout=30
        )

    if resp.status_code != 200:
        return ""  # 여전히 404나오면 URL이 잘못된 것이니 바로 확인

    # 성공 시 JSON 파싱
    try:
        return resp.json().get("text", "").strip()
    except ValueError:
        # JSON 파싱 실패 시, plain text 로 리턴
        return resp.text.strip()

# ============================
# 🔹 Tencent Cloud STT 변환 함수 (중국)
# ============================
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.asr.v20190614 import asr_client, models
import base64
import re
import json

def transcribe_tencent(audio_path, language="ko"):
    try:
        cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY)
        http_profile = HttpProfile()
        http_profile.endpoint = "asr.tencentcloudapi.com"

        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = asr_client.AsrClient(cred, TENCENT_REGION, client_profile)

        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()

        req = models.SentenceRecognitionRequest()
        params = {
            "ProjectId": 0,
            "SubServiceType": 2,
            "EngSerViceType": "16k_ko",
            "SourceType": 1,
            "VoiceFormat": "m4a",
            "UsrAudioKey": "session_123",
            "Data": base64.b64encode(audio_data).decode()
        }
        req.from_json_string(json.dumps(params))

        resp = client.SentenceRecognition(req)
        text = resp.Result.strip()

        # 구두점 제거
        text_no_punct = re.sub(r'[^\w\s\uAC00-\uD7A3]', '', text)

        return text_no_punct

    except Exception as e:
        print(f"Tencent Cloud STT 오류 ({audio_path}): {e}")
        return ""

# ============================
# 🔹 QWEN STT 변환 함수 (중국)
# ============================
import requests

def transcribe_qwen(audio_path, language="ko"):
    QWEN_ENDPOINT = "https://api.qwen.ai/v1/stt"  # 실제 endpoint로 변경해야 함

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Accept": "application/json",
    }

    with open(audio_path, "rb") as audio_file:
        files = {"file": (os.path.basename(audio_path), audio_file, "audio/wav")}
        data = {"language": language}

        try:
            response = requests.post(
                QWEN_ENDPOINT,
                headers=headers,
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # API의 응답 구조에 따라 조정 필요
            text = result.get("text", "").strip()

            # 구두점 제거
            text_no_punct = re.sub(r'[^\w\s\uAC00-\uD7A3]', '', text)

            return text_no_punct

        except requests.RequestException as e:
            print(f"Qwen API 오류 ({audio_path}): {e}")
            return ""

        except ValueError as e:
            print(f"Qwen API JSON 오류 ({audio_path}): {e}")
            return ""

# ============================
# 🔹 평가 유틸
# ============================
import jiwer

def evaluate_wer(reference: str, hypothesis: str) -> float:
    """
    - reference, hypothesis 양쪽이 빈 문자열인 경우 WER=0.0
    - reference 빈 문자열이지만 hypothesis non-empty인 경우 WER=1.0
    - 그렇지 않으면 jiwer.wer() 결과 그대로 반환
    """
    # 1) 둘 다 빈 문자열 → 틀린 게 없으므로 0.0
    if not reference and not hypothesis:
        return 0.0

    # 2) reference 빈 문자열만 → 모든 단어가 insertion, WER=1.0로 간주
    if not reference:
        return 1.0

    # 3) hypothesis 빈 문자열만 → 모든 단어가 deletion, WER=1.0
    if not hypothesis:
        return 1.0

    # 4) 정상 케이스
    try:
        return jiwer.wer(reference, hypothesis)
    except Exception as e:
        # 필요하다면 로깅
        print(f"WER 계산 오류: {e}")
        # 에러 났을 때 fallback 값—원하시면 예외를 다시 던져도 무방
        return 1.0

from jiwer import process_words

def evaluate_accuracy(reference: str, hypothesis: str) -> float:
    """
    ASR 정확도 = hits / (hits + substitutions + deletions)
    (reference 빈 문자열인 경우엔 0.0, 둘 다 빈 문자열인 경우엔 1.0)
    """
    # 1) 둘 다 빈 문자열 → 1.0
    if not reference and not hypothesis:
        return 1.0

    # 2) reference만 빈 문자열 → 0.0
    if not reference:
        return 0.0

    # 3) process_words 로 word-level 통계 추출
    result = process_words(reference, hypothesis)
    hits = result.hits
    subs = result.substitutions
    dels = result.deletions

    # 4) 정확도 계산
    N = hits + subs + dels
    return hits / N

# ============================
# 🔹 배치 평가 파이프라인
# ============================
async def batch_evaluate(folder_path, language="ko"):
    results = []
    wav_files = [f for f in os.listdir(folder_path) if f.endswith(".m4a")]
    total = len(wav_files)
    print(f"총 {total}개 파일 처리 시작…")

    for idx, fname in enumerate(wav_files, 1):
        base = fname[:-4]
        audio = os.path.join(folder_path, fname)
        txt   = os.path.join(folder_path, base + ".txt")
        if not os.path.exists(txt):
            print(f"⚠️ {base}.txt 없음, 스킵")
            continue

        with open(txt, "r", encoding="utf-8") as f:
            ref = f.read().strip()

        # 1) Whisper
        print(f"  🎤 [{idx}/{total}] {base} - Whisper 처리 중...")
        hyp_wh = await transcribe_whisper(audio, language)
        
        # 2) ElevenLabs
        print(f"  🎤 [{idx}/{total}] {base} - ElevenLabs 처리 중...")
        hyp_el = transcribe_elevenlabs(audio, language)
        
        # 3) Naver Clova
        print(f"  🎤 [{idx}/{total}] {base} - Clova 처리 중...")
        hyp_cv = transcribe_clova(audio)

        # # 4) Qwen API
        # print(f"  🎤 [{idx}/{total}] {base} - Qwen API 처리 중...")
        # hyp_qwen = transcribe_qwen(audio, language)

        # 5) Tencent Cloud
        print(f"  🎤 [{idx}/{total}] {base} - Tencent Cloud 처리 중...")
        hyp_tc = transcribe_tencent(audio, language)
        
        wer_wh = evaluate_wer(ref, hyp_wh)
        wer_el = evaluate_wer(ref, hyp_el)
        wer_cv = evaluate_wer(ref, hyp_cv)
        # wer_qwen = evaluate_wer(ref, hyp_qwen)
        wer_tc = evaluate_wer(ref, hyp_tc)

        acc_wh = evaluate_accuracy(ref, hyp_wh)
        acc_el = evaluate_accuracy(ref, hyp_el)
        acc_cv = evaluate_accuracy(ref, hyp_cv)
        # acc_qwen = evaluate_accuracy(ref, hyp_qwen)
        acc_tc = evaluate_accuracy(ref, hyp_tc)

        results.append({
            "file": base,
            "reference": ref,
            "whisper": {"text": hyp_wh, "wer": wer_wh, "acc": acc_wh},
            "elevenlabs": {"text": hyp_el, "wer": wer_el, "acc": acc_el},
            "clova": {"text": hyp_cv, "wer": wer_cv, "acc": acc_cv},
            # "qwen": {"text": hyp_qwen, "wer": wer_qwen, "acc": acc_qwen}
            "tencent": {"text": hyp_tc, "wer": wer_tc, "acc": acc_tc}
        })

        # 결과 출력
        print(f"[{idx}/{total}] {base} 완료 → WER Whisper:{wer_wh:.2f}, ElevenLabs:{wer_el:.2f}, Clova:{wer_cv:.2f}, Tencent:{wer_tc:.2f}")


    # 결과 저장
    from datetime import datetime
    import json

    if results:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"stt_compare_{ts}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"💾 결과: {out}")
    else:
        print("❌ 처리된 파일 없음")

    return results

# ============================
# 🔹 실행부
# ============================
import asyncio

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    print("STT 모델 비교 시작")
    
    # Tencent Cloud ASR 제한 확인
    # check_tencent_asr_limits()
    # print()
    
    asyncio.run(batch_evaluate(data_dir))