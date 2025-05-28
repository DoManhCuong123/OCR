import re
import unicodedata

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

def parse_cccd_text(text: str) -> dict:
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
