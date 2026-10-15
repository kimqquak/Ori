"""Sends text to Claude and returns its structure (theme, paragraph summaries, logical flow, outline, keywords) as JSON."""

import json
import re

import anthropic

MODEL = "claude-opus-5-5"

PARAGRAPH_ROLES = ["도입", "문제 제기", "주장", "근거", "예시", "부연", "반론", "재반박", "전환", "결론"]
FLOW_TYPES = ["주장", "근거", "예시", "반론", "재반박", "결론"]

STRUCTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"type": "string", "enum": ["ko", "en", "mixed"]},
        "title": {"type": "string", "description": "글에 어울리는 짧은 제목"},
        "topic": {"type": "string", "description": "글의 주제 (명사구)"},
        "main_idea": {"type": "string", "description": "글쓴이가 전달하려는 요지 한 문장"},
        "summary": {"type": "string", "description": "전체 내용 3~4문장 요약"},
        "paragraphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "role": {"type": "string", "enum": PARAGRAPH_ROLES},
                    "summary": {"type": "string", "description": "문단 핵심 한 줄"},
                    "key_sentence": {"type": "string", "description": "원문에서 그대로 가져온 중심 문장"},
                },
                "required": ["index", "role", "summary", "key_sentence"],
                "additionalProperties": False,
            },
        },
        "logic_flow": {
            "type": "array",
            "description": "글의 논리 전개를 순서대로",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": FLOW_TYPES},
                    "content": {"type": "string"},
                    "sentences": {
                        "type": "array",
                        "description": "근거가 된 원문 문장 번호 (예: \"2-1\")",
                        "items": {"type": "string"},
                    },
                },
                "required": ["type", "content", "sentences"],
                "additionalProperties": False,
            },
        },
        "outline": {
            "type": "array",
            "description": "I. / 1. / (1) 형식의 계층 개요",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "details": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["text", "details"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["heading", "points"],
                "additionalProperties": False,
            },
        },
        "keywords": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "explanation": {"type": "string", "description": "이 글에서의 의미/역할"},
                },
                "required": ["term", "explanation"],
                "additionalProperties": False,
            },
        },
        "vocabulary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "meaning": {"type": "string", "description": "한국어 뜻"},
                    "context": {"type": "string", "description": "원문에서 쓰인 구절"},
                },
                "required": ["word", "meaning", "context"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "language", "title", "topic", "main_idea", "summary",
        "paragraphs", "logic_flow", "outline", "keywords", "vocabulary",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """너는 국어·영어 독해를 가르치는 선생님이다. 학생이 글의 구조를 한눈에 파악할 수 있도록 글을 분석한다.

- 원문 언어와 관계없이 모든 설명은 한국어로 쓴다. 단, key_sentence와 vocabulary의 word/context는 원문 그대로 둔다.
- 문단은 [1], [2] 처럼, 문단 안의 문장은 {2-1}, {2-2} 처럼(2문단 1번째, 2번째 문장) 번호가 붙어 주어진다. paragraphs에는 모든 문단을 빠짐없이 그 번호로 넣는다.
- logic_flow는 글 전체의 논증 흐름(주장→근거→예시…)을 순서대로 정리한다. 논설문이 아닌 글(설명문, 서사 등)이면 중심 내용과 그것을 뒷받침하는 내용으로 흐름을 잡는다.
- logic_flow는 문장 단위로 뽑는다. 특히 근거와 예시는 원문 문장 하나가 한 항목이 되도록 나누고, 한 문단에 근거 문장이 여럿이면 각각 따로 항목을 만든다. 각 항목의 sentences에는 그 내용이 나온 원문 문장 번호(예: "2-1")를 넣는다. 번호는 주어진 것만 쓴다.
- outline은 2~5개의 큰 항목으로 나누고, 원문에 없는 내용을 지어내지 않는다.
- keywords는 글의 이해에 핵심인 용어 3~8개.
- vocabulary는 영어 글이면 수준 있는 단어·숙어 5~12개, 국어 글이면 어려운 한자어·개념어 3~10개. 해당하는 것이 없으면 빈 배열."""


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; if the text has none, fall back to single line breaks."""
    text = text.replace("\r\n", "\n").strip()
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(parts) == 1:
        parts = [p.strip() for p in text.split("\n") if p.strip()]
    return parts


_ABBREV = re.compile(r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|St|vs|etc|e\.g|i\.e|U\.S|No)\.|\b[A-Z]\.)$")


def split_sentences(paragraph: str) -> list[str]:
    """Split after . ! ? … (optionally followed by a closing quote/bracket), keeping common abbreviations intact."""
    pieces = re.split(r"(?<=[.!?…])\s+|(?<=[.!?…][\"'”’)])\s+", paragraph.strip())
    sentences: list[str] = []
    for piece in pieces:
        if sentences and _ABBREV.search(sentences[-1]):
            sentences[-1] += " " + piece
        elif piece:
            sentences.append(piece)
    return sentences


class StructureError(Exception):
    pass


def structure_text(text: str, client: anthropic.Anthropic | None = None) -> dict:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        raise StructureError("분석할 글이 비어 있습니다.")

    sentences = [split_sentences(p) for p in paragraphs]
    numbered = "\n\n".join(
        f"[{i}] " + " ".join(f"{{{i}-{j}}} {sent}" for j, sent in enumerate(sents, 1))
        for i, sents in enumerate(sentences, 1)
    )
    client = client or anthropic.Anthropic()

    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": STRUCTURE_SCHEMA},
        },
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"다음 글을 구조화해 줘.\n\n<text>\n{numbered}\n</text>"}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise StructureError("모델이 이 글의 분석을 거절했습니다.")
    if response.stop_reason == "max_tokens":
        raise StructureError("글이 너무 길어 결과가 잘렸습니다. 글을 나눠서 넣어 주세요.")

    raw = next(b.text for b in response.content if b.type == "text")
    result = json.loads(raw)
    result["source_paragraphs"] = paragraphs
    result["source_sentences"] = sentences
    return result
