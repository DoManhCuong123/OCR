from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtGui import QPixmap
from Lastest import Ui_MainWindow
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import pandas as pd
import re
import cv2
import unicodedata



# ocr = PaddleOCR(use_angle_cls=True,
#                 lang='vi',
#                 det_model_dir="inference/SAST",
#                 rec_model_dir="inference/SRN_Lastest",
#                 det_algorithm="SAST",
#                 rec_char_dict_path="Train/vietnamese/vn_dictionary.txt")

ocr = PaddleOCR(use_angle_cls=True,
                lang='vi',
                use_gpu='false',
                det_model_dir="inference/SAST",
                rec_model_dir="inference/SRN_Final",
                rec_image_shape="1, 64, 256",
                det_algorithm="SAST",
                rec_char_dict_path="Test/vi_vietnam.txt" )



STOP_KEYWORDS = [
    "Ngày sinh", "Date of birth", "Giới tính", "Sex",
    "Quốc tịch", "Nationality", "Quê quán", "Place of origin",
    "Nơi thường trú", "Place of residence", "Có giá trị", "Date", "Ngày hết hạn"
]
STOP_PATTERN = r'(?=\b(?:' + '|'.join(map(re.escape, STOP_KEYWORDS)) + r')\b)'

def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fix_common_ocr_errors(text: str) -> str:
    corrections = [
        (r'place of orign', 'Place of origin'),
        (r'freadom', 'freedom'),
        (r'ho\s*v[aà]\s*t[eê]n\s*full\s*name', 'Họ và tên Full name'),
        (r'HO\s*v[AÀ]\s*t[eê]n\s*full\s*name', 'Họ và tên Full name'),
        (r'no[ií]\s*thu[ơo]ng\s*tru\s*place\s*of\s*residence', 'Place of residence'),
        (r'date of( binth| bint| expiry| birth[!,:]?)', 'Date of birth'),
        (r'sex[.\s]?(nam|nu)', r'Sex: \1'),
        (r'qu[ôo]c\s*t[ịi]ch\s*natiohality', 'Nationality'),
        (r'place of ferginn', 'Place of origin'),
        (r'place of origin:?', 'Place of origin'),
        (r'place of forgins?', 'Place of origin'),
        (r'place of tri residence', 'Place of residence'),
        (r'date afexpiry', 'Date of expiry'),
    ]
    for pattern, repl in corrections:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text

def postprocess_info(info: dict) -> dict:
    if 'Quốc tịch' in info and info['Quốc tịch']:
        info['Quốc tịch'] = re.split(r'\bQuê quán\b', info['Quốc tịch'], flags=re.IGNORECASE)[0].strip()

    for key in ['Quê quán', 'Nơi thường trú']:
        if key in info and info[key]:
            # Xóa nhãn tiếng Anh và cắt nếu dính nhãn sau
            info[key] = re.sub(r'\b(?:Place of origin|Place of residence)\b', '', info[key], flags=re.IGNORECASE)
            info[key] = re.split(r'\b(Có giá trị|Ngày hết hạn|Date|CỎ|GIÁ|DATE)\b', info[key])[0].strip()

    if 'Họ và tên' in info and info['Họ và tên']:
        info['Họ và tên'] = re.sub(r'\b(Họ và tên|Full name)\b[\s:/.-]*', '', info['Họ và tên'], flags=re.IGNORECASE).strip()
        info['Họ và tên'] = re.split(STOP_PATTERN, info['Họ và tên'])[0].strip()

    return info

