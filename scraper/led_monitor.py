from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from PIL import Image, ImageDraw

import csv
from decimal import Decimal, InvalidOperation
import json
import os
import pytesseract
import re
import tempfile
import time
from pathlib import Path

URL = os.getenv("LED_URL", "https://asset.led.go.th/newbidreg/default.asp")
CHROME_PATH = os.getenv(
    "CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "/opt/homebrew/bin/tesseract")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "result.csv")
# Current result pages use table.table-hover; keep this centralized for site updates.
TABLE_SELECTOR = "table.table-hover"
LANDSMAPS_URL = os.getenv("LANDSMAPS_URL", "https://landsmaps.dol.go.th/")
LANDSMAPS_CONFIG_URL = "/Service/ProvinceService/configapi.json"
SUMMARY_FIELDS = [
    "ล็อต", "ลำดับ", "หมายเลขคดี", "ประเภท", "ไร่", "งาน", "ตรว",
    "ราคา", "ตำบล", "อำเภอ", "จังหวัด",
]
EXCLUDED_CSV_COLUMNS = {
    "ที่อยู่จดหมายอิเล็กทรอนิกส์",
    "ติดต่อผู้ดูแลเว็บไซต์",
}
PRICE_PRIORITY_LABELS = [
    "ราคาที่กำหนดโดยคณะกรรมการกำหนดราคาทรัพย์",
    "ราคาประเมินของเจ้าพนักงานประเมินราคาทรัพย์กรมบังคับคดี",
    "ราคาประเมินของเจ้าพนักงานบังคับคดี",
    "ราคาประเมินของผู้เชี่ยวชาญการประเมินราคา",
]
NO_BID_STATUS = "งดขายไม่มีผู้สู้ราคา"


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def fill_first_existing(page, selectors: list[str], value: str) -> str:
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.fill(value)
            return selector
    raise RuntimeError(f"Cannot find any input from selectors: {selectors}")


def fill_province(page, province_name: str) -> None:
    # The site currently uses a native select; retain the old autocomplete fallback.
    province_select = page.locator("select#provinces")
    if province_select.count() > 0:
        province_select.select_option(label=province_name)
        return

    province_input = page.locator("input#data.search-box")
    province_input.click()
    province_input.fill("")
    province_input.type(province_name, delay=80)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")


def select_dynamic_option(page, selector: str, target: str, timeout_ms: int = 15000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    target = normalize_text(target)
    while time.monotonic() < deadline:
        options = page.locator(f"{selector} option")
        for i in range(options.count()):
            option = options.nth(i)
            label = normalize_text(option.inner_text())
            value = option.get_attribute("value")
            if value and value != "00" and (label == target or target in label):
                # Some LandsMaps options share a value, so select by index.
                page.evaluate(
                    """({selector, index}) => {
                        const element = document.querySelector(selector);
                        element.selectedIndex = index;
                        element.dispatchEvent(new Event('change', {bubbles: true}));
                    }""",
                    {"selector": selector, "index": i},
                )
                return
        page.wait_for_timeout(200)
    raise RuntimeError(f"Cannot find option {target!r} in {selector}")


def fill_search_area(page, amphur: str, tambon: str) -> None:
    if amphur and page.locator("select#amphurSelect").count() > 0:
        select_dynamic_option(page, "select#amphurSelect", amphur)
    if tambon and page.locator("select#tambonSelect").count() > 0:
        select_dynamic_option(page, "select#tambonSelect", tambon)


def fill_asset_type(page, asset_type: str) -> None:
    if not normalize_text(asset_type):
        print("ℹ️ asset_type is empty; skip asset-type filter")
        return
    selector = 'select[name="asset_type"]'
    if page.locator(selector).count() == 0:
        raise RuntimeError("Cannot find asset-type selector")
    page.select_option(selector, label=asset_type)


def fill_price_range(page, minimum_price: str, maximum_price: str) -> None:
    values = {
        'input[name="price_begin"]': minimum_price,
        'input[name="price_end"]': maximum_price,
    }
    for selector, value in values.items():
        if value and page.locator(selector).count() > 0:
            page.fill(selector, value.replace(",", ""))


def load_config(filename: str = "config.json") -> dict:
    with open(filename, encoding="utf-8") as file:
        config = json.load(file)
    search = config.get("search") or {}
    required = ["province"]
    missing = [key for key in required if not str(search.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Missing config fields: {', '.join(missing)}")
    if str(search.get("rai_value", "")).strip() and not str(
        search.get("rai_condition", "")
    ).strip():
        raise ValueError("rai_condition is required when rai_value is provided")
    return config


def fill_land_area(page, rai_condition: str, rai_value: str) -> None:
    if not normalize_text(rai_value):
        print("ℹ️ rai_value is empty; skip land-area filters")
        return

    page.select_option('select[name="rai_if"]', label=rai_condition)

    used_selector = fill_first_existing(
        page,
        selectors=[
            'input[name="rai"]',
            'input[name="Rai"]',
            'input[name="area_rai"]',
            'input[placeholder*="ไร่"]',
        ],
        value=rai_value,
    )
    print(f"✅ filled rai using: {used_selector}")

    if page.locator('input[name="quaterrai"]').count() > 0:
        page.fill('input[name="quaterrai"]', "0")

    for selector in [
        'input[name="wa"]',
        'input[name="squarewa"]',
        'input[placeholder*="ตร."]',
    ]:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.fill("0")
            break


def scrape_results(page) -> list[dict]:
    page.wait_for_selector(f"{TABLE_SELECTOR} tbody tr", timeout=60000)

    rows = page.locator(f"{TABLE_SELECTOR} tbody tr")
    results = []

    print(f"จำนวนรายการ: {rows.count()}")

    for i in range(rows.count()):
        item = scrape_summary_from_row(rows.nth(i))
        if not item:
            print(f"⚠️ row {i} has too few columns, skipped")
            continue

        results.append(item)
        print(item)

    return results


def scrape_all_pages_with_detail(page) -> list[dict]:
    all_results = []
    visited_pages = set()

    while True:
        page.wait_for_selector(f"{TABLE_SELECTOR} tbody tr", timeout=60000)

        page_text = normalize_text(page.locator("body").inner_text())
        if "ผลการค้นหา พบ 0 รายการ" in page_text or "ไม่พบข้อมูล" in page_text:
            print("⚠️ เว็บไม่พบรายการตาม criteria")
            return []
        page_match = re.search(r"หน้าที่\s*(\d+)\s*/\s*(\d+)", page_text)

        if page_match:
            current_page = int(page_match.group(1))
            total_pages = int(page_match.group(2))
        else:
            current_page = 1
            total_pages = 1

        print(f"\n📄 scraping page {current_page}/{total_pages}")

        if current_page in visited_pages:
            print("⚠️ page loop detected, stop")
            break

        visited_pages.add(current_page)

        rows_count = page.locator(f"{TABLE_SELECTOR} tbody tr").count()
        print(f"จำนวนรายการในหน้านี้: {rows_count}")

        for i in range(rows_count):
            print(f"  → row {i + 1}/{rows_count}")

            # re-locate ใหม่ทุกครั้ง
            row = page.locator(f"{TABLE_SELECTOR} tbody tr").nth(i)
            summary = scrape_summary_from_row(row)

            if not summary:
                print(f"⚠️ skip row {i}, column count not enough")
                continue

            try:
                detail = open_row_and_scrape_detail(page, i)
            except PlaywrightTimeoutError:
                print(f"❌ timeout opening detail at page {current_page}, row {i + 1}")
                detail = {
                    "detail_raw": "",
                    "detail_url": "",
                    "เลขคดี_detail": "",
                    "โจทก์": "",
                    "จำเลย": "",
                    "ประเภททรัพย์_detail": "",
                    "เนื้อที่_detail": "",
                    "ตำบล_detail": "",
                    "อำเภอ_detail": "",
                    "จังหวัด_detail": "",
                    "ผู้ถือกรรมสิทธิ์": "",
                    "ติดต่อ": "",
                    "สถานที่จำหน่าย": "",
                    "เจ้าของสำนวน": "",
                    "detail_error": "timeout",
                }

            merged = {**summary, **detail}
            if is_mortgage_attached(merged):
                print(f"⚠️ skip mortgage-attached listing: row {i + 1}")
                continue
            merged.pop("_sale_method", None)
            all_results.append(merged)
            save_to_csv(all_results, OUTPUT_CSV)

        if not go_to_next_page(page):
            break

    return all_results


def scrape_summary_from_row(row) -> dict | None:
    cols = row.locator("td")
    if cols.count() < len(SUMMARY_FIELDS):
        return None

    table = row.locator("xpath=ancestor::table[1]")
    headers = table.locator("thead th")
    header_indexes = {
        normalize_text(headers.nth(i).inner_text()): i for i in range(headers.count())
    }
    # The site's "ขนาด" header is a colspan group. Its child headers appear
    # after the other headers in the DOM, while row cells keep size in-place.
    # Use the row order when this grouped header is present.
    if "ขนาด" in header_indexes:
        return {
            field: normalize_text(cols.nth(i).inner_text())
            for i, field in enumerate(SUMMARY_FIELDS)
        }

    aliases = {
        "หมายเลขคดี": ["หมายเลขคดี", "เลขคดี", "หมายเลขคดีแดง"],
        "ตรว": ["ตรว", "ตร.วา", "ตร.วา/ตร.ม."],
    }

    values = {}
    for field in SUMMARY_FIELDS:
        possible_headers = aliases.get(field, [field])
        index = next((header_indexes.get(name) for name in possible_headers if name in header_indexes), None)
        if index is None or index >= cols.count():
            index = SUMMARY_FIELDS.index(field)
        values[field] = normalize_text(cols.nth(index).inner_text())
    return values


def result_key(row: dict) -> tuple[str, ...]:
    """Build a stable key so pagination/navigation cannot duplicate rows."""
    return (
        normalize_text(row.get("หมายเลขคดี", "")),
        normalize_text(row.get("ล็อต", "")),
        normalize_text(row.get("ลำดับ", "")),
        normalize_text(row.get("จังหวัด", "")),
    )


def open_row_and_scrape_detail(page, row_index: int) -> dict:
    row = page.locator(f"{TABLE_SELECTOR} tbody tr").nth(row_index)

    # Each result row submits a form to asset_open.asp with target=_blank.
    with page.expect_popup(timeout=15000) as popup_info:
        row.click()
    detail_page = popup_info.value
    try:
        detail_page.wait_for_load_state("domcontentloaded", timeout=30000)
        return scrape_detail_page(detail_page)
    finally:
        detail_page.close()

def scrape_detail_page(page) -> dict:
    """
    เวอร์ชัน generic ก่อน:
    - ดึง text ทั้งหน้า
    - แปลง label:value เท่าที่หาได้
    - เก็บ raw text เผื่อใช้ภายหลัง
    """
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1000)

    body_text = page.locator("body").inner_text()
    detail = parse_detail_pairs_from_body(body_text)
    detail["_sale_method"] = extract_sale_method(body_text)

    deed_number = page.locator('input[name="deedno"]')
    if deed_number.count() > 0:
        detail["โฉนดที่ดิน"] = normalize_text(deed_number.first.input_value())
    else:
        deed_match = re.search(r"โฉนดเลขที่\s*([^\s]+)", body_text)
        if deed_match:
            detail["โฉนดที่ดิน"] = normalize_text(deed_match.group(1))

    base_price = select_base_price(body_text)
    statuses = extract_auction_statuses(page)
    latest_status = statuses[-1] if statuses else ""
    no_bid_count = sum(is_no_bid_status(status) for status in statuses)
    detail["ราคา_final"] = format_amount(
        calculate_final_price(base_price, latest_status, no_bid_count)
    )
    detail["deposit_amount"] = format_amount(extract_standard_deposit(body_text))

    # เก็บข้อความเต็มไว้ด้วย เผื่อคุณจะเอาไป parse ต่อใน web ภายหลัง
    detail["detail_raw_text"] = body_text
    detail["detail_url"] = page.url

    return detail


def parse_detail_pairs_from_body(text: str) -> dict:
    """
    fallback parser:
    พยายามแยกข้อมูลหน้า detail แบบ 'label : value'
    ใช้ได้แม้ยังไม่รู้ selector ชัดเจน
    """
    detail = {}
    lines = [normalize_text(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    detail_labels = {
        "คดีหมายเลขแดงที่": "เลขคดี_detail",
        "โจทก์": "โจทก์",
        "จำเลย": "จำเลย",
        "ประเภททรัพย์": "ประเภททรัพย์_detail",
        "เนื้อที่": "เนื้อที่_detail",
        "แขวง/ตำบล": "ตำบล_detail",
        "เขต/อำเภอ": "อำเภอ_detail",
        "จังหวัด": "จังหวัด_detail",
        "ผู้ถือกรรมสิทธิ์": "ผู้ถือกรรมสิทธิ์",
        "เจ้าของสำนวน": "เจ้าของสำนวน",
        "สถานที่จำหน่าย": "สถานที่จำหน่าย",
        "จะทำการขายโดย": "_sale_method",
    }

    for index, line in enumerate(lines):
        deed_match = re.match(r"^โฉนดเลขที่\s*(.+)$", line)
        if deed_match:
            detail["โฉนดที่ดิน"] = normalize_text(deed_match.group(1))
            continue

        m = re.match(r"^(.+?)\s*[:：]\s*(.+)$", line)
        if m:
            key = normalize_text(m.group(1))
            value = normalize_text(m.group(2))
            if key and value:
                detail[key] = value
            continue

        target_key = detail_labels.get(line)
        if target_key and index + 1 < len(lines):
            detail[target_key] = lines[index + 1]

    return detail


def parse_amount_after_label(text: str, label: str) -> Decimal | None:
    pattern = rf"{re.escape(label)}.*?จำนวน\s*(ไม่มี|[\d,]+(?:\.\d+)?)\s*บาท"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match or match.group(1) == "ไม่มี":
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def select_base_price(text: str) -> Decimal:
    for label in PRICE_PRIORITY_LABELS:
        amount = parse_amount_after_label(text, label)
        if amount is not None:
            return amount
    return Decimal("0")


def calculate_final_price(base_price: Decimal, latest_status: str, no_bid_count: int) -> Decimal:
    # Any recorded no-bid auction lowers the next price; the latest '-' row
    # represents the next scheduled auction and must not reset the discount.
    if no_bid_count <= 0:
        return base_price
    discount = {1: Decimal("0.10"), 2: Decimal("0.20")}.get(
        no_bid_count, Decimal("0.30") if no_bid_count >= 3 else Decimal("0")
    )
    return base_price * (Decimal("1") - discount)


def extract_auction_statuses(page) -> list[str]:
    statuses = []
    for table_index in range(page.locator("table").count()):
        table = page.locator("table").nth(table_index)
        table_text = normalize_text(table.inner_text())
        if "นัดที่" not in table_text or "สถานะ" not in table_text:
            continue
        rows = table.locator("tbody tr")
        for row_index in range(rows.count()):
            cells = rows.nth(row_index).locator("td")
            if cells.count() >= 3:
                statuses.append(normalize_text(cells.nth(2).inner_text()))
        if statuses:
            break
    return statuses


def is_no_bid_status(status: str) -> bool:
    """Match the status even when the site adds whitespace or extra text."""
    return NO_BID_STATUS in normalize_text(status)


def extract_standard_deposit(text: str) -> Decimal:
    match = re.search(
        r"ผู้ประสงค์จะเข้าเสนอราคา.*?หลักประกันเป็นจำนวน\s*"
        r"([\d,]+(?:\.\d+)?)\s*บาท",
        text,
        flags=re.DOTALL,
    )
    if not match:
        return Decimal("0")
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return Decimal("0")


def format_amount(amount: Decimal) -> str:
    return f"{amount:,.2f}"


def is_mortgage_attached(row: dict) -> bool:
    sale_method = normalize_text(row.get("_sale_method", row.get("จะทำการขายโดย", "")))
    return "การจำนองติดไป" in sale_method


def extract_sale_method(text: str) -> str:
    match = re.search(
        r"จะทำการขายโดย\s*(.*?)(?=ราคาประเมินของ|วันที่ประกาศขึ้นเว็บ|$)",
        text,
        flags=re.DOTALL,
    )
    return normalize_text(match.group(1)) if match else ""


def go_to_next_page(page) -> bool:
    """
    พยายามกดปุ่มไปหน้าถัดไป
    ถ้าไม่มีหน้าถัดไปให้คืน False
    """
    current_text = normalize_text(page.locator("body").inner_text())
    current_match = re.search(r"หน้าที่\s*(\d+)\s*/\s*(\d+)", current_text)

    if not current_match:
        return False

    current_page = int(current_match.group(1))
    total_pages = int(current_match.group(2))

    if current_page >= total_pages:
        return False

    # พยายามหาปุ่มหน้าถัดไปหลายแบบ
    candidates = [
        "text=ถัดไป",
        "text=>",
        "text=›",
        "img[alt*='next']",
        "a[title*='next']",
        "button[title*='next']",
    ]

    for selector in candidates:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.click(no_wait_after=True)
            page.wait_for_timeout(1500)
            page.wait_for_selector(f"{TABLE_SELECTOR} tbody tr", timeout=60000)
            return True

    # fallback: ลองกด link ที่เป็นเลขหน้าถัดไป
    next_page_number = str(current_page + 1)
    locator = page.locator(f"text='{next_page_number}'")
    if locator.count() > 0:
        locator.first.click(no_wait_after=True)
        page.wait_for_timeout(1500)
        page.wait_for_selector(f"{TABLE_SELECTOR} tbody tr", timeout=60000)
        return True

    return False


def save_to_csv(results: list[dict], filename: str) -> None:
    base_headers = SUMMARY_FIELDS

    if not results:
        candidate_headers = base_headers + ["Location"]
    else:
        extra_headers = []
        seen = set(base_headers)
        for row in results:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    extra_headers.append(key)
        candidate_headers = base_headers + extra_headers
    headers = []
    seen_signatures = {}
    for header in candidate_headers:
        if normalize_text(header) in EXCLUDED_CSV_COLUMNS:
            continue

        # Keep the first column when two columns contain the same values.
        values = [normalize_text(str(row.get(header, ""))) for row in results]
        if not any(values):
            headers.append(header)
            continue
        signature = tuple(values)
        if signature in seen_signatures:
            print(f"⚠️ duplicate CSV column skipped: {header}")
            continue
        seen_signatures[signature] = header
        headers.append(header)

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8-sig", dir=output_path.parent,
        prefix=f".{output_path.name}.", suffix=".tmp", delete=False,
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=headers,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(results)
        temp_path = Path(file.name)

    temp_path.replace(output_path)

    print(f"✅ saved CSV: {filename}" if results else f"⚠️ saved empty CSV: {filename}")


def normalize_landsmaps_name(value: str) -> str:
    """Match LandsMaps names despite district codes and parenthetical suffixes."""
    value = normalize_text(value)
    value = re.sub(r"\s*\([^)]*\)", "", value)
    return re.sub(r"^[^\-]+-", "", value)


def landsmaps_name_candidates(value: str) -> list[str]:
    candidates = [normalize_landsmaps_name(value)]
    for part in re.findall(r"\(([^)]*)\)", value):
        normalized = normalize_landsmaps_name(part)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def find_option_value(page, selector: str, target: str) -> str | None:
    target_normalized = normalize_landsmaps_name(target)
    options = page.locator(f"{selector} option")
    partial_match = None
    for i in range(options.count()):
        option = options.nth(i)
        label = normalize_landsmaps_name(option.inner_text())
        value = option.get_attribute("value")
        if not value or value == "00":
            continue
        if label == target_normalized:
            return value
        if target_normalized and target_normalized in label:
            partial_match = value
    return partial_match


def wait_for_amphur_option(page, amphur_name: str, timeout_ms: int = 15000) -> str:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        value = find_option_value(page, "#cbamphur", amphur_name)
        if value:
            return value
        page.wait_for_timeout(200)
    raise RuntimeError(f"ไม่พบอำเภอใน LandsMaps: {amphur_name}")


def extract_landsmaps_location(text: str) -> str:
    """Extract the coordinate pair displayed in the LandsMaps result dialog."""
    match = re.search(
        r"ค่าพิกัดแปลง\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)",
        text,
    )
    if not match:
        raise LookupError("LandsMaps ไม่พบค่าพิกัดแปลงในผลลัพธ์")
    return f"{match.group(1)},{match.group(2)}"


def search_landsmaps_via_ui(page, province_value: str, amphur_value: str, deed: str) -> str:
    """Use the same visible search flow as a user when the direct API fails."""
    page.select_option("#cbprovince", value=province_value)
    page.select_option("#cbamphur", value=amphur_value)
    page.locator("#faketxtparcelno").fill(deed)

    buttons = page.locator("button").filter(has_text="ค้นหา")
    if buttons.count() > 0:
        buttons.last.click()
    else:
        inputs = page.locator(
            'input[type="button"][value*="ค้นหา"], '
            'input[type="submit"][value*="ค้นหา"]'
        )
        if inputs.count() == 0:
            raise RuntimeError("ไม่พบปุ่มค้นหาใน LandsMaps")
        inputs.last.click()

    page.wait_for_function(
        "() => document.body.innerText.includes('ค่าพิกัดแปลง')",
        timeout=30000,
    )
    location = extract_landsmaps_location(page.locator("body").inner_text())

    close_buttons = page.locator("button").filter(has_text="ปิดหน้าต่าง")
    if close_buttons.count() > 0:
        close_buttons.last.click()
    return location


def get_landsmaps_location(page, row: dict, search_api: str, access_token: str) -> str:
    province = row.get("จังหวัด_detail", "")
    amphur = row.get("อำเภอ_detail", "")
    deed = normalize_text(row.get("โฉนดที่ดิน", ""))
    if not province or not amphur or not deed:
        raise ValueError("ข้อมูลจังหวัด_detail, อำเภอ_detail หรือ โฉนดที่ดิน ไม่ครบ")

    province_value = find_option_value(page, "#cbprovince", province)
    if not province_value:
        raise RuntimeError(f"ไม่พบจังหวัดใน LandsMaps: {province}")
    page.select_option("#cbprovince", value=province_value)
    last_error = None
    for amphur_candidate in landsmaps_name_candidates(amphur):
        try:
            amphur_value = wait_for_amphur_option(page, amphur_candidate)
            page.select_option("#cbamphur", value=amphur_value)
            page.locator("#faketxtparcelno").fill(deed)

            data = page.evaluate(
                """
                async ({url, token, province, amphur, deed}) => {
                    const response = await fetch(`${url}${province}/${amphur}/${deed}`, {
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    return { status: response.status, body: await response.json() };
                }
                """,
                {
                    "url": search_api,
                    "token": access_token,
                    "province": province_value,
                    "amphur": amphur_value,
                    "deed": deed,
                },
            )
            result = data.get("body", {}).get("result") or []
            if not result:
                last_error = LookupError(
                    f"LandsMaps ไม่พบข้อมูล: {province}/{amphur_candidate}/{deed}"
                )
                continue

            parcel = result[0]
            latitude = normalize_text(str(parcel.get("parcellat", "")))
            longitude = normalize_text(str(parcel.get("parcellon", "")))
            if latitude and longitude:
                return f"{latitude},{longitude}"
            last_error = LookupError(f"LandsMaps ไม่มีค่าพิกัด: {province}/{deed}")
        except Exception as error:
            last_error = error

    try:
        return search_landsmaps_via_ui(page, province_value, amphur_value, deed)
    except Exception as ui_error:
        raise RuntimeError(
            f"LandsMaps API และ UI ค้นหาไม่สำเร็จ: {province}/{amphur}/{deed}; "
            f"API={last_error}; UI={ui_error}"
        ) from ui_error


def enrich_locations_with_landsmaps(page, results: list[dict]) -> None:
    # Reuse the existing page/context so LandsMaps can initialize its sessionStorage token.
    page.goto(LANDSMAPS_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("#cbprovince", timeout=30000)
    config = page.evaluate(
        "async (url) => await (await fetch(url)).json()", LANDSMAPS_CONFIG_URL
    )
    page.wait_for_function(
        """() => {
            try {
                const user = JSON.parse(sessionStorage.getItem('userinfo'));
                return Boolean(user && user.access_token);
            } catch (_) {
                return false;
            }
        }""",
        timeout=30000,
    )
    userinfo = page.evaluate("JSON.parse(sessionStorage.getItem('userinfo'))")
    access_token = (userinfo or {}).get("access_token")
    search_api = config.get("getservicesearch")
    if not access_token or not search_api:
        raise RuntimeError("ไม่พบ LandsMaps API configuration หรือ access token")

    for index, row in enumerate(results, start=1):
        row.setdefault("Location", "")
        row.pop("Location_error", None)
        try:
            row["Location"] = get_landsmaps_location(
                page, row, search_api, access_token
            )
            print(f"📍 location {index}/{len(results)}: {row['Location']}")
        except Exception as error:
            row["Location"] = ""
            row["Location_error"] = str(error)
            print(f"⚠️ location {index}/{len(results)}: {error}")
        save_to_csv(results, OUTPUT_CSV)


def croped_captcha():
    img = Image.open("before_search.png")

    # crop(x1, y1, x2, y2)
    cropped = img.crop((80, 740, 180, 800))

    cropped.save("cropped.png")


def extract_ocr() -> str:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    img = Image.open("cropped.png")
    # CAPTCHA contains digits only; a single-line numeric OCR mode is more reliable.
    text = pytesseract.image_to_string(
        img,
        config="--psm 7 -c tessedit_char_whitelist=0123456789",
    )
    return "".join(re.findall(r"\d", text))


def wait_for_search_results(page) -> None:
    """Wait for results and report the site's validation message when search fails."""
    try:
        page.wait_for_selector(f"{TABLE_SELECTOR} tbody tr", timeout=60000)
    except PlaywrightTimeoutError as error:
        failure_screenshot = "search_failed.png"
        page.screenshot(path=failure_screenshot, full_page=True)
        body_text = normalize_text(page.locator("body").inner_text())
        known_messages = [
            "กรุณากรอกเงื่อนไขเพื่อค้นหา",
            "รหัสยืนยันไม่ถูกต้อง",
            "ไม่พบข้อมูล",
        ]
        message = next((item for item in known_messages if item in body_text), None)
        detail = message or "ไม่พบตารางผลลัพธ์ หรือโครงสร้างเว็บอาจเปลี่ยน"
        raise RuntimeError(
            f"ค้นหาไม่สำเร็จ: {detail}. บันทึกภาพไว้ที่ {failure_screenshot}"
        ) from error


def main() -> None:
    global OUTPUT_CSV
    config = load_config()
    search = config["search"]
    OUTPUT_CSV = config.get("output_csv", OUTPUT_CSV)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path=CHROME_PATH,
        )
        try:
            page = browser.new_page()
            page.goto(URL, wait_until="domcontentloaded")

            fill_province(page, search["province"])
            fill_search_area(
                page,
                search.get("amphur", ""),
                search.get("tambon", ""),
            )
            fill_asset_type(page, search.get("asset_type", ""))
            fill_land_area(page, search["rai_condition"], search["rai_value"])
            fill_price_range(
                page,
                search.get("minimum_price", ""),
                search.get("maximum_price", ""),
            )

            page.screenshot(path="before_search.png", full_page=True)
            print("📸 saved screenshot: before_search.png")

            croped_captcha()
            text = extract_ocr()
            print("OCR RESULT:", text)
            if not text:
                raise RuntimeError(
                    "OCR อ่าน CAPTCHA ไม่ได้ จึงไม่ส่งฟอร์มค้นหา "
                    "กรุณาตรวจ cropped.png หรือกรอก CAPTCHA ด้วยตนเอง"
                )

            page.fill('input[name="seckey"]', text)
            page.locator("#GFG_Button").click(no_wait_after=True)
            wait_for_search_results(page)

            results = scrape_all_pages_with_detail(page)
            save_to_csv(results, OUTPUT_CSV)
            print(f"✅ เว็บแสดงและบันทึกข้อมูลจำนวน {len(results)} รายการ")

            if results:
                enrich_locations_with_landsmaps(page, results)
                save_to_csv(results, OUTPUT_CSV)
                print("✅ เติม Location จาก LandsMaps เรียบร้อย")
            else:
                print("ℹ️ ข้าม LandsMaps เพราะไม่มีรายการให้ค้นหา")

            input("กด Enter เพื่อปิด browser...")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
