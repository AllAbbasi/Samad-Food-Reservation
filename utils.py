import re


def words_presence_regex(words):
    """Simple: check if all words are present in target."""
    if isinstance(words, str):
        words = words.split()
    # Just check each word is somewhere in the text
    pattern = "".join(rf"(?=.*{re.escape(w)})" for w in words)
    return re.compile(pattern)


def match_short_to_full_foodnames(week_food, short_foodnames):
    """
    Match short food names to full names, selecting the shortest match when multiple exist.
    """
    food_names = []
    for food_name_short in short_foodnames:
        pattern = words_presence_regex(food_name_short)
        matches = []

        # Find all matching foods
        for food in week_food:
            if re.search(pattern, food):  # Use search, not match
                matches.append(food)

        if matches:
            # Select the shortest match
            shortest = min(matches, key=len)
            food_names.append(shortest)
            week_food.remove(shortest) # Avoid reusing the same food
        else:
            # No match found - you can handle this differently if needed
            print(f"Warning: No match found for '{food_name_short}'")

    return food_names


def transform_food_schedule(raw_schedule, salon_name=None):
    """
    Transform the crawled food schedule from the web scraper format to the format
    expected by solve_food_schedule.

    Input format:
        {day: {meal_type: [{'name': food_name, 'price': price}, ...]}}

    Output format:
        {f"{day}_{meal_type}": [food_name1, food_name2, ...]}

    Args:
        raw_schedule: Dict with day keys containing meal types and food objects

    Returns:
        Dict with "day_mealtype" keys and lists of food names as values
    """
    transformed = {}

    for day, meals in raw_schedule.items():
        for meal_type, foods in meals.items():
            # Create a unique key combining day and meal type
            meal_key = day, meal_type

            # Extract just the food names from the list of dicts
            food_names = (
                [
                    (
                        f'{food["name"]}',
                        meal_type,
                        salon_name
                    )
                    for food in foods
                ]
                if foods
                else []
            )

            # Only add if there are foods available
            if food_names:
                transformed[meal_key] = food_names

    return transformed


def validate(user_info):
    return True


def update_all_foods(this_week_foods):
    try:
        with open('info/all_foods.txt', 'r', encoding="utf-8") as f:
            foods_sofar = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        foods_sofar = set()

    new_foods = this_week_foods - foods_sofar

    # Append just the new ones
    if new_foods:
        with open('info/all_foods.txt', 'a', encoding="utf-8") as f:
            f.write('\n')  # Separate entries
            for food in sorted(new_foods):
                f.write(food + '\n')