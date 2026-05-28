from backend.analytics import extract_score, history_stats
from backend.config import TEMP_AUDIO_PATH
from backend.database import openai_client


def generate_question(topic):
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "אתה מורה לעברית. חבר שאלה פתוחה אחת, קצרה, ברורה ומעניינת בעברית "
                    "לתלמיד בנושא המבוקש. החזר רק את השאלה נטו, ללא שום הקדמה, מרכאות או טקסט נוסף."
                ),
            },
            {"role": "user", "content": f"הנושא: {topic}"},
        ],
    )
    return response.choices[0].message.content


def get_examiner_feedback(student_text, question):
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    f"אתה בוחן לעברית. בדוק אם התשובה קשורה לשאלה, תקן שגיאות כתיב/תחביר אם יש, "
                    f"ותן ציון 1-10.\nסיים תמיד בשורה נפרדת בדיוק בפורמט: ציון: X/10\nהשאלה הייתה: {question}"
                ),
            },
            {"role": "user", "content": student_text},
        ],
    )
    return response.choices[0].message.content


def transcribe_audio(audio_bytes):
    TEMP_AUDIO_PATH.write_bytes(audio_bytes)
    with open(TEMP_AUDIO_PATH, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, language="he"
        )
    return transcript.text


def generate_level_summary(username, history):
    stats = history_stats(history)
    recent = history[:12]
    lines = []
    for i, item in enumerate(recent, 1):
        score = extract_score(item.get("feedback"))
        score_txt = f"ציון {score}/10" if score else "ללא ציון מפורש"
        lines.append(
            f"{i}. נושא: {item.get('topic', 'כללי')} | {score_txt}\n"
            f"   שאלה: {item.get('question', '')[:120]}\n"
            f"   תשובה: {(item.get('text') or '')[:200]}\n"
            f"   משוב: {(item.get('feedback') or '')[:300]}"
        )
    history_text = "\n\n".join(lines) if lines else "אין תרגולים"
    avg_line = (
        f"ממוצע ציונים (מתוך תרגולים עם ציון): {stats['avg']}/10"
        if stats["avg"]
        else "אין מספיק ציונים מספריים"
    )
    topics_line = ", ".join(f"{k} ({v})" for k, v in stats["topics"].items()) or "אין"

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "אתה מורה לעברית. על בסיס היסטוריית התרגול, כתוב סיכום קצר בעברית לתלמיד/ה: "
                    "רמת כישורים (מתחיל/בינוני/מתקדם), חוזקות, נקודות לשיפור, והמלצה לתרגול הבא. "
                    "השתמש בכותרות קצרות ורשימות. 150-250 מילים."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"תלמיד: {username}\n"
                    f"סה\"כ תרגולים: {stats['count']}\n"
                    f"{avg_line}\n"
                    f"נושאים שתורגלו: {topics_line}\n\n"
                    f"תרגולים אחרונים:\n{history_text}"
                ),
            },
        ],
    )
    return response.choices[0].message.content, stats
