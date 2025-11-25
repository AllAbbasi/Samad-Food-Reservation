from ortools.sat.python import cp_model
import re
from utils import *


def solve_food_schedule(food_schedule, preferences, constraints=[], time_limit=None):
    """
    Solve food scheduling problem with grouped constraints.
    
    Args:
        food_schedule: dict from (day, meal_type) to list of (food, meal_type, salon)
        preferences: dict from food names to scores
        constraints: List of dicts, e.g.:
                     [
                        {"foods": ["Pizza", "Nugget"], "limit": 2},
                        {"foods": ["Kebab"], "limit": 2, "gap": 3}
                     ]
        time_limit: Max time in seconds
    """
    
    # Ensure day_meals is consistent (sorting by day recommended if keys aren't sorted)
    print(f'User preferences:\n{preferences}')
    
    model = cp_model.CpModel()
    
    # --- 1. Variables & Basic Setup ---
    day_meals = list(food_schedule.keys())    
    meal_vars = {}
    meal_to_options = {}
    option_to_details = {}
    meal_score_vars = {}
    
    for meal, options in food_schedule.items():
        if options:
            # Variable for which option is selected (0 to N-1)
            meal_vars[meal] = model.NewIntVar(0, len(options) - 1, f'meal_{meal}')
            meal_to_options[meal] = options
            
            # Map index back to details for final output
            for idx, (food, mtype, salon) in enumerate(options):
                option_to_details[(meal, idx)] = (food, mtype, salon)
            
            # Optimization: Link selection to Score
            option_scores = [preferences.get(food, 0) for food, _, _ in options]
            min_s, max_s = (min(option_scores), max(option_scores)) if option_scores else (0, 0)
            meal_score_vars[meal] = model.NewIntVar(min_s, max_s, f'score_{meal}')
            model.AddElement(meal_vars[meal], option_scores, meal_score_vars[meal])

    # Constraint: Match meal types (sanity check)
    for (day, mtype), var in meal_vars.items():
        valid_indices = [
            i for i, (_, fmtype, _) in enumerate(meal_to_options[(day, mtype)])
            if fmtype == mtype
        ]
        if len(valid_indices) < len(meal_to_options[(day, mtype)]):
            model.AddAllowedAssignments([var], [[i] for i in valid_indices])

    # We iterate over the list of constraint objects
    for i, constraint in enumerate(constraints):
        target_foods = constraint.get("foods", [])
        limit = constraint.get("limit", None)
        gap = constraint.get("gap", None)
        
        # Skip if empty definition
        if not target_foods:
            continue

        # We need to track which meals HAVE a food from this group selected.
        # We'll create a boolean 'is_selected_var' for relevant meals.
        group_match_bools = {} # meal -> BoolVar
        
        for meal, options in meal_to_options.items():
            # Find indices of options that match ANY food in the target list
            matching_indices = []
            for idx, (food_name, _, _) in enumerate(options):
                # Check if food_name contains any of the target strings (regex or substring)
                # Using regex for flexibility (matches "Cheese Pizza" if target is "Pizza")
                if any(re.search(target, food_name) for target in target_foods):
                    matching_indices.append(idx)
            
            if matching_indices:
                # Create a boolean: Is a matching food selected for this meal?
                is_match = model.NewBoolVar(f'c{i}_match_{meal}')
                
                # Link main variable to this boolean
                # Logic: is_match == 1  <==>  meal_vars[meal] IN matching_indices
                
                # 1. Enforce True if selected index is in list
                model.AddLinearExpressionInDomain(
                    meal_vars[meal], 
                    cp_model.Domain.FromValues(matching_indices)
                ).OnlyEnforceIf(is_match)
                
                # 2. Enforce False if selected index is NOT in list (Complement)
                all_indices = set(range(len(options)))
                complement_indices = list(all_indices - set(matching_indices))
                if complement_indices:
                    model.AddLinearExpressionInDomain(
                        meal_vars[meal], 
                        cp_model.Domain.FromValues(complement_indices)
                    ).OnlyEnforceIf(is_match.Not())
                else:
                    # If all options match, bool is always true
                    model.Add(is_match == 1)
                
                group_match_bools[meal] = is_match

        # Apply LIMIT: Total occurrences <= limit
        if limit is not None and group_match_bools:
            model.Add(sum(group_match_bools.values()) <= int(limit))

        # Apply GAP: Distance between occurrences >= gap
        if gap is not None and group_match_bools:
            gap = int(gap)
            # Iterate through meals by index to check distances
            # Note: Assuming day_meals is sorted chronologically
            for j in range(len(day_meals)):
                for k in range(j + 1, len(day_meals)):
                    if k - j < gap:
                        meal_j = day_meals[j]
                        meal_k = day_meals[k]
                        
                        # If both meals define a boolean for this group, constraint them
                        if meal_j in group_match_bools and meal_k in group_match_bools:
                            # Cannot select matching foods at both j and k if they are too close
                            model.Add(group_match_bools[meal_j] + group_match_bools[meal_k] <= 1)

    # --- 3. Objective & Solving ---
    model.Maximize(sum(meal_score_vars.values()))

    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    if time_limit:
        solver.parameters.max_time_in_seconds = time_limit

    print("Solving for optimal schedule...")
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solution = {}
        total_score = 0
        print("-" * 40)
        print(f"Solution Status: {solver.StatusName(status)}")
        print("Food reservation plan:")
        
        for meal in day_meals:
            if meal in meal_vars:
                idx = solver.Value(meal_vars[meal])
                food, mtype, salon = option_to_details[(meal, idx)]
                solution[meal] = (food, mtype, salon)
                score = preferences.get(food, 0)
                total_score += score
                print(f"  {meal}: {food} ({salon}) [Score: {score}]")
                
        print("-" * 40)
        print(f"Total Score: {total_score}")
        return solution
    else:
        print("No solution found that satisfies all constraints.")
        return None
