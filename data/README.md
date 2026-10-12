# 평가 데이터

최종 태스크가 정해진 뒤 직접 작성할 평가 사례를 관리합니다. 현재 실제 평가 데이터는 없습니다.

사례별 권장 필드:
- case_id, category, user_request
- initial_state / available_evidence
- gold_answer_or_state / required_constraints
- evaluation_rule / tolerance
- source / authoring_note / review_status

정답은 평가기에만 제공하고 해결 Agent의 입력에서 제외합니다.
개발용 사례와 고정 평가본을 구분합니다. 같은 기본 사례에서 만든 변형을 독립 사례로 중복 계산하지 않습니다.
공개 전 개인정보·저작권·공유 권한을 확인합니다. 원본 대용량 자료는 raw/ 등에 두고 Git에 올리지 않습니다.
