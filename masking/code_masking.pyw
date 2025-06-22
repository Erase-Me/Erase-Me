import os
import json
import re
import sys
import pyperclip
import uuid
import time
import atexit
import psutil

masking_map = {}
_terminal_cache = {}
MASK_CACHE_FILE = "masking_record_code.json"

LOCK_FILE = "code_masking.lock"

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

def save_mask_cache():
    with open(MASK_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(masking_map, f, ensure_ascii=False, indent=2)

def load_mask_cache():
    global masking_map
    if os.path.exists(MASK_CACHE_FILE):
        with open(MASK_CACHE_FILE, "r", encoding="utf-8") as f:
            masking_map = json.load(f)

def generate_placeholder(label):
    return f"{label.upper()}_{uuid.uuid4().hex[:8]}"

def is_already_masked(value: str):
    return re.match(r'(KEY|URL|TOKEN|SECRET|USER|HOST|PATH)_[0-9a-f]{8}', value) is not None

def mask_and_store(label, origin_value):
    global masking_map

    if is_already_masked(origin_value):
        return origin_value

    load_mask_cache()

    for placeholder, original in masking_map.items():
        if original == origin_value:
            return placeholder

    placeholder = generate_placeholder(label)
    masking_map[placeholder] = origin_value
    save_mask_cache()
    return placeholder

def is_sensitive_value(value: str):
    if re.match(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', value):
        return "email"
    if value.startswith("http"):
        return "url"
    if len(value) >= 8 and not value.isdigit():
        return "key"
    return None

def extract_url(text: str):
    pattern = r'((?:\w+\.)*\w+)\s*=\s*["\'](https?://[^\s"\']+)["\']'
    def replacer(match):
        key, value = match.group(1), match.group(2)
        label = is_sensitive_value(value)
        if label:
            placeholder = mask_and_store(label, value)
            return f'{key} = "{placeholder}"'
        return match.group(0)
    return re.sub(pattern, replacer, text)

def extract_keys(text: str):
    pattern = re.compile(r'((?:\w+\.)*\w*(KEY|TOKEN|SECRET)\w*)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    def replacer(match):
        keys, value = match.group(1), match.group(3)
        label = is_sensitive_value(value)
        if label:
            placeholder = mask_and_store(label, value)
            return f'{keys} = "{placeholder}"'
        return match.group(0)
    return re.sub(pattern, replacer, text)

def extract_email(text: str):
    pattern = re.compile(r'(["\'])([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(["\'])')
    
    def replacer(match):
        quote1, email, quote2 = match.groups()
        placeholder = mask_and_store("email", email)
        return f'{quote1}{placeholder}{quote2}'
    
    return pattern.sub(replacer, text)

def extract_define_Clang(text: str):
    pattern = re.compile(r'#define\s+(\w*(key|token|secret|url)\w*)\s+["\']([^"\']+)["\']', re.IGNORECASE)
    def replacer(match):
        key, value = match.group(1), match.group(3)
        label = is_sensitive_value(value)
        if label:
            placeholder = mask_and_store(label, value)
            return f'#define {key} "{placeholder}"'
        return match.group(0)
    return re.sub(pattern, replacer, text)

def extract_env_style(text: str):
    pattern = re.compile(r'(["\']?\w*(KEY|TOKEN|SECRET|URL)\w*["\']?)\s*[:=]\s*["\'](https?://[^\s"\']+|[^"\']{8,})["\']', re.IGNORECASE)
    def replacer(match):
        key, value = match.group(1), match.group(3)
        label = is_sensitive_value(value)
        if label:
            placeholder = mask_and_store(label, value)
            return f'{key}="{placeholder}"'
        return match.group(0)
    return re.sub(pattern, replacer, text)

def mask_terminal(code) :
    lines = code.splitlines()
    masked_lines = []
    for line in lines :
        if line in _terminal_cache:
            masked_lines.append(_terminal_cache[line])
            continue
        origin_line = line
        line = mask_file_paths(line)
        
        mac_match = re.search(r"\((.*?)\)\s+(\w+)@([\w\-]+)\s+(.*?)\s*%",origin_line)
        if mac_match :
            env = mac_match.group(1)
            user = mac_match.group(2)
            host = mac_match.group(3)
            directory = mac_match.group(4).strip()
            
            masked_user = mask_and_store("user", user)
            masked_host = mask_and_store("host", host)
            masked_dir = mask_and_store("dir", directory)
            # % 이후 텍스트 추출
            # % 이후 텍스트 추출
            split_percent = origin_line.split("%", 1)
            post_percent = split_percent[1].strip() if len(split_percent) > 1 else ""
            # post_percent도 파일 경로 포함 가능 → 마스킹 처리
            masked_post = mask_file_paths(post_percent) if post_percent else ""
            masked_line = f"({env}) {masked_user}@{masked_host} {masked_dir} %"
            if masked_post:
                masked_line += f" {masked_post}"
            _terminal_cache[origin_line] = masked_line
            masked_lines.append(masked_line)
            continue
    
        win_match = re.match(r"([A-Z]):\\Users\\([^\\]+)\\(.+)>", line)
        if win_match :
            drive = win_match.group(1)
            user = win_match.group(2)
            path = win_match.group(3)
            
            masked_user = mask_and_store("user", user)
            masked_path = mask_and_store("path", path.replace("\\", "/"))
            print("User's WindowOS")
            masked_line = f"{drive}:\\Users\\{masked_user}\\{masked_path.replace('\\', '/')}>"
            _terminal_cache[line] = masked_line
            masked_lines.append(masked_line)
            continue
        
        masked_lines.append(line)
        
    return "\n".join(masked_lines)

def multi_mask(text: str, max_iter=10):
    prev = None
    current = text
    count = 0
    while prev != current and count < max_iter:
        prev = current
        current = extract_url(current)
        current = extract_keys(current)
        current = extract_define_Clang(current)
        current = extract_env_style(current)
        current = extract_email(current)
        count += 1
    return current

def unmask(text: str):
    load_mask_cache()
    for placeholder, original in masking_map.items():
        text = text.replace(placeholder, original)
    return text

def has_masked_placeholder(text: str):
    return bool(re.search(r'(KEY|URL|TOKEN|SECRET|USER|HOST|PATH)_[0-9a-f]{8}', text))

def mask_file_paths(text):
    unix_pattern = re.compile(r'(/Users/[^ \n\r\t]*)')
    text = unix_pattern.sub(lambda m: mask_path_full(m.group(0)), text)
    win_pattern = re.compile(r'([A-Z]:\\Users\\[^\\\s]+(?:\\[^\\\s]+)*)')
    def win_replacer(m):
        path_slash = m.group(0).replace('\\', '/')
        masked = mask_path_full(path_slash)
        return masked.replace('/', '\\')
    text = win_pattern.sub(win_replacer, text)
    return text

def mask_path_full(path):
    
    parts = path.strip('/').split('/')
    if len(parts) < 2:
        return path  
    prefix = parts[0]
    user = parts[1]
    user_mask = mask_and_store("user", user)
    if len(parts) > 2:
        rest_path = '/'.join(parts[2:])
        folder_file_mask = mask_and_store("folder__file", rest_path)
    else:
        folder_file_mask = ""
    if folder_file_mask:
        return f"/{prefix}/{user_mask}/{folder_file_mask}"
    else:
        return f"/{prefix}/{user_mask}"
    
def main():
    print("📋 code_masking 클립보드 감시 시작...")
    last_clip = pyperclip.paste()

    try:
        while True:
            current_clip = pyperclip.paste()

            if current_clip.strip() == "":
                time.sleep(0.3)
                continue

            if current_clip != last_clip:
                if has_masked_placeholder(current_clip):
                    print("\n♻️ 마스킹된 텍스트 감지 → 역마스킹")
                    load_mask_cache()
                    restored = unmask(current_clip)
                    pyperclip.copy(restored)
                    print("✅ 복원 후 클립보드에 저장됨:\n", restored)
                    last_clip = restored
                    continue

                print("\n🔍 새 복사 감지!\n", current_clip)

                terminal_masked = mask_terminal(current_clip)
                fully_masked = multi_mask(terminal_masked)

                if fully_masked != current_clip:
                    print("✅ 마스킹 적용됨 → 클립보드에 저장:\n", fully_masked)
                    pyperclip.copy(fully_masked)
                    last_clip = fully_masked
                else:
                    print("⚠️ 마스킹할 항목 없음 → 원본 유지")
                    last_clip = current_clip

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