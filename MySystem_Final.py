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



def normalize_text(text):
    # Chuẩn hóa tiếng Việt và xoá khoảng trắng thừa
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fix_common_ocr_errors(text):
    corrections = {
        'Place of orign': 'Place of origin',
        'Freadom': 'Freedom',
        'Ho va tenFull name': 'Ho va ten Full name',
        'Họ và tên Fuil name':'Ho va ten Full name',
        'Hovà tên Fullname':'Ho va ten Full name',
        'Noi thuong truPlace of residence': 'Noi thuong tru Place of residence',
        'Date ofexpiry': 'Date of expiry',
        'Quốc tịch Natiohality':'Nationality',
        'Place of origin:':'Place of origin',
        'Ngay sinhDate of birth': 'Ngay sinh Date of birth',
        'Date of birth,':'Ngay sinh Date of birth',
        'Sex.Nam': 'Sex: Nam',
        'Sex.Nu': 'Sex: Nu',
        'Nationality.':'Nationality',
        'Họ và tên Full Tname':'Ho va ten Full name',
        'Quê quán Place f onigin':'Place of origin',
        'Place of ferginn':'Place of origin',
        'Date of binth':'Date of birth',
        'Date of bint:':'Date of birth',
        'Date of birth!':'Date of birth'
    }
    for wrong, right in corrections.items():
        text = text.replace(wrong, right)
    return text


def clean_field(value):
    return re.split(r'\b(Ngay sinh|Date of birth|Gioi tinh|Sex|Quoc tich|Nationality|Que quan|Place of origin|Noi thuong tru|Place of residence|Co gia tri|Date)\b', value, flags=re.IGNORECASE)[0].strip()

stop_pattern = r'(?=\b(?:Ngày sinh|Date of birth|Giới tính|Sex|Quốc tịch|Nationality|Quê quán|Place of origin|Nơi thường trú|Place of residence|Có giá trị|Date)\b)'

def extract_info(text):
    text = normalize_text(text)
    text = fix_common_ocr_errors(text)

    info = {}

    # CCCD
    if m := re.search(r'\b\d{12}\b', text):
        info['CCCD'] = m.group()

    # Tên
    if m := re.search(r'(?:Họ và tên|Full name)[\s:/.-]*([A-ZÀ-ỴĐ][A-ZÀ-ỴĐ\s]+?)' + stop_pattern, text, re.IGNORECASE):
        info['Name'] = m.group(1).strip()

    # Ngày sinh
    if m := re.search(r'(?:Ngày sinh|Date of birth)[\s:/.-]*([0-3]?\d[/-][01]?\d[/-]\d{4})', text, re.IGNORECASE):
        info['Date'] = m.group(1)

    # Giới tính
    if m := re.search(r'(?:Giới tính|Gioi tinh|Sex)[\s:/.-]*([Nn]am|[Nn]u|[Nn]ữ)', text, re.IGNORECASE):
        info['Sex'] = m.group(1).capitalize()

    # Quốc tịch
    if m := re.search(r'(?:Quốc tịch|Quoc tich|Nationality)[\s:/.-]*[.:]?\s*([A-ZÀ-Ỵa-zà-ỹ\s]+?)' + stop_pattern, text, re.IGNORECASE):
        nation = m.group(1).strip()
        if nation.lower() not in ['nationality', 'quốc tịch', 'quoc tich']:
            info['Nation'] = nation

    # Quê quán
    if m := re.search(r'(?:Quê quán|Place of origin)[\s:/.-]*([A-Za-zÀ-Ỹà-ỹ,\s]+?)' + stop_pattern, text, re.IGNORECASE):
        result = m.group(1).strip()
        result = re.sub(r'^(Place of origin\s*)', '', result, flags=re.IGNORECASE).strip()
        info['Place of Origin'] = result


    return info


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