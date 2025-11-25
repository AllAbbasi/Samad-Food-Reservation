def get_foods_by_day_and_meal(page):
    """
    Extract foods by day and meal.
    """
    page.wait_for_selector('.reserve-program-col', timeout=10000)
    
    result = page.evaluate("""
        () => {
            const result = {};
            
            // Step 1: Get header columns (sticky row)
            const headerCols = document.querySelectorAll('.sticky.top-0 .reserve-program-col');
            
            // Step 2: Get food columns (find the flex div that has food items)
            let foodCols = [];
            const allFlexDivs = document.querySelectorAll('.flex');
            
            for (const flexDiv of allFlexDivs) {
                const cols = flexDiv.querySelectorAll(':scope > .reserve-program-col');
                if (cols.length === 0) continue;
                
                // Check if any column has food items
                let hasFood = false;
                for (const col of cols) {
                    if (col.querySelector('.program-reserve-item')) {
                        hasFood = true;
                        break;
                    }
                }
                
                if (hasFood) {
                    foodCols = Array.from(cols);
                    break;
                }
            }
            
            // Debug info
            console.log('Headers found:', headerCols.length);
            console.log('Food columns found:', foodCols.length);
            
            // Step 3: Match them by index
            for (let i = 0; i < Math.min(headerCols.length, foodCols.length); i++) {
                // Get day name
                const dayEl = headerCols[i].querySelector('.week-day-name');
                if (!dayEl) {
                    console.log('No day name at index', i);
                    continue;
                }
                
                const dayName = dayEl.textContent.trim();
                result[dayName] = { 'ناهار': [], 'شام': [] };
                
                // Get food items in this column
                const items = foodCols[i].querySelectorAll('.program-reserve-item');
                console.log('Day:', dayName, 'Items:', items.length);
                
                items.forEach(item => {
                    const mealEl = item.querySelector('.font-bold');
                    const nameEl = item.querySelector('.item-name');
                    const priceEl = item.querySelector('.item-price');
                    
                    if (mealEl && nameEl) {
                        const meal = mealEl.textContent.trim();
                        const name = nameEl.textContent.trim();
                        const price = priceEl ? priceEl.textContent.trim() : '';
                        
                        if (!result[dayName][meal]) {
                            result[dayName][meal] = [];
                        }
                        
                        result[dayName][meal].push({ name: name, price: price });
                    }
                });
            }
            
            return result;
        }
    """)
    
    return result



def reserve_food(page, day_identifier, meal_type, food_name, other_options=[], max_retries=3):
    """
    Reserve a food or increase quantity if already reserved (synchronous version).
    Filters by day to find the correct food item.
    
    Args:
        page: Playwright page (synchronous)
        day_identifier: Day name or date (e.g., 'سه‌شنبه', 'سهشنبه', or '11 آذر')
        meal_type: 'ناهار' or 'شام'
        food_name: Food name to reserve
        max_retries: Maximum number of retry attempts
    
    Returns:
        bool: Success status
    """
    page.wait_for_selector('.program-reserve-item', timeout=10000)
    page.wait_for_timeout(1000)
    
    for attempt in range(max_retries):
        # Find and click the reserve button for the specific day
        result = page.evaluate("""
            ({ dayId, meal, foodName }) => {
                // Find all columns
                const allCols = document.querySelectorAll('.reserve-program-col');
                
                // First 7 columns are day headers, next 7 are food columns
                const dayHeaders = Array.from(allCols).slice(0, 7);
                const foodColumns = Array.from(allCols).slice(7, 14);
                
                // Find which day index matches
                let dayIndex = -1;
                for (let i = 0; i < dayHeaders.length; i++) {
                    const dayText = dayHeaders[i].textContent || '';
                    if (dayText.includes(dayId)) {
                        dayIndex = i;
                        break;
                    }
                }
                
                if (dayIndex === -1) {
                    return { success: false, action: 'day_not_found', dayIndex: -1 };
                }
                
                // Get the corresponding food column
                const foodColumn = foodColumns[dayIndex];
                if (!foodColumn) {
                    return { success: false, action: 'column_not_found', dayIndex: dayIndex };
                }
                
                // Search for food items only in this column
                const items = foodColumn.querySelectorAll('.program-reserve-item');
                
                for (const item of items) {
                    const mealEl = item.querySelector('.font-bold');
                    const nameEl = item.querySelector('.item-name');
                    
                    if (mealEl && nameEl) {
                        const itemMeal = mealEl.textContent.trim();
                        const itemName = nameEl.textContent.trim();
                        
                        if (itemMeal === meal && itemName === foodName) {
                            // Check if there's a reserve button (not yet reserved)
                            const reserveBtn = item.querySelector('.button-reserve');
                            if (reserveBtn) {
                                reserveBtn.click();
                                return { success: true, action: 'reserved', dayIndex: dayIndex };
                            }
                            
                            // Check if already reserved - look for increment button
                            const incBtn = item.querySelector('.reserve-inc');
                            if (incBtn) {
                                incBtn.click();
                                return { success: true, action: 'increased', dayIndex: dayIndex };
                            }
                            
                            return { success: false, action: 'already_reserved_no_inc', dayIndex: dayIndex };
                        }
                    }
                }
                
                return { success: false, action: 'not_found', dayIndex: dayIndex };
            }
        """, {'dayId': day_identifier, 'meal': meal_type, 'foodName': food_name})
        
        # Handle errors based on action
        if not result['success']:
            if result['action'] == 'day_not_found':
                print(f"✗ Day '{day_identifier}' not found")
                return False
            elif result['action'] == 'column_not_found':
                print(f"✗ Food column not found for day index {result['dayIndex']}")
                return False
            elif result['action'] == 'not_found':
                print(f"✗ '{food_name}' not found for {meal_type} on day index {result['dayIndex']}")
                return False
        
        # Wait for response
        page.wait_for_timeout(1500)
        
        # Check for error alert
        has_error = False
        try:
            alerts = page.get_by_role("alert").all()
            for alert in alerts:
                text = alert.text_content()
                if text and "خطای نامشخصی رخ داده است" in text:
                    has_error = True
                    print(f"Error (attempt {attempt + 1}/{max_retries}): {text.strip()}")
                elif text and "مورد انتخابی تا حداکثر سقف ممکن، توسط کاربران رزرو شده است!" in text:
                    print(f"Reservation limit reached for '{food_name}' ({meal_type}) on day index {result['dayIndex']}")
                    if other_options:
                        print(f"Reserving next best option.")
                        return reserve_food(page, day_identifier, meal_type, other_options[0], other_options=other_options[1:], max_retries=3)
                else:
                    print(f"Alert: {text.strip()}")
                page.get_by_text(text.strip()).click()
        except:
            pass
        
        if has_error:
            if attempt < max_retries - 1:
                print(f"Retrying...")
                page.wait_for_timeout(1000)
                continue
            else:
                print(f"✗ Failed after {max_retries} attempts")
                return False
        
        # Success!
        if result['action'] == 'reserved':
            print(f"✓ Reserved '{food_name}' ({meal_type}) for day index {result['dayIndex']}")
        elif result['action'] == 'increased':
            print(f"✓ Increased quantity for '{food_name}' ({meal_type}) for day index {result['dayIndex']}")
        elif result['action'] == 'already_reserved_no_inc':
            print(f"! '{food_name}' is already reserved (day index {result['dayIndex']})")
        
        return result['success']
    
    return False
