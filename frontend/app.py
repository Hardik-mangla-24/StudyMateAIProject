
import os
import sys
from pathlib import Path
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from gtts import gTTS


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="StudyMate AI",
    page_icon="📚",
    layout="wide"
)

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add project root to Python import path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================
# 2. BACKEND IMPORTS
# ==========================================

from backend.auth import (
    register_user,
    authenticate_user
)

from backend.pdf_service import (
    extract_pdf_text,
    split_text
)

from backend.rag_service import (
    create_embeddings,
    search_relevant_chunks
)

from backend.quiz_service import generate_quiz

from backend.database import (
    create_tables,
    migrate_quiz_history,
    save_quiz_result,
    get_quiz_history
)


# ==========================================
# 3. ENVIRONMENT VARIABLES
# ==========================================

load_dotenv(PROJECT_ROOT / ".env")

# First check local environment variable
api_key = os.getenv("GOOGLE_API_KEY")

# If not found, check Streamlit Cloud Secrets
if not api_key:
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except (KeyError, FileNotFoundError):
        api_key = None

if not api_key:
    st.error(
        "Google API Key missing. "
        "Please configure GOOGLE_API_KEY in .env or Streamlit Secrets."
    )
    st.stop()


# ==========================================
# 4. GEMINI CLIENT
# ==========================================

try:

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            api_version="v1beta"
        )
    )

except Exception as e:

    st.error(f"Gemini Client Error: {e}")
    st.stop()


# ==========================================
# 5. DATABASE INITIALIZATION
# ==========================================

try:

    create_tables()

    migrate_quiz_history()

except Exception as e:

    st.error(f"Database Error: {e}")
    st.stop()


# ==========================================
# 6. SESSION STATE
# ==========================================

defaults = {

    "user": None,
    "chunks": [],
    "embeddings": [],
    "chat_history": [],
    "quiz_questions": [],
    "quiz_submitted": False,
    "quiz_saved": False,
    "quiz_version": 0,
    "quiz_source": None,
    "quiz_score": 0,
    "quiz_answers": {},
    "pdf_processed": False,
    "processed_pdf_name": None,
    "voice_language": "English"

}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# 7. RESET QUIZ FUNCTION
# ==========================================

def reset_quiz():

    keys_to_delete = [

        key for key in list(st.session_state.keys())

        if key.startswith("quiz_answer_")

    ]

    for key in keys_to_delete:
        del st.session_state[key]

    st.session_state.quiz_questions = []

    st.session_state.quiz_submitted = False

    st.session_state.quiz_saved = False

    st.session_state.quiz_score = 0

    st.session_state.quiz_answers = {}

    st.session_state.quiz_version += 1


# ==========================================
# 8. AUTHENTICATION PAGE
# ==========================================

