"""简化版 IndexTTS2 WebUI：支持录音、文本克隆与结果回放。

尽量复用现有推理入口 `IndexTTS2.infer`，只在界面层做轻量封装，避免与
`webui.py` 重复实现大段逻辑。"""
import os
import time
from datetime import datetime
from pathlib import Path

import gradio as gr
import pandas as pd

from indextts.infer_v2 import IndexTTS2

MODEL_DIR = os.environ.get("INDEXTTS_MODEL_DIR", "checkpoints")
DEVICE = os.environ.get("INDEXTTS_DEVICE", "mps")
OUTPUT_DIR = Path(os.environ.get("INDEXTTS_OUTPUT_DIR", "outputs/webui_mic"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 复用核心推理逻辑，避免与 webui.py 内部实现重复
tts = IndexTTS2(
    cfg_path=os.path.join(MODEL_DIR, "config.yaml"),
    model_dir=MODEL_DIR,
    use_fp16=False,
    use_cuda_kernel=False,
    use_deepspeed=False,
    device=DEVICE,
)


def run_inference(ref_audio: str | None, text: str, history: list[dict] | None):
    history = history or []
    text = (text or "").strip()
    if not ref_audio:
        return "请先录音或上传参考音色。", None, history, pd.DataFrame(history)
    if not text:
        return "请输入需要克隆的文本内容。", None, history, pd.DataFrame(history)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".wav"
    output_path = OUTPUT_DIR / filename

    start = time.perf_counter()
    tts.infer(
        spk_audio_prompt=ref_audio,
        text=text,
        output_path=str(output_path),
        verbose=False,
    )
    elapsed = time.perf_counter() - start

    new_entry = {
        "时间": timestamp,
        "文本": text,
        "字数": len(text),
        "输出文件": str(output_path),
        "耗时(s)": f"{elapsed:.2f}",
    }
    history.insert(0, new_entry)
    history_df = pd.DataFrame(history)[["时间", "字数", "耗时(s)", "输出文件"]]

    return "克隆完成 ✅", str(output_path), history, history_df


def clear_history(_):
    return [], pd.DataFrame([], columns=["时间", "字数", "耗时(s)", "输出文件"])


with gr.Blocks(title="IndexTTS2 录音克隆体验页") as demo:
    gr.Markdown(
        """
        ## IndexTTS2 语音克隆体验
        1. 点击左侧录音按钮采样（或直接上传参考音频）。
        2. 输入需要合成的文本内容。
        3. 点击 **开始克隆**，稍等片刻即可在下方播放/下载生成语音。
        """
    )

    history_state = gr.State([])

    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="① 录制或上传参考音色",
            )
            text_input = gr.Textbox(
                label="② 输入需要克隆的文本",
                lines=5,
                placeholder="请在此输入台词/播报内容…",
            )
            with gr.Row():
                run_btn = gr.Button("开始克隆", variant="primary")
                clear_btn = gr.Button("清空历史")
        with gr.Column():
            status = gr.Textbox(label="状态提示", interactive=False)
            output_audio = gr.Audio(label="③ 生成语音预览", interactive=False)
            history_table = gr.Dataframe(
                headers=["时间", "字数", "耗时(s)", "输出文件"],
                label="历史记录",
                interactive=False,
            )

    run_btn.click(
        fn=run_inference,
        inputs=[audio_input, text_input, history_state],
        outputs=[status, output_audio, history_state, history_table],
    )
    clear_btn.click(
        fn=clear_history,
        inputs=[history_state],
        outputs=[history_state, history_table],
    )

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
