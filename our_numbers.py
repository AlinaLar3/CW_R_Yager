from typing import List, Dict, Tuple

def yager_method(alternatives: List[str], 
                 criteria_importance: Dict[str, float], 
                 ratings_matrix: List[List[float]]) -> Tuple[Dict[str, float], List[Tuple[str, float]], bool]:
    """Метод Яджера для числовых значений"""
    if not alternatives or not criteria_importance or not ratings_matrix:
        return {}, [], False    
    criteria_names = list(criteria_importance.keys())
    importance_values = list(criteria_importance.values())
    barriers = [1 - imp for imp in importance_values]
    barred_ratings = {}
    for i, alt in enumerate(alternatives):
        barred = [max(barriers[j], ratings_matrix[i][j]) for j in range(len(criteria_names))]
        barred_ratings[alt] = barred
    final_scores = {alt: min(barred_ratings[alt]) for alt in alternatives}
    best_score = max(final_scores.values())
    best_alternatives = [alt for alt, score in final_scores.items() if abs(score - best_score) < 1e-10]
    was_tie = len(best_alternatives) > 1
    if len(best_alternatives) > 1:
        winners, final_scores = _resolve_tie(best_alternatives, barred_ratings, final_scores)
    else:
        winners = {best_alternatives[0]: final_scores[best_alternatives[0]]}
    sorted_alternatives = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    return winners, sorted_alternatives, was_tie

def _resolve_tie(tied_alts: List[str], 
                 barred_ratings: Dict[str, List[float]], 
                 current_scores: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Разрешение ничьи для числовых"""
    current_tied = tied_alts.copy()
    excluded = {alt: [] for alt in current_tied}
    updated_scores = current_scores.copy()
    max_iterations = len(barred_ratings[tied_alts[0]]) if tied_alts else 0
    for iteration in range(max_iterations):
        if len(current_tied) <= 1:
            break
        all_have_criteria = True
        for alt in current_tied:
            if len(excluded[alt]) >= len(barred_ratings[alt]):
                all_have_criteria = False
                break        
        if not all_have_criteria:
            break
        min_positions = {}
        for alt in current_tied:
            ratings = barred_ratings[alt]
            remaining = [(i, ratings[i]) for i in range(len(ratings)) if i not in excluded[alt]]
            if remaining:
                min_val = min(v for _, v in remaining)
                min_positions[alt] = [i for i, v in remaining if abs(v - min_val) < 1e-10]
        new_scores = {}
        for alt in current_tied:
            if alt in min_positions and min_positions[alt]:
                excluded[alt].append(min_positions[alt][0])
                remaining_values = [barred_ratings[alt][i] for i in range(len(barred_ratings[alt])) 
                                  if i not in excluded[alt]]
                if remaining_values:
                    new_scores[alt] = min(remaining_values)
                    updated_scores[alt] = new_scores[alt]
                else:
                    new_scores[alt] = updated_scores[alt]
        if new_scores:
            max_new = max(new_scores.values())
            current_tied = [alt for alt in current_tied 
                           if alt in new_scores and abs(new_scores[alt] - max_new) < 1e-10]
        else:
            break
    winners = {alt: updated_scores[alt] for alt in current_tied}
    return winners, updated_scores