def authentication_page():

    st.title("📚 StudyMate AI")

    st.subheader("Your Personal AI Study Assistant")

    st.write(
        "Create an account or login to access your AI study assistant."
    )

    st.divider()

    login_tab, register_tab = st.tabs(
        ["🔐 Login", "📝 Register"]
    )

    # --------------------------------------
    # LOGIN
    # --------------------------------------

    with login_tab:

        st.subheader("Welcome Back!")

        with st.form("login_form"):

            login_email = st.text_input(
                "Email Address",
                placeholder="Enter your email"
            )

            login_password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )

            login_button = st.form_submit_button(
                "Login",
                type="primary",
                use_container_width=True
            )

        if login_button:

            if not login_email.strip() or not login_password:

                st.warning("Please enter email and password.")

            else:

                try:

                    user = authenticate_user(
                        login_email,
                        login_password
                    )

                    if user:

                        st.session_state.user = user

                        st.success("Login successful!")

                        st.rerun()

                    else:

                        st.error("Invalid email or password.")

                except Exception as e:

                    st.error(f"Login Error: {e}")

    # --------------------------------------
    # REGISTRATION
    # --------------------------------------

    with register_tab:

        st.subheader("Create Your Account")

        with st.form("register_form"):

            register_name = st.text_input(
                "Full Name",
                placeholder="Enter your full name"
            )

            register_email = st.text_input(
                "Email Address",
                placeholder="Enter your email"
            )

            register_password = st.text_input(
                "Password",
                type="password",
                placeholder="Minimum 8 characters"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            register_button = st.form_submit_button(
                "Create Account",
                type="primary",
                use_container_width=True
            )

        if register_button:

            if not register_name.strip():

                st.warning("Please enter your full name.")

            elif not register_email.strip():

                st.warning("Please enter your email.")

            elif not register_password:

                st.warning("Please enter your password.")

            elif register_password != confirm_password:

                st.error("Passwords do not match.")

            elif len(register_password) < 8:

                st.warning("Password must contain at least 8 characters.")

            else:

                try:

                    success, message = register_user(
                        register_name,
                        register_email,
                        register_password
                    )

                    if success:

                        st.success(message)

                        st.info("Please login to continue.")

                    else:

                        st.error(message)

                except Exception as e:

                    st.error(f"Registration Error: {e}")


# ==========================================
# 9. LOGIN CHECK
# ==========================================

if st.session_state.user is None:

    authentication_page()

    st.stop()


# ==========================================
# 10. USER SIDEBAR
# ==========================================

logged_in_user = st.session_state.user

st.sidebar.title("📚 StudyMate AI")

st.sidebar.success(
    f"Welcome, {logged_in_user['full_name']}!"
)

st.sidebar.caption(
    logged_in_user["email"]
)

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()


# ==========================================
# 11. MAIN HEADER
# ==========================================

st.title("📚 StudyMate AI")

st.caption("Your Personal AI Study Assistant")

st.markdown("""
Upload your study PDF and use AI to:

- Understand your study material
- Ask questions from your PDF
- Listen to AI answers in Hindi or English
- Generate practice quizzes
- Track your learning progress
""")

st.divider()


# ==========================================
# 12. PDF UPLOAD
# ==========================================

st.header("📄 Upload Study Material")

uploaded_file = st.file_uploader(
    "Choose your PDF file",
    type=["pdf"],
    key="pdf_uploader"
)

process_button = st.button(
    "🚀 Process PDF",
    type="primary",
    disabled=uploaded_file is None
)


# ==========================================
# 13. PROCESS PDF
# ==========================================

if process_button and uploaded_file is not None:

    current_pdf_name = uploaded_file.name

    with st.spinner(
        "Reading PDF and creating AI embeddings..."
    ):

        try:

            pdf_bytes = uploaded_file.getvalue()

            pdf_text = extract_pdf_text(pdf_bytes)

            chunks = split_text(
                pdf_text,
                chunk_size=1000,
                overlap=200
            )

            if not chunks:

                st.error("No readable text found in PDF.")
                st.stop()

            embeddings = create_embeddings(
                client,
                chunks
            )

            if len(chunks) != len(embeddings):

                raise ValueError(
                    "PDF chunks and embeddings do not match."
                )

            st.session_state.chunks = chunks

            st.session_state.embeddings = embeddings

            st.session_state.pdf_processed = True

            st.session_state.quiz_source = current_pdf_name

            st.session_state.processed_pdf_name = current_pdf_name

            st.session_state.chat_history = []

            reset_quiz()

            st.success(
                f"PDF processed successfully! {len(chunks)} chunks created."
            )

        except Exception as e:

            st.error(f"PDF Processing Error: {e}")


# ==========================================
# 14. PDF STATUS
# ==========================================

if st.session_state.pdf_processed and st.session_state.chunks:

    st.success(
        f"📘 Current PDF: {st.session_state.processed_pdf_name}"
    )

    st.info(
        f"Total PDF chunks: {len(st.session_state.chunks)}"
    )

    st.divider()


# ==========================================
# 15. VOICE SETTINGS
# ==========================================

language_instruction = """
Answer in simple English suitable for a student.
"""

voice_code = "en"

if st.session_state.chunks:

    st.header("🔊 Voice Settings")

    voice_language = st.selectbox(
        "Select AI response language",
        options=["English", "Hindi"],
        index=(
            0 if st.session_state.voice_language == "English"
            else 1
        )
    )

    st.session_state.voice_language = voice_language

    if voice_language == "Hindi":

        language_instruction = """
        Answer in simple Hindi using Devanagari script.
        Keep important technical terms in English when needed.
        """

        voice_code = "hi"

    st.divider()


# ==========================================
# 16. CHAT WITH PDF
# ==========================================

if st.session_state.chunks:

    st.header("💬 Chat with Your PDF")

    st.caption(
        "Ask questions related to your uploaded study material."
    )

    for index, message in enumerate(
        st.session_state.chat_history
    ):

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

            if message["role"] == "assistant":

                if st.button(
                    "🔊 Play Voice",
                    key=f"voice_{index}"
                ):

                    try:

                        with st.spinner("Generating voice..."):

                            audio_buffer = BytesIO()

                            tts = gTTS(
                                text=message["content"],
                                lang=voice_code,
                                slow=False
                            )

                            tts.write_to_fp(audio_buffer)

                            audio_buffer.seek(0)

                            st.audio(
                                audio_buffer.getvalue(),
                                format="audio/mp3"
                            )

                    except Exception as e:

                        st.warning(
                            f"Voice generation failed: {e}"
                        )

    # --------------------------------------
    # QUESTION FORM
    # --------------------------------------

    with st.form(
        key="chat_form",
        clear_on_submit=True
    ):

        user_question = st.text_input(
            "✍️ Enter your question",
            placeholder="Example: What is Machine Learning?"
        )

        send_question = st.form_submit_button(
            "📩 Send Question",
            type="primary"
        )

    if send_question and user_question.strip():

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })

        try:

            with st.spinner("StudyMate AI is thinking..."):

                relevant_chunks = search_relevant_chunks(
                    client,
                    user_question,
                    st.session_state.chunks,
                    st.session_state.embeddings,
                    top_k=4
                )

                context = "\n\n".join(relevant_chunks)

                prompt = f"""
You are StudyMate AI, a helpful educational assistant.

Answer the student's question using the provided PDF context.

Instructions:
1. {language_instruction}
2. Explain concepts in a student-friendly way.
3. Use headings and bullet points when useful.
4. Give examples when helpful.
5. Do not invent facts.
6. If the answer is not available in the PDF,
   clearly tell the student.
7. Keep answers clear and easy to understand.

PDF CONTEXT:
{context}

STUDENT QUESTION:
{user_question}

ANSWER:
"""

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )

                answer = response.text

                if not answer:
                    answer = "Sorry, I could not generate an answer."

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer
                })

            st.rerun()

        except Exception as e:

            st.error(f"Chat Error: {e}")

    if st.button("🗑️ Clear Chat"):

        st.session_state.chat_history = []

        st.rerun()

    st.divider()


