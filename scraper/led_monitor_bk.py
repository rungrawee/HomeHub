from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
import pytesseract
import csv

URL = "https://asset.led.go.th/newbidreg/default.asp"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def croped_captcha():
    img = Image.open("led_full.png")

    # crop(x1, y1, x2, y2)
    cropped = img.crop((570, 600, 650, 650))

    cropped.save("cropped.png")

def extract_ocr() -> str:
    pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

    img = Image.open("cropped.png")
    txt = pytesseract.image_to_string(img, lang="tha+eng")
    return txt

def fill_search_form(page):
    # จังหวัด
    province = page.locator("input#data.search-box")
    province.click()
    province.fill("")
    province.type("นนทบุรี", delay=80)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")

    # เงื่อนไขไร่ = มากกว่า
    page.select_option('select[name="rai_if"]', label="มากกว่า")

    # ใส่ค่าไร่ = 5
    used = fill_first_existing(
        page,
        selectors=[
            'input[name="rai"]',
            'input[name="Rai"]',
            'input[name="area_rai"]',
            'input[placeholder*="ไร่"]',
        ],
        value="5"
    )
    print("✅ filled rai using:", used)

    # งาน = 0 (ถ้ามี)
    if page.locator('input[name="quaterrai"]').count() > 0:
        page.fill('input[name="quaterrai"]', "0")

    # ตร.ว. = 0 (ถ้ามี)
    for wa_sel in [
        'input[name="wa"]',
        'input[name="squarewa"]',
        'input[placeholder*="ตร."]'
    ]:
        if page.locator(wa_sel).count() > 0:
            page.locator(wa_sel).first.fill("0")
            break


def fill_first_existing(page, selectors, value: str):
    for sel in selectors:
        loc = page.locator(sel)
        if loc.count() > 0:
            loc.first.fill(value)
            return sel
    raise RuntimeError(f"Cannot find any input from selectors: {selectors}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, executable_path=CHROME_PATH)
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded")

    # ---- จังหวัด (autocomplete) ----
    province = page.locator("input#data.search-box")
    province.click()
    province.fill("")
    province.type("นนทบุรี", delay=80)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")

    # ---- ขนาดเนื้อที่: มากกว่า 5 ไร่ ----
    # เลือกเงื่อนไข "มากกว่า" ของ "ไร่"
    page.select_option('select[name="rai_if"]', label="มากกว่า")

    # ใส่ค่าไร่ = 5 (ลองหลายชื่อเผื่อเว็บใช้ name ไม่เหมือนกัน)
    used = fill_first_existing(
        page,
        selectors=[
            'input[name="rai"]',
            'input[name="Rai"]',
            'input[name="area_rai"]',
            'input[placeholder*="ไร่"]',
        ],
        value="5"
    )

    # (ไม่จำเป็น) ใส่งาน/ตรว. เป็น 0 ให้ครบ
    if page.locator('input[name="quaterrai"]').count() > 0:
        page.fill('input[name="quaterrai"]', "0")

    for wa_sel in [
        'input[name="wa"]',
        'input[name="squarewa"]',
        'input[placeholder*="ตร."]'
    ]:
        if page.locator(wa_sel).count() > 0:
            page.locator(wa_sel).first.fill("0")
            break

            pw = sync_playwright().start()
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto("https://asset.led.go.th/newbidreg/default.asp")

            print(page.content())
            print(page.title())

            browser.close()
            pw.stop()

    # # ---- CAPTCHA แล้วค่อยค้นหา ----
    # input("กรอก CAPTCHA ให้เสร็จ แล้วกด Enter เพื่อค้นหา...")

    print("✅ filled rai using:", used)
    page.screenshot(path="led_full.png", full_page=True)
    print("📸 บันทึกภาพแล้ว: led_full.png")

    croped_captcha()
    text = extract_ocr()

    print("OCR RESULT:", text)
    page.fill('input[name="seckey"]', text)

    page.click("#GFG_Button")
    page.wait_for_selector("table", timeout=60000)
    page.wait_for_selector("#box-table-a tbody tr")

    rows = page.locator("#box-table-a tbody tr")

    print("จำนวนรายการ:", rows.count())

    for i in range(rows.count()):
        cols = rows.nth(i).locator("td")

        lot = cols.nth(0).inner_text().strip()
        order = cols.nth(1).inner_text().strip()
        case_no = cols.nth(2).inner_text().strip()
        asset_type = cols.nth(3).inner_text().strip()

        rai = cols.nth(4).inner_text().strip()
        ngan = cols.nth(5).inner_text().strip()
        wah = cols.nth(6).inner_text().strip()

        price = cols.nth(7).inner_text().strip()
        subdistrict = cols.nth(8).inner_text().strip()
        district = cols.nth(9).inner_text().strip()
        province = cols.nth(10).inner_text().strip()

        print({
            "ล็อต": lot,
            "ลำดับ": order,
            "หมายเลขคดี": case_no,
            "ประเภท": asset_type,
            "ไร่": rai,
            "งาน": ngan,
            "ตรว": wah,
            "ราคา": price,
            "ตำบล": subdistrict,
            "อำเภอ": district,
            "จังหวัด": province
        })

    with open("result.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["ล็อต", "ลำดับ", "หมายเลขคดี", "ประเภท", "ไร่", "งาน", "ตรว", "ราคา", "ตำบล", "อำเภอ", "จังหวัด"])

        for i in range(rows.count()):
            cols = rows.nth(i).locator("td")
            writer.writerow([cols.nth(j).inner_text().strip() for j in range(cols.count())])

    input("กด Enter เพื่อปิด...")
    browser.close()

# def save_csv(page, selectors, value: str):
