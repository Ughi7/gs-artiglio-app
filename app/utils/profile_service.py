from datetime import datetime

from sqlalchemy import func

from app.models import Event, Fine, MatchStats, db


def calculate_completed_streaks(user, now=None):
    now = now or datetime.now()
    start_of_year = datetime(now.year, 1, 1)
    fines = Fine.query.filter(
        Fine.user_id == user.id,
        Fine.date >= start_of_year,
    ).order_by(Fine.date.asc()).all()

    if not fines:
        total_days = (now - start_of_year).days
        return {
            'settimanali': total_days // 7,
            'mensili': total_days // 30,
        }

    weekly_streaks = 0
    monthly_streaks = 0

    first_fine = fines[0].date
    days_before_first_fine = (first_fine - start_of_year).days
    weekly_streaks += days_before_first_fine // 7
    monthly_streaks += days_before_first_fine // 30

    for index in range(len(fines) - 1):
        gap_days = (fines[index + 1].date - fines[index].date).days
        weekly_streaks += gap_days // 7
        monthly_streaks += gap_days // 30

    last_fine = fines[-1].date
    days_after_last_fine = (now - last_fine).days
    weekly_streaks += days_after_last_fine // 7
    monthly_streaks += days_after_last_fine // 30

    return {
        'settimanali': weekly_streaks,
        'mensili': monthly_streaks,
    }


def get_user_profile_summary(user):
    totals = db.session.query(
        func.coalesce(func.sum(MatchStats.points), 0),
        func.coalesce(func.sum(MatchStats.aces), 0),
        func.coalesce(func.sum(MatchStats.blocks), 0),
    ).join(Event).filter(
        MatchStats.user_id == user.id,
        Event.is_friendly == False,
    ).one()

    achievements_list = [
        {
            'icon': user_achievement.achievement.icon,
            'name': user_achievement.achievement.name,
            'desc': user_achievement.achievement.description,
            'color': user_achievement.achievement.color if user_achievement.achievement.color else 'bg-warning',
            'is_monthly': user_achievement.achievement.is_monthly,
            'month': user_achievement.month,
            'year': user_achievement.year,
        }
        for user_achievement in user.achievements
    ]

    return {
        'mvp_count': Event.query.filter(
            Event.mvp_id == user.id,
            Event.is_friendly == False,
        ).count(),
        'total_points': totals[0],
        'total_aces': totals[1],
        'total_blocks': totals[2],
        'total_multe_count': Fine.query.filter_by(user_id=user.id).count(),
        'denunce_fatte': Fine.query.filter_by(denunciante_id=user.id).count(),
        'denunce_prese': Fine.query.filter(Fine.user_id == user.id, Fine.denunciante_id != None).count(),
        'achievements_list': achievements_list,
    }


def build_profile_context(user, viewing_other=False, now=None):
    profile_summary = get_user_profile_summary(user)
    streak_completate = calculate_completed_streaks(user, now=now)

    return {
        'user': user,
        'mvp_count': profile_summary['mvp_count'],
        'total_points': profile_summary['total_points'],
        'total_aces': profile_summary['total_aces'],
        'total_blocks': profile_summary['total_blocks'],
        'total_multe_count': profile_summary['total_multe_count'],
        'denunce_fatte': profile_summary['denunce_fatte'],
        'denunce_prese': profile_summary['denunce_prese'],
        'viewing_other': viewing_other,
        'achievements_list': profile_summary['achievements_list'],
        'streak_completate': streak_completate,
    }