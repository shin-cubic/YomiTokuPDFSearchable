import json
import sys
import cv2
import os
import shutil
from yomitoku import OCR
from yomitoku.data.functions import load_pdf
from reportlab.pdfgen import canvas
from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 日本語対応フォント（IPAexMincho）の登録（ipaexm.ttf が必要）
pdfmetrics.registerFont(TTFont('IPAexMincho', 'ipaexm.ttf'))

def results_to_dict(results):
    data = {"words": []}
    if not results or not hasattr(results, "words"):
        return data  # OCR結果が無効な場合は空のデータを返す
    
    for word in results.words:
        data["words"].append({
            "content": word.content,
            "points": word.points,
            "rec_score": word.rec_score,
            "det_score": word.det_score,
            "direction": word.direction,
        })
    return data

def json_to_hocr(json_data, page_num):
    hocr = [
        '<!DOCTYPE html>', '<html>', '<head>', '<meta charset="UTF-8">',
        f'<title>hOCR output - Page {page_num}</title>', '</head>', '<body>',
        f'<div class="ocr_page" id="page_{page_num}">'
    ]
    for i, word in enumerate(json_data.get('words', [])):
        content = word.get('content', '')
        points = word.get('points', [])
        if len(points) < 3:
            continue  # 座標情報が不足している場合はスキップ
        x_min = min(p[0] for p in points)
        y_min = min(p[1] for p in points)
        x_max = max(p[0] for p in points)
        y_max = max(p[1] for p in points)
        bbox = f"bbox {x_min} {y_min} {x_max} {y_max}"
        hocr.append(
            f'<span class="ocrx_word" id="word_{i+1}" title="{bbox}; x_wconf {int(word.get("rec_score", 0) * 100)}">{content}</span>'
        )
    hocr.append('</div>')
    hocr.append('</body>')
    hocr.append('</html>')
    return '\n'.join(hocr)

def draw_invisible_text(c, text, x, y, font_size):
    c.saveState()
    c.setFont("IPAexMincho", font_size)
    try:
        c.setFillAlpha(0)
    except AttributeError:
        c.setFillColorRGB(1, 1, 1, alpha=0)  # 透明化が可能なら適用
    c.drawString(x, y, text)
    c.restoreState()

def pdf_to_searchable(pdf_path, output_pdf):
    ocr = OCR(visualize=False, device="cuda")
    imgs = load_pdf(pdf_path)
    
    output_dir = os.path.abspath("output")
    os.makedirs(output_dir, exist_ok=True)
    
    temp_img_files = []
    json_files = []
    hocr_files = []
    
    for i, img in enumerate(imgs):
        try:
            results, _ = ocr(img)
            if not results:
                raise ValueError(f"OCR failed to process page {i}.")
            
            json_path = os.path.join(output_dir, f"output_{i}.json")
            json_data = results_to_dict(results)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            if os.path.getsize(json_path) == 0:
                raise ValueError(f"JSON file {json_path} is empty after writing.")
            json_files.append(json_path)
            
            img_path = os.path.join(output_dir, f"output_page_{i}.jpg")
            cv2.imwrite(img_path, img)
            temp_img_files.append(img_path)
            
            hocr_output = json_to_hocr(json_data, i + 1)
            hocr_path = os.path.join(output_dir, f"output_{i}.hocr")
            with open(hocr_path, "w", encoding="utf-8") as f:
                f.write(hocr_output)
            hocr_files.append(hocr_path)
        
        except Exception as e:
            print(f"Error processing page {i}: {e}")
            continue  # エラーがあったページはスキップ
    
    c = canvas.Canvas(output_pdf)
    for i, img_path in enumerate(temp_img_files):
        pil_img = Image.open(img_path)
        width, height = pil_img.size
        c.setPageSize((width, height))
        c.drawImage(img_path, 0, 0, width=width, height=height)
        
        json_path = json_files[i]
        with open(json_path, "r", encoding="utf-8") as f:
            json_loaded = json.load(f)
        
        for word in json_loaded.get('words', []):
            content = word.get('content', '')
            points = word.get('points', [])
            if len(points) < 3:
                continue
            x_min = min(p[0] for p in points)
            y_min = min(p[1] for p in points)
            x_max = max(p[0] for p in points)
            y_max = max(p[1] for p in points)
            pdf_x = x_min
            pdf_y = height - y_max
            font_size = max(y_max - y_min, 10)
            draw_invisible_text(c, content, pdf_x, pdf_y, font_size)
        c.showPage()
    c.save()
    
    try:
        for file in temp_img_files + json_files + hocr_files:
            if os.path.exists(file):
                os.remove(file)
        shutil.rmtree(output_dir, ignore_errors=True)
    except Exception as e:
        print(f"Failed to delete temporary files: {e}")
    
    print(f"Searchable PDF created: {output_pdf}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py input.pdf output.pdf")
        sys.exit(1)
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    try:
        pdf_to_searchable(input_pdf, output_pdf)
    except Exception as e:
        print(f"Error: {e}")

