from collections import defaultdict

from app.models import Event


def build_match_stats_context():
    matches = Event.query.filter(
        Event.sets_us + Event.sets_them > 0,
        Event.is_friendly == False,
    ).order_by(Event.date_start).all()

    wins_over_time = []
    losses_over_time = []
    match_dates = []
    sets_per_month = defaultdict(lambda: {'vinti': 0, 'persi': 0})

    for match in matches:
        match_dates.append(match.date_start.strftime('%d/%m/%y'))
        if match.sets_us > match.sets_them:
            wins_over_time.append(1)
            losses_over_time.append(0)
        else:
            wins_over_time.append(0)
            losses_over_time.append(1)

        month_key = match.date_start.strftime('%Y-%m')
        sets_per_month[month_key]['vinti'] += match.sets_us
        sets_per_month[month_key]['persi'] += match.sets_them

    sorted_months = sorted(sets_per_month.keys())
    total_wins = sum(1 for match in matches if match.sets_us > match.sets_them)
    total_losses = len(matches) - total_wins

    return {
        'date_partite': match_dates,
        'vittorie_tempo': wins_over_time,
        'sconfitte_tempo': losses_over_time,
        'mesi_partite': sorted_months,
        'set_vinti_per_mese': [sets_per_month[month]['vinti'] for month in sorted_months],
        'set_persi_per_mese': [sets_per_month[month]['persi'] for month in sorted_months],
        'vittorie_totali': total_wins,
        'sconfitte_totali': total_losses,
    }