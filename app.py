import gradio as gr
from dotenv import load_dotenv
from research_manager import ResearchManager
from styles import CSS, JS, EXAMPLES, HEADER_HTML

load_dotenv(override=True)


async def run(query: str):
    file_update = gr.update(value=None, visible=False)
    async for status_update in ResearchManager().run(query):
        if isinstance(status_update, tuple):
            markdown_report, path = status_update
            file_update = gr.update(value=path, visible=True)
            yield markdown_report, file_update
        else:
            yield status_update, file_update


with gr.Blocks(title="Deep Research") as ui:
    gr.HTML(HEADER_HTML)

    with gr.Row(elem_classes="dr-query-row"):
        query_textbox = gr.Textbox(
            placeholder="Type a research question...",
            show_label=False,
            container=False,
            autofocus=True,
            elem_id="dr-query",
            scale=5,
        )
        run_button = gr.Button("Investigate", variant="primary", elem_id="dr-run", scale=1)

    gr.HTML('<div class="dr-examples-label">Try one</div>')
    gr.Examples(examples=EXAMPLES, inputs=query_textbox, elem_id="dr-examples")

    report = gr.Markdown(elem_id="dr-report")
    report_file = gr.File(
        label="Saved report",
        visible=False,
        interactive=False,
        elem_id="dr-file",
    )

    run_button.click(run, inputs=query_textbox, outputs=[report, report_file])
    query_textbox.submit(run, inputs=query_textbox, outputs=[report, report_file])


if __name__ == "__main__":
    ui.launch(css=CSS, js=JS, theme=gr.themes.Base())
