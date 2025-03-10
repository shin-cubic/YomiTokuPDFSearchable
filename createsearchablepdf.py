import json
import sys
import cv2
import os
from yomitoku import OCR
from yomitoku.data.functions import load_pdf
from reportlab.pdfgen import canvas
from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 日本語対応フォント（IPAexMincho）の登録（ipaexm.ttfが必要）
pdfmetrics.registerFont(TTFont('IPAexMincho', 'ipaexm.ttf'))

def json_to_hocr(json_data, page_num):
    hocr = [
        '<!DOCTYPE html>', '<html>', '<head>', '<meta charset="UTF-8">',
        f'<title>hOCR output - Page {page_num}</title>', '</head>', '<body>',
        f'<div class="ocr_page" id="page_{page_num}">'
    ]
    for i, word in enumerate(json_data['words']):
        content = word['content']
        points = word['points']
        bbox = f"bbox {points[0][0]} {points[0][1]} {points[2][0]} {points[2][1]}"
        hocr.append(
            f'<span class="ocrx_word" id="word_{i+1}" title="{bbox}; x_wconf {int(word["rec_score"] * 100)}">{content}</span>'
        )
    hocr.append('</div>')
    hocr.append('</body>')
    hocr.append('</html>')
    return '\n'.join(hocr)

def draw_invisible_text(c, text, x, y, font_size):
    """
    PDF上に検索可能なテキストを描画します。
    ここでは、テキストを完全に透明（または背景色と同じ色）に設定することで、見た目には表示されないがPDF内に文字情報として残ります。
    """
    c.saveState()
    c.setFont("IPAexMincho", font_size)
    try:
        # 透明度を0に設定（ReportLabのバージョンによっては未対応の場合があります）
        c.setFillAlpha(0)
    except AttributeError:
        # 透明度がサポートされない場合、背景が白前提で白色に設定
        c.setFillColorRGB(1, 1, 1)
    c.drawString(x, y, text)
    c.restoreState()

def pdf_to_searchable(pdf_path, output_pdf):
    ocr = OCR(visualize=False, device="cpu")
    imgs = load_pdf(pdf_path)
    
    # OCR結果や画像を一時ファイルとして保存
    temp_img_files = []
    json_files = []
    hocr_files = []
    for i, img in enumerate(imgs):
        results, _ = ocr(img)
        json_path = f"output_{i}.json"
        results.to_json(json_path)
        json_files.append(json_path)
        
        # 画像を一時保存
        img_path = f"output_page_{i}.jpg"
        cv2.imwrite(img_path, img)
        temp_img_files.append(img_path)
        
        # 任意でhOCRも出力（ログ用）
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        hocr_output = json_to_hocr(json_data, i + 1)
        hocr_path = f"output_{i}.hocr"
        with open(hocr_path, "w", encoding="utf-8") as f:
            f.write(hocr_output)
        hocr_files.append(hocr_path)
    
    # ReportLabで新たなPDFを生成
    c = canvas.Canvas(output_pdf)
    
    for i, img_path in enumerate(temp_img_files):
        pil_img = Image.open(img_path)
        width, height = pil_img.size
        c.setPageSize((width, height))
        
        # ページ背景に画像を描画
        c.drawImage(img_path, 0, 0, width=width, height=height)
        
        # 対応するOCR結果のJSONを読み込み、非表示テキストレイヤーを追加
        json_path = json_files[i]
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        
        for word in json_data['words']:
            content = word['content']
            points = word['points']
            # OCRの座標は画像の左上原点。ReportLabは左下原点なので変換が必要です。
            x1, y1 = points[0]
            x2, y2 = points[2]
            pdf_x = x1
            pdf_y = height - y2  # 下部へ変換
            font_size = y2 - y1 if (y2 - y1) > 0 else 10
            draw_invisible_text(c, content, pdf_x, pdf_y, font_size)
        
        c.showPage()
    
    c.save()
    
    # 一時ファイルの削除
    for file in temp_img_files + json_files + hocr_files:
        os.remove(file)
    
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
    except Exception as e:
        print(f"Error: {e}")
