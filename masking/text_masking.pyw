import os
import sys
import json
import pyperclip
import time
import re
import uuid
import requests
import atexit
import psutil
from dotenv import load_dotenv

LOCK_FILE = "text_masking.lock"

def is_already_running():
    if not os.path.exists(LOCK_FILE):
        return False
    try:
        with open(LOCK_FILE, "r") as f:
            pid = int(f.read())
        if psutil.pid_exists(pid):
            print(f"⚠️ 이미 실행 중 (PID: {pid})")
            return True
    except:
        pass
    return False

def create_lock():
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base_path, relative_path)

load_dotenv(dotenv_path=resource_path(".env"))
server_url = os.getenv("TEXT_MASKING_SERVER_URL")
MASK_CACHE_FILE = "masking_record_text.json"

SELECTION_MASKING = {
    "이름": {"PERSON"},
    "날짜": {"DATE"},
    "시간": {"TIME"},
    "장소": {"LOCATION"},
    "기관": {"ORGANIZATION"},
    "이메일": {"EMAIL"},
    "전화번호": {"PHONE"},
    "주민등록번호": {"SSN"}
}
MASK_CACHE = {}

def save_mask_cache():
    with open(MASK_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(MASK_CACHE, f, ensure_ascii=False, indent=2)

def load_mask_cache():
    global MASK_CACHE
    if os.path.exists(MASK_CACHE_FILE):
        with open(MASK_CACHE_FILE, "r", encoding="utf-8") as f:
            MASK_CACHE = json.load(f)

def generate_uid():
    return str(uuid.uuid4())[:8]

def get_ner_result(text):
    try:
        response = requests.post(server_url, json={"text": text}, timeout=60)
        response.raise_for_status()
        return response.json()["ner_result"]
    except Exception as e:
        print(f"❌ 서버 요청 실패: {e}")
        return []
    
def load_mask_tags_from_selection(file="selected_fields.json"):
    if not os.path.exists(file):
        return set()
    with open(file, "r", encoding="utf-8") as f:
        user_selections = json.load(f)

    mask_tags = set()
    for sel in user_selections:
        mask_tags.update(SELECTION_MASKING.get(sel, set()))
    return mask_tags

def mask_text_with_cache(text):
    mask_tags = load_mask_tags_from_selection()
    result = get_ner_result(text)
    masked_text = text

    global MASK_CACHE

    if not MASK_CACHE:
        if os.path.exists(MASK_CACHE_FILE):
            with open(MASK_CACHE_FILE, "r", encoding="utf-8") as f:
                MASK_CACHE = json.load(f)

    def add_to_cache_and_replace(tag, word):
        for k, (t, v) in MASK_CACHE.items():
            if t == tag and v == word:
                return f"[{tag}_{k}]"
        uid = generate_uid()
        MASK_CACHE[uid] = (tag, word)
        return f"[{tag}_{uid}]"

    for word, tag in result:
        if tag in mask_tags and word in masked_text:
            masked_text = masked_text.replace(word, add_to_cache_and_replace(tag, word))

    if "EMAIL" in mask_tags:
        for email in re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', masked_text):
            masked_text = masked_text.replace(email, add_to_cache_and_replace("EMAIL", email))

    if "PHONE" in mask_tags:
        for phone in re.findall(r'01[016789]-\d{3,4}-\d{4}', masked_text):
            masked_text = masked_text.replace(phone, add_to_cache_and_replace("PHONE", phone))

    if "SSN" in mask_tags:
        for ssn in re.findall(r'\d{6}-\d{7}', masked_text):
            masked_text = masked_text.replace(ssn, add_to_cache_and_replace("SSN", ssn))

    save_mask_cache()
    return masked_text

def partial_unmask(text):
    global MASK_CACHE
    restored = text
    pattern = re.compile(r'\[([A-Z]+)_([a-f0-9]{8})\]')
    for tag, uid in pattern.findall(text):
        if uid in MASK_CACHE and MASK_CACHE[uid][0] == tag:
            word = MASK_CACHE[uid][1]
            restored = restored.replace(f"[{tag}_{uid}]", word)
    return restored

def main():
    print("📋 text_masking 클립보드 감시 중...")
    last_clip = pyperclip.paste()

    try:
        while True:
            current_clip = pyperclip.paste()

            if current_clip.strip() == "":
                time.sleep(0.3)
                continue

            if current_clip != last_clip:
                if re.search(r'\[([A-Z]+)_([a-f0-9]{8})\]', current_clip):
                    print("\n♻️ 마스킹된 텍스트 감지 → 역마스킹")
                    load_mask_cache()
                    restored = partial_unmask(current_clip)
                    pyperclip.copy(restored)
                    print("✅ 복원 후 클립보드에 저장됨:\n", restored)
                    last_clip = restored
                    continue

                print("\n🔍 새 복사 감지!\n", current_clip)
                masked = mask_text_with_cache(current_clip)
                pyperclip.copy(masked)
                print("✅ 마스킹 후 클립보드에 저장됨:\n", masked)
                last_clip = masked

            time.sleep(0.5)

    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    if is_already_running():
        sys.exit()
    create_lock()
    atexit.register(remove_lock)
    main()
