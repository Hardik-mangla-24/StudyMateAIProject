import json
import re

from google.genai import types


def generate_quiz(client, chunks, num_questions=5):

    if not chunks:
        raise ValueError(
            "Please upload and process a PDF first."
        )

    if not 1 <= num_questions <= 20:
        raise ValueError(
            "Question count must be between 1 and 20."
        )

    context = "\n\n".join(chunks)

    # Context limit
    context = context[:30000]

    prompt = f"""
You are an educational MCQ quiz generator.

Generate exactly {num_questions} MCQ questions
using ONLY the PDF content below.

Rules:
1. Every question must have exactly 4 options.
2. Only one option can be correct.
3. Questions must be clear and educational.
4. Do not invent facts.
5. Give a short explanation for every question.
6. Avoid duplicate questions.

Return JSON in this structure:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": 0,
      "explanation": "Explanation"
    }}
  ]
}}

IMPORTANT:
- answer must be an integer from 0 to 3.
- Return exactly {num_questions} questions.
- Return JSON only.

PDF CONTENT:
{context}
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
        )

    except Exception as e:

        raise RuntimeError(
            f"Gemini Quiz API Error: {str(e)}"
        )

    result = response.text

    if not result:
        raise ValueError(
            "Gemini returned an empty response."
        )

    result = result.strip()

    # Remove markdown code fences if present
    result = re.sub(
        r"^```(?:json)?\s*",
        "",
        result,
        flags=re.IGNORECASE
    )

    result = re.sub(
        r"\s*```$",
        "",
        result
    )

    try:

        data = json.loads(result)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Invalid Gemini JSON response: {e}"
        )

    if not isinstance(data, dict):
        raise ValueError("Invalid quiz response format.")

    questions = data.get("questions")

    if not isinstance(questions, list):
        raise ValueError("Questions list not found.")

    if len(questions) != num_questions:
        raise ValueError(
            f"Expected {num_questions} questions, "
            f"received {len(questions)}."
        )

    seen_questions = set()

    for index, question_data in enumerate(questions):

        if not isinstance(question_data, dict):
            raise ValueError(
                f"Invalid question at position {index + 1}."
            )

        question = question_data.get("question")

        options = question_data.get("options")

        answer = question_data.get("answer")

        explanation = question_data.get("explanation")

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question text is missing.")

        normalized_question = question.strip().lower()

        if normalized_question in seen_questions:
            raise ValueError("Duplicate questions detected.")

        seen_questions.add(normalized_question)

        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(
                "Every question must have exactly 4 options."
            )

        if not all(
            isinstance(option, str) and option.strip()
            for option in options
        ):
            raise ValueError("Invalid option text.")

        normalized_options = [
            option.strip().lower()
            for option in options
        ]

        if len(set(normalized_options)) != 4:
            raise ValueError("Duplicate options detected.")

        if (
            not isinstance(answer, int)
            or isinstance(answer, bool)
            or answer not in range(4)
        ):
            raise ValueError(
                "Correct answer must be an index from 0 to 3."
            )

        if (
            not isinstance(explanation, str)
            or not explanation.strip()
        ):
            raise ValueError("Question explanation is missing.")

    return questions