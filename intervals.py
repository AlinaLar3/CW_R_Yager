from typing import List, Dict, Tuple

class Interval:
    """Класс для представления интервалов"""
    def __init__(self, left: float, right: float):
        if left > right:
            raise ValueError(f"Левая граница {left} не может быть больше правой {right}")
        if not (0 <= left <= right <= 1):
            raise ValueError(f"Должно быть: 0 <= x1 <= x2 <= 1, получено: {left}, {right}")
        self.left = left
        self.right = right
    
    def __repr__(self):
        return f"({self.left:.3f}, {self.right:.3f})"
    
    def __str__(self):
        return f"({self.left:.3f}, {self.right:.3f})"
    
    def midpoint(self) -> float:
        return (self.left + self.right) / 2
    
    def length(self) -> float:
        return self.right - self.left
    
    def rep(self) -> float:
        m = self.midpoint()
        r = self.length()
        return m - 0.5 * m * r
    
    @staticmethod
    def min_interval(a, b):
        return Interval(min(a.left, b.left), min(a.right, b.right))
    
    @staticmethod
    def max_interval(a, b):
        return Interval(max(a.left, b.left), max(a.right, b.right))


def interval_yager_method(alternatives: List[str], criteria_importance: Dict[str, Interval], 
                         ratings_matrix: List[List[Interval]],
                         resolve_tie: bool = False) -> Tuple[Dict[str, Tuple[Interval, float]], 
                                                            List[Tuple[str, Interval, float]], 
                                                            bool]:
    """Метод Яджера для интервалов"""
    if not alternatives or not criteria_importance or not ratings_matrix:
        return {}, [], False
    criteria_names = list(criteria_importance.keys())
    importance_intervals = list(criteria_importance.values())
    barriers = [Interval(1 - imp.right, 1 - imp.left) for imp in importance_intervals]
    barred_ratings = {}
    for i, alt in enumerate(alternatives):
        barred = [Interval.max_interval(barriers[j], ratings_matrix[i][j]) for j in range(len(criteria_names))]
        barred_ratings[alt] = barred
    final_intervals = {}
    for alt in alternatives:
        min_interval = barred_ratings[alt][0]
        for interval in barred_ratings[alt][1:]:
            min_interval = Interval.min_interval(min_interval, interval)
        final_intervals[alt] = min_interval
    rep_scores = {alt: interval.rep() for alt, interval in final_intervals.items()}
    best_rep = max(rep_scores.values())
    best_alternatives = [alt for alt, score in rep_scores.items() if abs(score - best_rep) < 1e-10]
    was_tie = len(best_alternatives) > 1
    if was_tie and resolve_tie:
        winners, final_intervals, rep_scores = _resolve_interval_tie(best_alternatives, barred_ratings, final_intervals, rep_scores)
    else:
        winners = {alt: (final_intervals[alt], rep_scores[alt]) for alt in best_alternatives}
    sorted_alternatives = sorted([(alt, final_intervals[alt], rep_scores[alt]) for alt in alternatives], key=lambda x: x[2], reverse=True)
    return winners, sorted_alternatives, was_tie

def _resolve_interval_tie(tied_alts: List[str], barred_ratings: Dict[str, List[Interval]], 
                         current_intervals: Dict[str, Interval],
                         current_reps: Dict[str, float]) -> Tuple[Dict[str, Tuple[Interval, float]], 
                                                                 Dict[str, Interval], 
                                                                 Dict[str, float]]:
    """Разрешение ничьи для интервалов"""
    current_tied = tied_alts.copy()
    excluded = {alt: [] for alt in current_tied}
    updated_intervals = current_intervals.copy()
    updated_reps = current_reps.copy()
    n_criteria = len(barred_ratings[tied_alts[0]]) if tied_alts else 0
    for iteration in range(n_criteria):
        if len(current_tied) <= 1:
            break
        all_have_criteria = True
        for alt in current_tied:
            if len(excluded[alt]) >= n_criteria - 1:
                all_have_criteria = False
                break
        if not all_have_criteria:
            break
        criteria_to_remove = {}
        for alt in current_tied:
            ratings = barred_ratings[alt]
            remaining = [(i, ratings[i]) for i in range(len(ratings)) if i not in excluded[alt]]
            if remaining:
                min_left = min(interval.left for _, interval in remaining)
                for i, interval in remaining:
                    if abs(interval.left - min_left) < 1e-10:
                        criteria_to_remove[alt] = i
                        break
        new_scores = {}
        for alt in current_tied:
            if alt in criteria_to_remove:
                excluded[alt].append(criteria_to_remove[alt])
                remaining_intervals = [barred_ratings[alt][i] for i in range(len(barred_ratings[alt])) if i not in excluded[alt]]
                if remaining_intervals:
                    min_interval = remaining_intervals[0]
                    for interval in remaining_intervals[1:]:
                        min_interval = Interval.min_interval(min_interval, interval)
                    updated_intervals[alt] = min_interval
                    updated_reps[alt] = min_interval.rep()
                    new_scores[alt] = updated_reps[alt]
        if new_scores:
            max_new = max(new_scores.values())
            current_tied = [alt for alt in current_tied if alt in new_scores and abs(new_scores[alt] - max_new) < 1e-10]
        else:
            break
    winners = {alt: (updated_intervals[alt], updated_reps[alt]) for alt in current_tied}
    return winners, updated_intervals, updated_reps
  