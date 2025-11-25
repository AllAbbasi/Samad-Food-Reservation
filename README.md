## How to Run

### Prerequisites

```bash
# Optionally create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows `venv\Scripts\activate`

pip install -r requirements.txt
playwright install chromium
```

### Configuration

Before running the script, make sure to fill out the following configuration files with your details:

1.  **`personal_info.json`**: Add your login credentials and your preferred salons.
2.  **`preferences.txt`**: List your food preferences. It does not need to be the excat name. It can only contain key words (e.g. `جوجه کاله`) and it will be mapped to the closest option. You can reorder current list using alt+up/down keys in vscode. Also `all_foods.txt` gets updated with all the food options the bot has encountered.
3.  **`constraints.json`**: Define constraints on a list of foods. This list  needs only key words. Currently supported constraints are `limit` (the amount of times foods from that group should be reserved) and `gap` (**number of meals** that those foods should be apart).
For example you can limit your fast food intake by something like this:
```json
{
    "foods": ["پیتزا", "ناگت", "برگر", "ساندویچ"],
    "limit": 2,  # only twice a week
    "gap": 2  # at least 2 meals (1 day) apart
}
```

### Usage

Run the main script in your environment:

```bash
python main.py
```

Additional command-line options:
```
--quiet     Don't show the browser window
--update    Only update `all_foods.txt` with new foods appended, without making reservations
```

### To Do
- [ ] Reserving dinners from both dorm and university (`سلف مرکزی بیرون بر`)