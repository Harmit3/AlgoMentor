import gradio as gr
from tutor import new_session, tutor_turn, session_status
from ingest import ingest

session = {}

# Build / refresh the ChromaDB knowledge base when the app starts.
# This is useful for Hugging Face Spaces because chroma_db may not exist yet.
try:
    ingest()
except Exception as e:
    print(f"Warning: Could not ingest knowledge base automatically: {e}")


def start_session(problem):
    global session

    if not problem.strip():
        return "Please enter a problem first.", []

    session = new_session(problem.strip())
    return f"Session started. {session_status(session)}", []


def chat(student_message, history):
    global session

    if history is None:
        history = []

    if not session:
        history.append({
            "role": "assistant",
            "content": "Please set a problem first."
        })
        return history, "Please enter a problem to begin.", ""

    if not student_message.strip():
        return history, session_status(session), ""

    reply, _ = tutor_turn(session, student_message.strip())

    history.append({
        "role": "user",
        "content": student_message
    })

    history.append({
        "role": "assistant",
        "content": reply
    })

    return history, session_status(session), ""


with gr.Blocks(title="AlgoMentor") as demo:
    gr.Markdown("## AlgoMentor: Socratic Algorithm Tutor")
    gr.Markdown(
        "Paste an algorithm problem, then ask questions. "
        "The tutor guides you step by step instead of giving the full answer directly."
    )

    with gr.Row():
        problem_box = gr.Textbox(
            label="Problem",
            placeholder="Paste a LeetCode / Codeforces problem here...",
            lines=5,
            scale=4
        )
        start_btn = gr.Button("Start Session", scale=1)

    status = gr.Textbox(
        label="Status",
        interactive=False
    )

    chatbot = gr.Chatbot(
        label="Conversation",
        height=500
    )

    with gr.Row():
        msg_box = gr.Textbox(
            label="Your message",
            placeholder="Ask a question or describe your approach...",
            scale=4
        )
        send_btn = gr.Button("Send", scale=1)

    start_btn.click(
        start_session,
        inputs=problem_box,
        outputs=[status, chatbot]
    )

    send_btn.click(
        chat,
        inputs=[msg_box, chatbot],
        outputs=[chatbot, status, msg_box]
    )

    msg_box.submit(
        chat,
        inputs=[msg_box, chatbot],
        outputs=[chatbot, status, msg_box]
    )


if __name__ == "__main__":
    demo.launch()