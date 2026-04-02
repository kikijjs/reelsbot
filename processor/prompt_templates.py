"""
Claude 스크립트 생성용 프롬프트 템플릿.

페르소나와 작성 전략, 5파트 출력 형식을 정의한다.
"""

PERSONA = """
너는 인스타그램 릴스, 틱톡, 유튜브 쇼츠의 조회수를 폭발시키고
소비자 심리학을 꿰뚫고 구매 전환까지 이끌어내는 '1% 숏폼 전략가'야.

단순히 제품을 설명하는 게 아니라, 시청자가 이 정보를 모르면 '손해'를
본다고 느끼게 하거나, 이 제품 하나로 '압도적 이득'을 얻을 수 있다는
확신을 주는 스크립트를 써야 해.

제품의 '기능'이 아니라 그 제품이 가져다주는 '정서적 해방감'과
'시간/에너지의 보상'을 파악하는 카피라이터야.

[작성 전략]
- 과거의 고통 강조: 제품이 없었을 때의 짜증, 낭비되는 시간을 묘사
- 반전의 쾌감: "이렇게 쉬운 걸 왜 몰랐지?"라는 해방감 표현
- 말투: "~하네요", "~몰라요" 같은 친근한 구어체
""".strip()

OUTPUT_FORMAT = """
아래 JSON 형식으로만 답변해. 다른 텍스트는 절대 포함하지 마.

{
  "cover_text": "커버 문구 — 결핍·이득·호기심 중 하나를 건드려 1초 만에 클릭하게 만드는 짧고 강렬한 텍스트 (10~20자)",
  "hook": "후킹 — 첫 3초 안에 시선 강탈. 질문형 또는 충격적 사실 또는 공감 불편함. '나만 몰랐어?', '이거 하나로 끝' 류의 강력한 도입부 (2~3문장)",
  "body": "공감 및 해결 — 제품 특징이 아닌 편익(Benefit)에 집중. 구체적 상황 묘사 (3~5문장)",
  "cta": "CTA — 댓글 유도 또는 프로필 링크 클릭 유도. 자연스럽고 강력하게 (1~2문장)",
  "subtitle_timeline": [
    {"text": "자막 텍스트", "start_sec": 0, "end_sec": 2},
    {"text": "자막 텍스트", "start_sec": 2, "end_sec": 5}
  ]
}

subtitle_timeline 규칙:
- cover_text: 0~3초
- hook: 3~8초
- body: 8~25초 (내용 길이에 따라 여러 줄 분할)
- cta: 25~30초
- 각 자막은 2~5초 단위로 분할해서 읽기 편하게
""".strip()


def build_script_prompt(analysis: dict, emotion_strategy: str = "") -> str:
    """
    Gemini 분석 JSON을 바탕으로 Claude에게 전달할 스크립트 생성 프롬프트를 조립한다.

    Args:
        analysis: GeminiAnalysis.model_dump() 결과
        emotion_strategy: 감정 전략 힌트 (A/B 테스트 시 버전별로 다르게 지정)
                          비어있으면 analysis의 target_emotion 사용
    """
    target_emotion = emotion_strategy or analysis.get("target_emotion", "이득강조")

    analysis_block = f"""
[제품 분석 데이터]
- 제품명: {analysis.get("product_name", "")}
- 시각적 특징: {", ".join(analysis.get("visual_features", []))}
- 사용 장면: {analysis.get("use_case_scene", "")}
- 사용자 고통 포인트: {", ".join(analysis.get("user_pain_points", []))}
- 차별점: {", ".join(analysis.get("product_differentiators", []))}
- 정서적 혜택: {analysis.get("emotional_benefit", "")}
- 감정 전략: {target_emotion}
""".strip()

    strategy_hint = {
        "손실회피": "시청자가 이걸 모르면 손해라는 느낌, 지금까지 낭비한 시간/돈에 대한 아쉬움을 자극해.",
        "이득강조": "이 제품으로 얻는 압도적 이득과 삶의 변화를 구체적으로 강조해. 갖고 싶다는 욕구를 자극해.",
        "호기심": "시청자가 '이게 뭐지?', '어떻게 이게 가능해?'라는 호기심을 느끼게 만들어. 반전을 활용해.",
    }.get(target_emotion, "")

    return f"""{PERSONA}

{analysis_block}

[감정 전략 힌트]
{strategy_hint}

[출력 형식]
{OUTPUT_FORMAT}"""


def build_ab_prompt_pair(analysis: dict) -> tuple[str, str]:
    """
    A/B 테스트용 프롬프트 2개를 생성한다.

    Returns:
        (prompt_a, prompt_b)
        - A버전: analysis의 target_emotion 그대로 사용
        - B버전: 나머지 감정 전략 중 하나 사용
    """
    primary = analysis.get("target_emotion", "이득강조")

    # B버전은 primary와 다른 전략 선택
    all_emotions = ["손실회피", "이득강조", "호기심"]
    alternatives = [e for e in all_emotions if e != primary]
    secondary = alternatives[0]  # 순서상 첫 번째 대안 선택

    prompt_a = build_script_prompt(analysis, emotion_strategy=primary)
    prompt_b = build_script_prompt(analysis, emotion_strategy=secondary)

    return prompt_a, prompt_b
