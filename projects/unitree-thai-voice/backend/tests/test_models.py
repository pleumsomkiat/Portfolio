import pytest
from pydantic import ValidationError

from backend.app.models import ChatRequest


@pytest.mark.parametrize("message", ["", "   ", "\n\t", "ก" * 2001])
def test_invalid_questions_are_rejected(message):
    with pytest.raises(ValidationError):
        ChatRequest(message=message)


def test_question_is_trimmed_without_changing_thai_text():
    request = ChatRequest(message="  สวัสดี G1 ครับ \n")
    assert request.message == "สวัสดี G1 ครับ"
