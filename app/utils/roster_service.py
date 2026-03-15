from datetime import datetime

from app.models import User


ROLE_ORDER = {
    'Palleggiatore': 1,
    'Opposto': 2,
    'Libero': 3,
    'Schiacciatore': 4,
    'Centrale': 5,
    'Jolly': 6,
    'Allenatore': 7,
    'Dirigente': 8,
}


def build_roster_context(now=None):
    players = User.query.all()
    ordered_players = sorted(players, key=lambda player: ROLE_ORDER.get(player.ruolo_volley, 99))

    achievements_dict = {}
    for player in ordered_players:
        achievements_dict[player.id] = [
            {
                'icon': user_achievement.achievement.icon,
                'name': user_achievement.achievement.name,
                'desc': user_achievement.achievement.description,
                'color': user_achievement.achievement.color if user_achievement.achievement.color else 'bg-warning',
                'is_monthly': user_achievement.achievement.is_monthly,
                'month': user_achievement.month,
                'year': user_achievement.year,
            }
            for user_achievement in player.achievements
        ]

    return {
        'elenco_giocatori': ordered_players,
        'achievements_dict': achievements_dict,
        'now': now or datetime.now(),
    }