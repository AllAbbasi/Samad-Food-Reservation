from collections import defaultdict
import re
import time
from typing import Dict, List
from playwright.sync_api import Playwright, sync_playwright, expect
import json
from utils import *
from page_interactions import *
from CSP_solver import *
from tqdm import tqdm
import argparse


def run(playwright: Playwright, args) -> None:
    browser = playwright.chromium.launch(headless=args.quiet)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://samad.app/login")
    page.get_by_text(USER_INFO['university']).click()
    page.get_by_text("ورود با نام کاربری و رمز عبور").click()
    # page.get_by_role("textbox", name="نام کاربری").click()
    page.get_by_role("textbox", name="نام کاربری").fill(str(USER_INFO["username"]))
    # page.get_by_role("textbox", name="رمز عبور").click()
    page.get_by_role("textbox", name="رمز عبور").fill(str(USER_INFO["password"]))
    page.get_by_role("button", name="ورود").click()
    page.get_by_role("button", name="ورود به رابط کاربری دانشجویی").click()
    page.get_by_text("رزرو غذا").click()
    # for choosing self
    page.locator("div").filter(has_text=re.compile(r"^کاله پردیس مرکزی\(بیرون بر\)$")).click()
    page.get_by_role("button", name="Close").click()
    page.get_by_text("هفته بعد").click()

    overall_food_schedule : Dict[tuple, List[str]] = defaultdict(list)
    partial = False
    for salon in (pbar := tqdm(set(USER_INFO["lunch-salons"] + USER_INFO["dinner-salons"]))):
        pbar.set_postfix_str(f"Getting foods from {salon}")
        page.locator(".flaticon-left-chevron").first.click()
        page.locator("div.self-list-item").filter(has_text=words_presence_regex(salon)).last.click()
        page.wait_for_timeout(1000)

        # see if food plan is avialable:
        locator = page.get_by_text("هیچ برنامه ی غذایی ای برای این تاریخ تعریف نشده است")
        if locator.count() > 0:
            print(f"No meal plan defined for {salon}")
            partial = True
            continue
        expect(page.get_by_text("جزئیات بیشتر").first).to_be_visible()
        # dict{day : dict{meal: foods}}
        salon_schedule = get_foods_by_day_and_meal(page)
        normalized_salon_schedule = transform_food_schedule(salon_schedule, salon)
        for meal_day, foods in normalized_salon_schedule.items():
            overall_food_schedule[meal_day].extend(foods)

    # convertng preferences to full names
    this_week_foods = {food for foods in overall_food_schedule.values() for food, *_ in foods}
    update_all_foods(this_week_foods)

    should_reseve = True
    if not overall_food_schedule:
        print("No food is avialble yet")
        should_reseve = False
    if args.update:
        print("Food schedule updated. Exiting as per --update flag.")
        should_reseve = False
    if should_reseve and partial:
        should_reseve = input("Some salons are missing. Partial reserve? (Y/N)").lower() == 'y'
    if not should_reseve:
        context.close()
        browser.close()
        return

    preferences = match_short_to_full_foodnames(this_week_foods, PREFERENCES)
    preferences = {food: len(preferences) - i for i, food in enumerate(preferences)}

    # solving CSP
    reserve_solution = solve_food_schedule(overall_food_schedule, preferences, CONSTRAINTS)
    saolon_reserves = defaultdict(list)
    for (day, meal), (food, meal_type, salon) in reserve_solution.items():
        saolon_reserves[salon].append((day, meal_type, food))

    for salon, reserves in saolon_reserves.items():
        pbar.set_postfix_str(f"Getting foods from {salon}")
        page.locator(".flaticon-left-chevron").first.click()
        page.locator("div.self-list-item").filter(has_text=words_presence_regex(salon)).last.click()
        expect(page.get_by_text("جزئیات بیشتر").first).to_be_visible()
        page.wait_for_timeout(1000)

        for day, meal_type, food_name in reserves:
            other_options = [
                f for f, mtype, salon_name in overall_food_schedule[(day, meal_type)]
                if f != food_name
            ]
            other_options.sort(key=lambda f: -preferences.get(f, 0))
            success = reserve_food(page, day, meal_type, food_name, other_options=other_options, max_retries=5)
    # ---------------------
    context.close()
    browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true", help="Don't show the browser window")
    parser.add_argument("--update", action="store_true", help="Only update the all_foods.txt with new foods appended, without making reservations")
    args = parser.parse_args()


    with open("info/personal_info.json", "r", encoding="utf-8") as file:
        USER_INFO = json.load(file)

    with open("info/constraints.json", "r", encoding="utf-8") as file:
        CONSTRAINTS = json.load(file)

    with open("info/preferences.txt", "r", encoding="utf-8") as file:
        PREFERENCES = [line.strip() for line in file.readlines() if line.strip()]

    validate(USER_INFO)
    with sync_playwright() as playwright:
        run(playwright, args)