# ==========================================
# 17. QUIZ GENERATION
# ==========================================

if st.session_state.chunks:

    st.header("🎓 Test Your Knowledge")

    st.write(
        "Generate an MCQ quiz using your uploaded PDF."
    )

    number_of_questions = st.selectbox(
        "Select number of questions",
        options=[5, 10, 15, 20],
        index=1
    )

    if st.button(
        "📝 Generate Quiz",
        type="primary"
    ):

        with st.spinner("Generating your quiz..."):

            try:

                questions = generate_quiz(
                    client,
                    st.session_state.chunks,
                    number_of_questions
                )

                if not questions:

                    st.error("No questions generated.")

                else:

                    reset_quiz()

                    st.session_state.quiz_questions = questions

                    st.success(
                        f"{len(questions)} questions generated!"
                    )

                    st.rerun()

            except Exception as e:

                st.error(
                    f"Quiz Generation Error: {e}"
                )


# ==========================================
# 18. QUIZ FORM
# ==========================================

if st.session_state.quiz_questions:

    questions = st.session_state.quiz_questions

    quiz_version = st.session_state.quiz_version

    st.subheader("📋 Your Quiz")

    st.write(
        f"Total Questions: {len(questions)}"
    )

    if not st.session_state.quiz_submitted:

        with st.form(
            key=f"quiz_form_{quiz_version}"
        ):

            for i, question in enumerate(questions):

                st.markdown(
                    f"### Q{i + 1}. {question['question']}"
                )

                st.radio(
                    "Choose your answer:",
                    options=question["options"],
                    index=None,
                    key=f"quiz_answer_{quiz_version}_{i}"
                )

                st.write("")

            submit_quiz = st.form_submit_button(
                "✅ Submit Quiz",
                type="primary"
            )

        if submit_quiz:

            unanswered = []

            selected_answers = {}

            for i, question in enumerate(questions):

                answer_key = f"quiz_answer_{quiz_version}_{i}"

                selected_answer = st.session_state.get(
                    answer_key
                )

                if selected_answer is None:

                    unanswered.append(i + 1)

                else:

                    selected_answers[i] = selected_answer

            if unanswered:

                st.warning(
                    "Please answer all questions. "
                    f"Unanswered: {unanswered}"
                )

            else:

                score = 0

                for i, question in enumerate(questions):

                    selected_answer = selected_answers[i]

                    correct_index = question["answer"]

                    correct_text = question["options"][correct_index]

                    if (
                        selected_answer.strip().lower()
                        == correct_text.strip().lower()
                    ):

                        score += 1

                st.session_state.quiz_answers = selected_answers

                st.session_state.quiz_score = score

                if not st.session_state.quiz_saved:

                    try:

                        save_quiz_result(
                            user_id=logged_in_user["id"],
                            pdf_name=(
                                st.session_state.quiz_source
                                or "Unknown PDF"
                            ),
                            total_questions=len(questions),
                            correct_answers=score
                        )

                        st.session_state.quiz_saved = True

                    except Exception as e:

                        st.error(
                            f"Database save error: {e}"
                        )

                st.session_state.quiz_submitted = True

                st.rerun()


