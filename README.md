# Ori: 글 구조화

영어나 국어 글을 붙여넣으면 Claude가 글의 구조를 정리해 주는 웹 앱입니다.

- **주제·요지·요약**
- **문단별 요약**: 문단 역할(도입/주장/근거/예시/반론/결론 등), 한 줄 요약, 원문 중심 문장
- **논리 흐름**: 주장 → 근거 → 예시 → 반론 → 결론을 순서대로, 각 항목이 나온 문단 번호와 함께
- **개요**: I. / 1. / - 형식의 계층 개요
- **핵심어·어휘**: 핵심 용어 설명, 영어 단어·숙어나 어려운 한자어의 뜻
- 결과를 Markdown으로 복사하거나 JSON으로 저장할 수 있습니다.

## 실행

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # https://console.anthropic.com 에서 발급
uvicorn app:app --reload
```

브라우저에서 http://localhost:8000 을 열면 됩니다.

## 구성

| 파일 | 역할 |
|---|---|
| `structurer.py` | 문단 분리, Claude 호출(JSON 스키마로 출력 형식 고정) |
| `app.py` | FastAPI 서버 (`/` 화면, `POST /api/structure`) |
| `static/index.html` | 입력창과 결과 화면 |

모델은 `claude-opus-5-5`를 쓰며, 출력 형식은 `structurer.py`의 `STRUCTURE_SCHEMA`로 고정되어 있습니다.

## 태블릿·휴대폰에서 쓰기

`artifact/ori.html`은 claude.ai 아티팩트로 올린 버전입니다. 서버나 API 키 없이 claude.ai에 로그인한 브라우저에서 바로 열립니다.
글 분석은 내 Claude 계정 사용량으로 처리되며, 처음 쓸 때 Claude 사용을 허용할지 묻습니다.

- 링크: https://claude.ai/artifact/6WW7eb8HUUJLUHUu3GMdAf