def extract_info(text: str) -> dict:
    result = {}
    text = normalize_text(text)
    text = fix_common_ocr_errors(text)

    # CCCD
    m = re.search(r'\b\d{12}\b', text)
    result['CCCD'] = m.group() if m else None

    # Họ và tên
    m = re.search(r'(?:Họ và tên|Ho va ten|Full name)[\s:/.-]*([A-ZÀ-ỴĐ][A-ZÀ-ỴĐ\s]{2,}?)(?=' + STOP_PATTERN + ')', text, re.IGNORECASE)
    result['Họ và tên'] = m.group(1).strip() if m else None

    # Ngày sinh
    m = re.search(r'(?:Ngày sinh|Date of birth)[\s:/.-]*([0-3]?\d[/-][01]?\d[/-]\d{4})', text, re.IGNORECASE)
    result['Ngày sinh'] = m.group(1) if m else None

    # Giới tính
    m = re.search(r'(?:Giới tính|Sex)[\s:/.-]*([Nn]am|[Nn]ữ|[Nn]u)', text, re.IGNORECASE)
    result['Giới tính'] = m.group(1).capitalize() if m else None

    # Quốc tịch
    m = re.search(r'(?:Quốc tịch|Nationality)[\s:/.-]*([A-Za-zÀ-Ỹà-ỹ\s]{3,})(?=' + STOP_PATTERN + ')', text, re.IGNORECASE)
    result['Quốc tịch'] = m.group(1).strip().title() if m else None

    # Quê quán
    m = re.search(r'(?:Quê quán|Place of origin)[\s:/.-]*([A-Za-zÀ-Ỹà-ỹ,\s]+?)(?=' + STOP_PATTERN + ')', text, re.IGNORECASE)
    result['Quê quán'] = m.group(1).strip() if m else None

    # Nơi thường trú
    m = re.search(r'(?:Nơi thường trú|Place of residence)[\s:/.-]*([A-Za-zÀ-Ỹà-ỹ,\s]+?)(?=' + STOP_PATTERN + ')', text, re.IGNORECASE)
    result['Nơi thường trú'] = m.group(1).strip() if m else None

    # Ngày hết hạn
    dates = re.findall(r'\d{2}/\d{2}/\d{4}', text)
    if len(dates) >= 2:
        result['Ngày hết hạn'] = dates[-1]
    elif len(dates) == 1:
        result['Ngày hết hạn'] = dates[0]
    else:
        result['Ngày hết hạn'] = None

    return postprocess_info(result)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.btChonAnh.clicked.connect(self.select_image)
        self.ui.btTrichXuat.clicked.connect(self.trich_xuat_thong_tin)
        self.last_text = ""
        self.ui.btQuetAnhCam.clicked.connect(self.quet_anh_camera)
        self.ui.btExport.clicked.connect(self.xuat_excel)
        self.extracted_data = []  # Danh sách lưu trữ các thông tin đã trích xuất

    def  select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self,"Chọn ảnh OCR","","Image Files (*.jpg *.jpeg *.png *.bmp)")
        if file_path:
            result = ocr.ocr(file_path, cls=True)
            image = Image.open(file_path).convert('RGB')
            boxes = [line[0] for res in result for line in res]
            txts = [line[1][0] for res in result for line in res]
            if not txts:
                self.ui.txtChu.setPlainText("❌ Không phát hiện ra chữ. Vui lòng chọn lại ảnh.")
                self.ui.txtChu_2.setPlainText("")
                return
            scores = [line[1][1] for res in result for line in res]
            im_draw = draw_ocr(image, boxes, font_path='PaddleOCR/doc/fonts/latin.ttf')
            im_draw = Image.fromarray(im_draw)
            im_draw.save("ocr_result.jpg")  # tạm thời lưu
            pixmap = QPixmap("ocr_result.jpg")
            self.ui.lbAnh.setPixmap(pixmap.scaled(self.ui.lbAnh.size()))

            full_text = " ".join(txts)
            with open("test.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
            self.last_text = full_text
            self.ui.txtChu.setPlainText(full_text)

    def xuat_excel(self):
        if not self.extracted_data:
            self.ui.txtChu_2.setPlainText("⚠️ Không có dữ liệu để xuất.")
            return

        df = pd.DataFrame(self.extracted_data)

        save_path, _ = QFileDialog.getSaveFileName(self, "Lưu file CSV", "thong_tin_ocr.csv", "CSV Files (*.csv)")
        if save_path:
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            self.ui.txtChu_2.append("\n✅ Đã xuất toàn bộ thông tin ra file CSV.")

    def xu_ly_anh_ocr(self,file_path):
        result = ocr.ocr(file_path, cls=True)
        image = Image.open(file_path).convert('RGB')
        boxes = [line[0] for res in result for line in res]
        txts = [line[1][0] for res in result for line in res]
        scores = [line[1][1] for res in result for line in res]
        txts = [line[1][0] for res in result for line in res]
        if not txts:
            self.ui.txtChu.setPlainText("❌ Không phát hiện ra chữ. Vui lòng chụp lại ảnh.")
            self.ui.txtChu_2.setPlainText("")
            return
        im_draw = draw_ocr(image, boxes, font_path='PaddleOCR/doc/fonts/latin.ttf')

        im_draw = Image.fromarray(im_draw)

        im_draw.save("ocr_result.jpg")  # tạm thời lưu
        pixmap = QPixmap("ocr_result.jpg")
        self.ui.lbAnh.setPixmap(pixmap.scaled(self.ui.lbAnh.size()))

        full_text = " ".join(txts)
        with open("test.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
        self.last_text = full_text
        self.ui.txtChu.setPlainText(full_text)

    def trich_xuat_thong_tin(self):
        text = self.ui.txtChu.toPlainText()
        info = extract_info(text)

        self.ui.txtChu_2.clear()
        if not info:
            self.ui.txtChu_2.setPlainText("Không tìm thấy thông tin.")
        else:
            result_text = "Thông tin trích xuất:\n"
            for key, value in info.items():
                result_text += f"{key}: {value}\n"
            self.ui.txtChu_2.setPlainText(result_text)

        self.extracted_data.append(info)


    def quet_anh_camera(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.ui.txtChu.setPlainText("Không mở được camera.")
            return

        self.ui.txtChu.setPlainText("Nhấn SPACE để chụp, ESC để thoát.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow("Camera - Space to take picture", frame)

            key = cv2.waitKey(1)
            if key == 27:  # ESC
                break
            elif key == 32:  # SPACE
                img_path = "captured_image.jpg"
                cv2.imwrite(img_path, frame)
                self.xu_ly_anh_ocr(img_path)
                break

        cap.release()
        cv2.destroyAllWindows()





if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()