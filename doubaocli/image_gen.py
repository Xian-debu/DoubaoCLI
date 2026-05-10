"""AI image generation via Doubao's /chat/create-image page.

Uses Seedream 4.5 model with ContentEditable input (not textarea).
"""

import time

from playwright.sync_api import Page

from .config import (
    IMAGE_CREATE_URL,
    IMAGE_INPUT_SELECTORS,
    IMAGE_MODEL_SELECTOR,
    IMAGE_RATIO_SELECTOR,
    IMAGE_STYLE_SELECTOR,
    IMAGE_RESULT_SELECTORS,
    ImageResult,
)


def navigate(page: Page) -> bool:
    """Navigate to the AI creation page. Returns True on success."""
    try:
        page.goto(IMAGE_CREATE_URL, timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        return "create-image" in page.url
    except Exception:
        return False


def switch_tab(page: Page, tab: str) -> bool:
    """Switch between 'image' (图像) and 'video' (视频) tabs. Returns True on success."""
    try:
        tab_text = "图像" if tab == "image" else "视频"
        btn = page.locator(f"text={tab_text}").first
        if btn.count() > 0:
            btn.click()
            time.sleep(1)
            return True
    except Exception:
        pass
    return False


def generate(page: Page, prompt: str, model: str = "",
             ratio: str = "", style: str = "", timeout: int = 120) -> ImageResult:
    """Generate an AI image.

    Args:
        prompt: Image description.
        model: Model name (default is Seedream 4.5).
        ratio: Aspect ratio.
        style: Image style.

    Returns ImageResult with URLs of generated images.
    """
    t0 = time.time()

    # Ensure we're on the right page
    if "create-image" not in page.url:
        if not navigate(page):
            return ImageResult(error="Cannot navigate to create-image page", elapsed=time.time() - t0)

    # Switch to image tab if needed
    switch_tab(page, "image")

    # Find the ContentEditable input
    editor = None
    for sel in IMAGE_INPUT_SELECTORS:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible():
                editor = el
                break
        except Exception:
            pass

    if not editor:
        return ImageResult(error="Cannot find image prompt input", elapsed=time.time() - t0)

    # Type the prompt
    try:
        editor.click()
        time.sleep(0.3)
        editor.fill(prompt)
        time.sleep(0.5)
    except Exception as e:
        return ImageResult(error=f"Cannot type prompt: {e}", elapsed=time.time() - t0)

    # Press Enter to generate
    editor.press("Enter")

    # Wait for images to appear
    start = time.time()
    urls = []
    while time.time() - start < timeout:
        time.sleep(3)
        urls = _extract_image_urls(page)
        if urls:
            break

    return ImageResult(
        urls=urls,
        prompt=prompt,
        model=model or "Seedream 4.5",
        elapsed=time.time() - t0,
        error=None if urls else "No images generated within timeout",
    )


def get_generated_images(page: Page) -> list[str]:
    """Get URLs of currently displayed generated images."""
    return _extract_image_urls(page)


def _extract_image_urls(page: Page) -> list[str]:
    """Extract image URLs from the AI creation page."""
    urls = set()
    for sel in IMAGE_RESULT_SELECTORS:
        try:
            elements = page.locator(sel)
            for i in range(elements.count()):
                src = elements.nth(i).get_attribute("src")
                if src and src.startswith("http"):
                    urls.add(src)
        except Exception:
            pass

    # Also try JS extraction
    if not urls:
        js = """
        () => {
            const urls = [];
            const imgs = document.querySelectorAll('img[src*="doubao"], img[src*="volc"], '
                + 'img[src*="byteimg"], img[src*="tos"], img[class*="generated"], '
                + 'img[class*="result"], [class*="semi-image"] img');
            for (const img of imgs) {
                if (img.src && img.src.startsWith('http') && img.naturalWidth > 50) {
                    urls.push(img.src);
                }
            }
            return urls;
        }
        """
        try:
            urls = set(page.evaluate(js))
        except Exception:
            pass

    return list(urls)