# ==========================================
# 19. QUIZ RESULTS
# ==========================================

if (
    st.session_state.quiz_questions
    and st.session_state.quiz_submitted
):

    questions = st.session_state.quiz_questions

    score = st.session_state.quiz_score

    total_questions = len(questions)

    percentage = (score / total_questions) * 100

    st.success("Quiz submitted successfully!")

    st.info("Your answers are locked.")

    st.header("🏆 Your Quiz Results")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Your Score",
            f"{score} / {total_questions}"
        )

    with col2:

        st.metric(
            "Percentage",
            f"{percentage:.2f}%"
        )

    with col3:

        st.metric(
            "Correct Answers",
            score
        )

    if percentage == 100:

        st.success("Excellent! Great performance! 🎉")

    elif percentage >= 70:

        st.success("Great job! Keep practicing. 🌟")

    elif percentage >= 40:

        st.warning("Good effort! Review your answers.")

    else:

        st.info("Keep learning. You will improve!")

    st.divider()

    st.subheader("📖 Answer Review")

    for i, question in enumerate(questions):

        correct_text = question["options"][question["answer"]]

        user_answer = st.session_state.quiz_answers.get(
            i,
            "Not answered"
        )

        st.markdown(
            f"### Q{i + 1}. {question['question']}"
        )

        st.write(f"**Your answer:** {user_answer}")

        st.write(f"**Correct answer:** {correct_text}")

        if (
            str(user_answer).strip().lower()
            == correct_text.strip().lower()
        ):

            st.success("Correct answer ✅")

        else:

            st.error("Incorrect answer ❌")

        explanation = question.get("explanation", "")

        if explanation:

            st.info(f"💡 Explanation: {explanation}")

        st.divider()

    if st.button("🔄 Generate New Quiz"):

        reset_quiz()

        st.rerun()


# ==========================================
# 20. PERSONAL LEARNING DASHBOARD
# ==========================================

st.header("📊 My Learning Dashboard")

try:

    history = get_quiz_history(
        logged_in_user["id"]
    )

    if history:

        history_data = [
            dict(row)
            for row in history
        ]

        total_quizzes = len(history_data)

        percentages = [
            float(row["score_percentage"])
            for row in history_data
        ]

        average_score = sum(percentages) / total_quizzes

        highest_score = max(percentages)

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Total Quizzes",
                total_quizzes
            )

        with col2:

            st.metric(
                "Average Score",
                f"{average_score:.2f}%"
            )

        with col3:

            st.metric(
                "Highest Score",
                f"{highest_score:.2f}%"
            )

        st.subheader("🗂️ My Quiz History")

        st.dataframe(
            history_data,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("📈 Quiz Performance")

        chart_data = {

            "Quiz": [
                f"Quiz {i + 1}"
                for i in range(total_quizzes)
            ],

            "Score (%)": percentages

        }

        st.line_chart(
            chart_data,
            x="Quiz",
            y="Score (%)"
        )

    else:

        st.info(
            "No quiz history available yet. "
            "Complete a quiz to see your progress."
        )

except Exception as e:

    st.error(f"Dashboard Error: {e}")


# ==========================================
# 21. FOOTER
# ==========================================

st.divider()

st.markdown(
    """
    <div style="text-align:center;">
        <h3>📚 StudyMate AI</h3>
        <p>Your Personal AI Study Assistant</p>
        <p>Created by Hardik Mangla</p>
    </div>
    """,
    unsafe_allow_html=True
)
