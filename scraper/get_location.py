#!/usr/bin/env python3
"""Look up one land parcel location from LandsMaps."""

import argparse

from playwright.sync_api import sync_playwright

from led_monitor import (
    CHROME_PATH,
    LANDSMAPS_CONFIG_URL,
    LANDSMAPS_URL,
    get_landsmaps_location,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ค้นหาค่าพิกัดแปลงจาก LandsMaps ด้วยจังหวัด อำเภอ และเลขที่โฉนด"
    )
    parser.add_argument("--province", required=True, help="ชื่อจังหวัด")
    parser.add_argument("--amphur", required=True, help="ชื่ออำเภอ")
    parser.add_argument("--deed", required=True, help="เลขที่โฉนด")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            executable_path=CHROME_PATH,
        )
        try:
            page = browser.new_page()
            page.goto(LANDSMAPS_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("#cbprovince", timeout=30000)

            config = page.evaluate(
                "async (url) => await (await fetch(url)).json()",
                LANDSMAPS_CONFIG_URL,
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

            row = {
                "จังหวัด_detail": args.province,
                "อำเภอ_detail": args.amphur,
                "โฉนดที่ดิน": args.deed,
            }
            location = get_landsmaps_location(
                page, row, search_api, access_token
            )
            print(f"Location: {location}")
            print(f"Google Maps: https://www.google.com/maps?q={location}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
