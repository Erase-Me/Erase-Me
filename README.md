<div align="center">
  <h1>Erase Me - 개인정보 자동 마스킹 프로그램</h1>
</div>

<br/>

<div align="center">
  <img src="./Public/Main.png" alt="Main" style="border-radius: 10px;"/>
</div>

<br/>

---

## ✍️ 프로젝트 개요

- **프로젝트명:** Erase Me
- **프로젝트 기간:** 2025.03 ~ 2025.06
- **프로젝트 형태:** 교내 캡스톤 프로젝트
- **목표:** 생성형 AI 사용시 발생하는 무의식적인 개인정보 유출 방지
- **멤버:** 구자연, 김희정, 홍가을
- **개발언어:** Python

---

## ✍️ 프로젝트 소개

### 프로젝트 배경

일상생활 속에서 저희는 다음과 같은 문제점들을 발견했습니다.:

1. **일상생활 속 개인정보 노출** 
- 편리성 추구로 인한 무의식적인 개인정보 노출
- 지나친 AI 의존도

2. **코드 개발 중 개인정보 노출** 
- 코드에서 발생한 에러 검색 시 포함된 중요정보
- 코드 속 가리지 못한 중요한 키 값

3. **학습에 사용되는 개인정보** 
- ChatGPT 음성 모드의 대화 수집 사례
- OmniGPT에서 약 3만명의 정보 유출 사례
- DeepSeek의 정보 노출 사례
- AI의 불확실한 개인정보 처리 방식 

**Erase Me**는 위 문제를 해결하기 위해 UUID를 기반으로 한 마스킹 및 역마스킹 기능을 제공하고, OCR과 STT 모델을 활용하여 이미지 및 음성 마스킹을 제공하는 프로그램입니다.

---

## 🚀 주요 기능

1. **텍스트 마스킹** 
- Name Entity Recognition(Pororo)를 이용한 단어 인식 및 정규식 이용
- 이름, 이메일, 전화번호, 주민등록번호, 날짜, 시간, 장소, 기관 마스킹 가능
- 자동 마스킹 및 역마스킹 지원

2. **이미지 마스킹** 
- OCR(paddleOCR) 인식을 통한 분석 후 해당 부분 마스킹
- 자동 마스킹 및 첨부한 파일 마스킹 지원
- 마스킹 된 이미지를 저장하여 재사용 가능

3. **음성 마스킹**
- STT(Google Speech-to-Text API) 변환 후 텍스트 마스킹
- 정확도 및 속도 향상을 위한 분할 변환

4. **코드 모드**
- 코드 기반 텍스트와 이미지에 대한 마스킹 지원
- 코드 속 키 값, 디렉토리 사용자 명, 이메일 마스킹 가능

---

## 사용법
1. 코드 실행
``` Python
git clone https://github.com/Erase-Me/Erase-Me.git
cd Erase-Me/
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python main.py
```

2. 실행 프로그램 다운로드
- 우측 `release` 탭에서 다운로드 가능합니다.

---
