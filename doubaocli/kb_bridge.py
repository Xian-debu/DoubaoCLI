"""Bridge between Doubao multimodal analysis and local RAG knowledge base.

Core workflow:
  PDF/Image → upload to Doubao → multi-turn analysis → structured Markdown
  → kb ingest → semantic search available

This supplements local parsing (PyPDF2, etc.) which has many deficiencies
with Chinese text, complex layouts, and images within documents.
"""

import json
import time
import subprocess
from pathlib import Path

from playwright.sync_api import Page

from .file_upload import upload_file, clear_files
from .chat import ChatSession

import os
KB_CLI = os.environ.get("KB_CLI_PATH", "")  # Set to your RAG kb CLI path to enable pdf_to_kb


def analyze_document(page: Page, chat: ChatSession,
                     file_path: str | Path,
                     questions: list[str] | None = None,
                     timeout: int = 300) -> dict:
    """Upload a document and perform multi-turn analysis.

    Args:
        page: Doubao chat page.
        chat: ChatSession instance.
        file_path: Path to PDF/document.
        questions: Custom questions to ask about the document.
                   Default: summary, key points, methodology, conclusions.

    Returns:
        {
            "filename": str,
            "summary": str,
            "key_points": list[str],
            "sections": list[dict],  # {question, answer}
            "raw_text": str,          # Full concatenated response
        }
    """
    path = Path(file_path).expanduser().resolve()
    result = {
        "filename": path.name,
        "summary": "",
        "key_points": [],
        "sections": [],
        "raw_text": "",
    }

    if not path.exists():
        result["sections"].append({"question": "ERROR", "answer": f"File not found: {path}"})
        return result

    # Upload file
    ok = upload_file(page, path, wait_process=True, timeout=15)
    if not ok:
        result["sections"].append({"question": "ERROR", "answer": "Upload failed"})
        return result

    time.sleep(5)  # Let Doubao fully process the file content

    # Default questions if none provided
    if not questions:
        ext = path.suffix.lower()
        if ext == ".pdf":
            questions = [
                f"请详细总结这篇文档({path.name})的主要内容、研究目标和核心发现。",
                f"请列出这篇文档的关键论点和方法论，每条用一两句话概括。",
                f"这篇文档有什么重要的数据、表格或实验结果？请提炼关键数字和结论。",
                f"请用中文总结这篇文档的结构（分几个部分，每部分讲什么），并标注任何可能的局限或不足。",
            ]
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            questions = [
                f"请详细描述这张图片({path.name})的内容，包括所有可见的文字、物体、布局和颜色。",
                f"这张图片中有什么关键信息或数据？请逐项列出。",
            ]
        else:
            questions = [
                f"请总结这个文件({path.name})的主要内容和关键信息。",
                f"请列出其中的重要细节和值得注意的点。",
            ]

    # Multi-turn Q&A
    all_text = []
    for i, q in enumerate(questions):
        result_send = chat.send(q, timeout=timeout // max(len(questions), 1))
        answer = result_send.text or f"(no response: {result_send.error})"
        all_text.append(f"## Q{i+1}: {q}\n\n{answer}")
        result["sections"].append({"question": q, "answer": answer})
        time.sleep(2)

    result["raw_text"] = "\n\n".join(all_text)
    result["summary"] = result["sections"][0]["answer"] if result["sections"] else ""

    # Extract key points from section 2 if available
    if len(result["sections"]) > 1:
        kp_text = result["sections"][1]["answer"]
        result["key_points"] = [
            line.strip("- •1234567890. ") for line in kp_text.split("\n")
            if line.strip() and len(line.strip()) > 10
        ][:15]

    # Clean up — clear attached file for next use
    clear_files(page)
    time.sleep(1)

    return result


def analyze_image(page: Page, chat: ChatSession,
                  file_path: str | Path,
                  question: str | None = None,
                  timeout: int = 120) -> str:
    """Upload an image and get Doubao's description/analysis.

    Args:
        page: Doubao chat page.
        chat: ChatSession instance.
        file_path: Path to image file (png, jpg, webp).
        question: Custom question. Default: detailed description.

    Returns:
        Doubao's text response describing the image.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return f"ERROR: File not found: {path}"

    ok = upload_file(page, path, wait_process=True, timeout=15)
    if not ok:
        return "ERROR: Upload failed"

    time.sleep(5)

    prompt = question or (
        f"请详细描述这张图片的全部内容。包括：\n"
        f"1. 整体内容和主题\n"
        f"2. 所有可见的文字（逐字抄录）\n"
        f"3. 图表/数据/图形的具体数值和含义\n"
        f"4. 颜色、布局、风格等视觉特征"
    )
    result = chat.send(prompt, timeout=timeout)

    clear_files(page)
    time.sleep(1)

    return result.text or f"(no response: {result.error})"


def pdf_to_kb(page: Page, chat: ChatSession,
              file_path: str | Path,
              category: str = "document-analysis",
              timeout: int = 300) -> int:
    """Full pipeline: PDF → Doubao multi-turn analysis → KB ingest.

    1. Upload PDF to Doubao
    2. Ask structured questions (summary, methods, data, structure)
    3. Compile responses into a clean Markdown document
    4. Ingest Markdown into local RAG knowledge base
    5. Return number of ingested chunks

    Args:
        page: Doubao chat page.
        chat: ChatSession instance.
        file_path: Path to PDF file.
        category: KB category tag for the ingested document.
        timeout: Max total time for analysis.

    Returns:
        Number of chunks ingested into KB (0 on failure).
    """
    path = Path(file_path).expanduser().resolve()

    # Step 1-3: Doubao analysis
    analysis = analyze_document(page, chat, path, timeout=timeout)

    if not analysis["raw_text"]:
        return 0

    # Step 4: Compile into Markdown
    md_lines = [
        f"# {path.stem} — Doubao Analysis",
        f"",
        f"**Source**: {path.name}",
        f"**Analyzed by**: Doubao AI (via doubao framework)",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}",
        f"**Category**: {category}",
        f"",
        f"---",
        f"",
    ]

    for section in analysis["sections"]:
        md_lines.append(f"## {section['question'][:80]}")
        md_lines.append("")
        md_lines.append(section["answer"])
        md_lines.append("")

    md_content = "\n".join(md_lines)

    # Save temp Markdown file
    tmp_md = Path(f"/tmp/doubao_kb_{path.stem}_{int(time.time())}.md")
    tmp_md.write_text(md_content)

    # Step 5: Ingest into KB (if KB_CLI is configured)
    if not KB_CLI:
        tmp_md.unlink(missing_ok=True)
        return 0  # KB CLI not configured — skip ingestion

    try:
        cmd = f"{KB_CLI} ingest {tmp_md} --mode chunk --source doubao --category {category}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        # Parse chunk count from output
        for line in result.stdout.split("\n"):
            if "Chunks:" in line:
                try:
                    chunks = int(line.split(":")[1].strip())
                    tmp_md.unlink(missing_ok=True)
                    return chunks
                except ValueError:
                    pass

        tmp_md.unlink(missing_ok=True)
        return 1 if "Chunks:" in result.stdout else 0
    except Exception:
        tmp_md.unlink(missing_ok=True)
        return 0
