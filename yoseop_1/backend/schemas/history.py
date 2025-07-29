from pydantic import BaseModel

class InterviewHistoryResponse(BaseModel):
    detail_id: int
    interview_id: int
    who: str
    question_index: int
    question_id: int
    question_content: str
    question_intent: str
    question_level: str
    answer: str
    feedback: str
    sequence: int
    duration: int

