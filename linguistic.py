from typing import List, Dict, Tuple

def yager_method_linguistic(alternatives: List[str],criteria_importance: Dict[str, str], 
                              ratings_matrix: List[List[str]], 
                              linguistic_scale: List[str]) -> Tuple[Dict[str, str], List[Tuple[str, str]], bool]:
    """Метод Яджера для вербальных оценок"""
    if not alternatives or not criteria_importance or not ratings_matrix or not linguistic_scale:
        return {}, [], False
    word_to_index = {word: i for i, word in enumerate(linguistic_scale)}
    n = len(linguistic_scale) - 1
    criteria_names = list(criteria_importance.keys())
    importance_words = list(criteria_importance.values())
    b_indices = [word_to_index[word] for word in importance_words]
    b_prime_indices = [n - idx for idx in b_indices]
    final_indices = {}
    all_barred_indices = {}
    for i, alt in enumerate(alternatives):
        alt_ratings = ratings_matrix[i]
        alt_indices = [word_to_index[rating] for rating in alt_ratings]
        c_indices = [max(b_prime_indices[j], alt_indices[j]) for j in range(len(criteria_names))]
        all_barred_indices[alt] = c_indices
        final_indices[alt] = min(c_indices)
    best_index = max(final_indices.values())
    best_alternatives = [alt for alt, idx in final_indices.items() if idx == best_index]
    was_tie = len(best_alternatives) > 1
    final_scores_indices = final_indices.copy()
    if was_tie:
        winners_indices, final_scores_indices = _resolve_tie_linguistic(best_alternatives, all_barred_indices, final_indices)
    else:
        winners_indices = {best_alternatives[0]: final_indices[best_alternatives[0]]}
    winners = {alt: linguistic_scale[idx] for alt, idx in winners_indices.items()}
    sorted_alternatives = sorted([(alt, linguistic_scale[idx]) for alt, idx in final_scores_indices.items()],
        key=lambda x: word_to_index[x[1]], reverse=True)
    return winners, sorted_alternatives, was_tie


def _resolve_tie_linguistic(tied_alts: List[str], 
                             barred_indices: Dict[str, List[int]], 
                             current_indices: Dict[str, int]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Разрешение ничьи для вербальных оценок"""
    current_tied = tied_alts.copy()
    excluded = {alt: [] for alt in current_tied}
    updated_indices = current_indices.copy()
    max_iterations = len(barred_indices[tied_alts[0]]) if tied_alts else 0
    for iteration in range(max_iterations):
        if len(current_tied) <= 1:
            break
        all_have_criteria = True
        for alt in current_tied:
            if len(excluded[alt]) >= len(barred_indices[alt]):
                all_have_criteria = False
                break        
        if not all_have_criteria:
            break
        min_positions = {}
        for alt in current_tied:
            indices = barred_indices[alt]
            remaining = [(i, indices[i]) for i in range(len(indices)) if i not in excluded[alt]]
            if remaining:
                min_val = min(v for _, v in remaining)
                min_positions[alt] = [i for i, v in remaining if v == min_val]
        new_indices = {}
        for alt in current_tied:
            if alt in min_positions and min_positions[alt]:
                excluded[alt].append(min_positions[alt][0])
                remaining_values = [barred_indices[alt][i] for i in range(len(barred_indices[alt])) if i not in excluded[alt]]
                if remaining_values:
                    new_indices[alt] = min(remaining_values)
                    updated_indices[alt] = new_indices[alt]
        if new_indices:
            max_new = max(new_indices.values())
            current_tied = [alt for alt in current_tied if alt in new_indices and new_indices[alt] == max_new]
        else:
            break
    winners = {alt: updated_indices[alt] for alt in current_tied}
    return winners, updated_indices
