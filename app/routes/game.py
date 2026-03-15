import json
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None # Fallback per Python vecchi
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import db, User, FlappyGameProfile, FlappyMonthlyScore, Notification
from app.utils.json_services import JsonValidationError, parse_non_negative_int, parse_optional_text, require_json_object
from app.utils.notifications import crea_notifica, get_nome_giocatore

game_bp = Blueprint('game', __name__)


def _update_monthly_score(score, achieved_at=None):
    achieved_at = achieved_at or datetime.now()
    monthly_score = FlappyMonthlyScore.query.filter_by(
        user_id=current_user.id,
        month=achieved_at.month,
        year=achieved_at.year,
    ).first()

    monthly_improved = False
    if monthly_score:
        if score > monthly_score.score:
            monthly_score.score = score
            monthly_score.date_achieved = achieved_at
            monthly_improved = True
    else:
        monthly_score = FlappyMonthlyScore(
            user_id=current_user.id,
            score=score,
            month=achieved_at.month,
            year=achieved_at.year,
        )
        db.session.add(monthly_score)
        monthly_improved = True

    return monthly_improved, achieved_at


def _notify_monthly_top_three(score, achieved_at):
    top3_mensile = FlappyMonthlyScore.query.filter(
        FlappyMonthlyScore.month == achieved_at.month,
        FlappyMonthlyScore.year == achieved_at.year,
    ).order_by(FlappyMonthlyScore.score.desc()).limit(3).all()

    for i, monthly_score in enumerate(top3_mensile):
        if monthly_score.user_id == current_user.id:
            pos = i + 1
            pos_str = {1: '🥇 PRIMO', 2: '🥈 SECONDO', 3: '🥉 TERZO'}[pos]
            mese_nome = achieved_at.strftime('%B %Y')
            existing = Notification.query.filter(
                Notification.tipo == 'floppy_top3_mensile',
                Notification.messaggio.contains(get_nome_giocatore(current_user)),
                Notification.messaggio.contains(mese_nome)
            ).first()
            if not existing:
                crea_notifica('floppy_top3_mensile', f"🎮 {get_nome_giocatore(current_user)} è {pos_str} in Floppy Eagle di {mese_nome} con {score} punti!", icon='🎮')
            break

@game_bp.route('/game')
@login_required
def game():
    leaderboard = User.query.filter(User.flappy_high_score > 0).order_by(User.flappy_high_score.desc()).limit(20).all()

    # Classifica mensile con filtro
    now = datetime.now()
    filter_month = request.args.get('month', f'{now.year}-{now.month:02d}')
    
    try:
        anno, mese = map(int, filter_month.split('-'))
    except:
        anno, mese = now.year, now.month
    
    monthly_scores = db.session.query(
        User, FlappyMonthlyScore.score
    ).join(
        FlappyMonthlyScore, User.id == FlappyMonthlyScore.user_id
    ).filter(
        FlappyMonthlyScore.month == mese,
        FlappyMonthlyScore.year == anno
    ).order_by(
        FlappyMonthlyScore.score.desc()
    ).limit(20).all()
    
    leaderboard_mese = [(user, score) for user, score in monthly_scores]
    
    available_months = db.session.query(
        FlappyMonthlyScore.year, FlappyMonthlyScore.month
    ).distinct().order_by(FlappyMonthlyScore.year.desc(), FlappyMonthlyScore.month.desc()).all()
    
    months_list = [f'{y}-{m:02d}' for y, m in available_months]

    return render_template('game.html', 
                         leaderboard=leaderboard, 
                         leaderboard_mese=leaderboard_mese, 
                         mese=mese, 
                         anno=anno,
                         filter_month=filter_month,
                         available_months=months_list)


@game_bp.route('/api/game/leaderboard/monthly', methods=['GET'])
@login_required
def get_monthly_leaderboard():
    filter_month = request.args.get('month')
    if not filter_month:
        return jsonify({'error': 'Missing month parameter'}), 400
        
    try:
        anno, mese = map(int, filter_month.split('-'))
    except ValueError:
        return jsonify({'error': 'Invalid month format, expected YYYY-MM'}), 400
        
    monthly_scores = db.session.query(
        User, FlappyMonthlyScore.score
    ).join(
        FlappyMonthlyScore, User.id == FlappyMonthlyScore.user_id
    ).filter(
        FlappyMonthlyScore.month == mese,
        FlappyMonthlyScore.year == anno
    ).order_by(
        FlappyMonthlyScore.score.desc()
    ).limit(20).all()
    
    results = []
    for user, score in monthly_scores:
        is_current_user = (current_user.id == user.id)
        results.append({
            'name': get_nome_giocatore(user),
            'score': score,
            'is_current_user': is_current_user
        })
        
    return jsonify({'results': results})

@game_bp.route('/api/flappy/sync', methods=['GET', 'POST'])
@login_required
def flappy_sync():
    profile = FlappyGameProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = FlappyGameProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()
        
    unlocked_skins = json.loads(profile.unlocked_skins)
    
    # Migrazione Dragon -> Bee (vedi app.py per logica)
    if not current_user.is_admin and 'dragon' in unlocked_skins:
        missions = profile.missions_completed_count or 0
        if missions < 200:
            unlocked_skins.remove('dragon')
            if 'bee' not in unlocked_skins:
                unlocked_skins.append('bee')
            profile.unlocked_skins = json.dumps(unlocked_skins)
            if profile.selected_skin == 'dragon':
                profile.selected_skin = 'bee'
            db.session.commit()
    
    if current_user.is_admin:
        all_skins = ["default", "duck", "pigeon", "parrot", "owl", "rooster", "dodo", "phoenix", "dragon", "flamingo", "peacock", "penguin", "turkey", "bat", "swan", "goose", "raven", "dove", "unicorn", "bee", "hen", "chick", "butterfly", "canary", "hatchling", "goat", "ladybug"]
        unlocked_skins = all_skins
    
    if request.method == 'POST':
        try:
            data = require_json_object(request.get_json(silent=True), 'Payload skin non valido.')
        except JsonValidationError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

        selected_skin = parse_optional_text(data.get('selected_skin'), 'Skin selezionata', max_length=50)
        if selected_skin and selected_skin in unlocked_skins:
            profile.selected_skin = selected_skin
            db.session.commit()

    morning_dates_count = len(json.loads(profile.morning_play_dates or '[]'))
    night_dates_count = len(json.loads(profile.night_play_dates or '[]'))
    
    return {
        'skins': unlocked_skins,
        'selected_skin': profile.selected_skin,
        'missions_count': profile.missions_completed_count,
        'coins': profile.coins or 0,
        'streak': profile.current_game_streak,
        'total_games': profile.total_games_played,
        'games_over_2000': profile.games_over_2000 or 0,
        'morning_plays': morning_dates_count,
        'night_plays': night_dates_count,
        'high_score': current_user.flappy_high_score
    }

@game_bp.route('/api/flappy/save_progress', methods=['POST'])
@login_required
def flappy_save_progress():
    profile = FlappyGameProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = FlappyGameProfile(user_id=current_user.id)
        db.session.add(profile)
    
    profile.total_games_played = (profile.total_games_played or 0) + 1
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload progresso non valido.')
        score = parse_non_negative_int(data.get('score'), 'Score')
        level = parse_non_negative_int(data.get('level', 1), 'Livello', default=1)
        coins_collected = parse_non_negative_int(data.get('coins', 0), 'Monete', default=0)
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    if score >= 2000:
        profile.games_over_2000 = (profile.games_over_2000 or 0) + 1
    
    if ZoneInfo:
        now = datetime.now(ZoneInfo('Europe/Rome'))
    else:
        now = datetime.now()
    hour = now.hour
    today = now.date().isoformat()
    
    # Night: 1AM - 5AM
    if 1 <= hour < 5:
        profile.night_plays = (profile.night_plays or 0) + 1
        try:
            night_dates = json.loads(profile.night_play_dates or '[]')
            if today not in night_dates:
                night_dates.append(today)
                profile.night_play_dates = json.dumps(night_dates)
        except (json.JSONDecodeError, TypeError):
            profile.night_play_dates = json.dumps([today])
        
    # Morning: 5AM - 7AM
    if 5 <= hour < 7:
        profile.morning_plays = (profile.morning_plays or 0) + 1
        try:
            morning_dates = json.loads(profile.morning_play_dates or '[]')
            if today not in morning_dates:
                morning_dates.append(today)
                profile.morning_play_dates = json.dumps(morning_dates)
        except (json.JSONDecodeError, TypeError):
            profile.morning_play_dates = json.dumps([today])

    unlocked = []
    try:
        unlocked = json.loads(profile.unlocked_skins or '["default"]')
    except (json.JSONDecodeError, TypeError):
        unlocked = ['default']
        profile.unlocked_skins = json.dumps(unlocked)
    
    new_unlock = False
    unlocked_skins_list = []
    
    def unlock_skin(code, name, icon_emoji):
        nonlocal new_unlock
        if code not in unlocked:
            unlocked.append(code)
            new_unlock = True
            unlocked_skins_list.append({'name': name, 'icon': icon_emoji})
            player_name = get_nome_giocatore(current_user)
            try:
                crea_notifica('skin_unlock', f'🦅 {player_name} ha sbloccato la skin {name}!', icon=icon_emoji, send_push=True, commit=False)
            except Exception as e:
                import traceback
                current_app.logger.error(f'Errore notifica skin unlock: {e}\n{traceback.format_exc()}')

    # Check Milestones
    if (profile.games_over_2000 or 0) >= 15: unlock_skin('duck', 'PAPERA', '🦆')
    if (profile.games_over_2000 or 0) >= 50: unlock_skin('pigeon', 'PICCIONE', '🐦')
    if (profile.games_over_2000 or 0) >= 100: unlock_skin('chick', 'PULCINO', '🐤')
    
    try:
        if len(json.loads(profile.morning_play_dates or '[]')) >= 10: unlock_skin('hen', 'GALLINA', '🐔')
    except (json.JSONDecodeError, TypeError):
        pass
    
    try:
        if len(json.loads(profile.night_play_dates or '[]')) >= 10: unlock_skin('bat', 'PIPISTRELLO', '🦇')
    except (json.JSONDecodeError, TypeError):
        pass
    
    if (profile.games_over_2000 or 0) >= 200: unlock_skin('swan', 'CIGNO', '🦢')
    if (profile.games_over_2000 or 0) >= 500: unlock_skin('goose', 'OCA', '🪿')
    if (profile.games_over_2000 or 0) >= 1000: unlock_skin('hatchling', 'PULCINO NASCENTE', '🐣')
    if (current_user.flappy_high_score >= 7500 or score >= 7500): unlock_skin('parrot', 'PAPPAGALLO', '🦜')
    
    try:
        if len(json.loads(profile.night_play_dates or '[]')) >= 3: unlock_skin('owl', 'GUFO', '🦉')
    except (json.JSONDecodeError, TypeError):
        pass
    
    try:
        if len(json.loads(profile.morning_play_dates or '[]')) >= 3: unlock_skin('rooster', 'GALLO', '🐓')
    except (json.JSONDecodeError, TypeError):
        pass
    
    if level >= 10: unlock_skin('phoenix', 'FENICE', '🐦‍🔥')

    if new_unlock:
        profile.unlocked_skins = json.dumps(unlocked)
    
    # Check High Score & Top 3 General
    old_high_score = current_user.flappy_high_score or 0
    if score > old_high_score:
        db_user = db.session.get(User, current_user.id)
        if db_user:
            db_user.flappy_high_score = score
        else:
            current_user.flappy_high_score = score
        try:
            top_players = User.query.filter(User.flappy_high_score > 0).order_by(User.flappy_high_score.desc()).limit(3).all()
            for idx, player in enumerate(top_players):
                if player.id == current_user.id:
                    position = idx + 1
                    emoji = '🥇' if position == 1 else ('🥈' if position == 2 else '🥉')
                    position_text = 'PRIMO' if position == 1 else ('SECONDO' if position == 2 else 'TERZO')
                    crea_notifica('flappy_leaderboard', f'{emoji} {get_nome_giocatore(current_user)} ha raggiunto il {position_text} posto in Floppy Eagle con {score} punti!', icon=emoji, commit=False)
                    break
        except Exception as e:
            import traceback
            current_app.logger.error(f'Errore leaderboard notification: {e}\n{traceback.format_exc()}')

    monthly_improved, achieved_at = _update_monthly_score(score, now)

    if coins_collected > 0:
        profile.coins = (profile.coins or 0) + coins_collected
    
    # Single commit at the end to ensure transactional integrity
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import traceback
        current_app.logger.error(f'Errore salvataggio progresso flappy: {e}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'error': 'Errore nel salvataggio - riprovare'}), 500

    if monthly_improved:
        try:
            _notify_monthly_top_three(score, achieved_at)
        except Exception as e:
            import traceback
            current_app.logger.error(f'Errore monthly notification: {e}\n{traceback.format_exc()}')

    first_skin = unlocked_skins_list[0] if unlocked_skins_list else None
    return {
        'success': True, 
        'new_unlock': new_unlock,
        'unlocked_skin_name': first_skin['name'] if first_skin else None,
        'unlocked_skin_icon': first_skin['icon'] if first_skin else None,
        'high_score': current_user.flappy_high_score or 0,
        'total_coins': profile.coins or 0,
    }

@game_bp.route('/api/save_score', methods=['POST'])
@login_required
def save_score():
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload punteggio non valido.')
        score = parse_non_negative_int(data.get('score'), 'Score')
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    old_high_score = current_user.flappy_high_score or 0
    new_record = score > old_high_score
    
    # (High score is also handled in save_progress for redundancy, but keeping this route just in case)
    if new_record:
        db_user = db.session.get(User, current_user.id)
        if db_user:
            db_user.flappy_high_score = score
        else:
            current_user.flappy_high_score = score

    # Monthly score logic
    now = datetime.now()
    monthly_improved, achieved_at = _update_monthly_score(score, now)
    
    db.session.commit()

    # Top 3 Mensile Notifica
    if monthly_improved:
        _notify_monthly_top_three(score, achieved_at)

    return {'new_record': new_record, 'high_score': current_user.flappy_high_score}

@game_bp.route('/api/flappy/complete_mission', methods=['POST'])
@login_required
def flappy_complete_mission():
    profile = FlappyGameProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = FlappyGameProfile(user_id=current_user.id)
        db.session.add(profile)
    
    try:
        require_json_object(request.get_json(silent=True), 'Payload missione non valido.')
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    profile.missions_completed_count = (profile.missions_completed_count or 0) + 1
    
    try:
        unlocked = json.loads(profile.unlocked_skins or '["default"]')
    except (json.JSONDecodeError, TypeError):
        unlocked = ['default']
        profile.unlocked_skins = json.dumps(unlocked)
    
    new_unlock = False
    unlocked_skin_name = None
    unlocked_skin_icon = None
    
    def check_mission_unlock(req, code, name, icon):
        nonlocal new_unlock, unlocked_skin_name, unlocked_skin_icon, unlocked
        if profile.missions_completed_count >= req and code not in unlocked:
            unlocked.append(code)
            profile.unlocked_skins = json.dumps(unlocked)
            new_unlock = True
            unlocked_skin_name = name
            unlocked_skin_icon = icon
            try:
                crea_notifica('skin_unlock', f'🦅 {get_nome_giocatore(current_user)} ha sbloccato la skin {name}!', icon=icon, send_push=True, commit=False)
            except Exception as e:
                import traceback
                current_app.logger.error(f'Errore notifica mission unlock: {e}\n{traceback.format_exc()}')

    check_mission_unlock(30, 'dodo', 'DODO', '🦤')
    check_mission_unlock(100, 'bee', 'APE', '🐝')
    check_mission_unlock(200, 'dragon', 'DRAGO', '🐉')
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import traceback
        current_app.logger.error(f'Errore salvataggio missione: {e}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'error': 'Errore nel salvataggio - riprovare'}), 500
    
    return {
        'success': True, 'new_unlock': new_unlock, 
        'total_missions': profile.missions_completed_count,
        'unlocked_skin_name': unlocked_skin_name, 'unlocked_skin_icon': unlocked_skin_icon
    }

@game_bp.route('/api/flappy/save_coins', methods=['POST'])
@login_required
def flappy_save_coins():
    profile = FlappyGameProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = FlappyGameProfile(user_id=current_user.id)
        db.session.add(profile)
    
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload monete non valido.')
        coins_collected = parse_non_negative_int(data.get('coins'), 'Monete')
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    if coins_collected > 0:
        profile.coins = (profile.coins or 0) + coins_collected
        db.session.commit()
    
    return {'success': True, 'total_coins': profile.coins or 0}

@game_bp.route('/api/flappy/shop/buy', methods=['POST'])
@login_required
def flappy_shop_buy():
    profile = FlappyGameProfile.query.filter_by(user_id=current_user.id).first()
    if not profile: return {'success': False, 'error': 'Profilo non trovato'}, 400
    
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload shop non valido.')
        item_id = parse_optional_text(data.get('item_id'), 'Item', max_length=50)
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    SHOP_ITEMS = {
        'flamingo': {'price': 150, 'type': 'skin', 'name': 'Fenicottero', 'icon': '🦩'},
        'peacock': {'price': 250, 'type': 'skin', 'name': 'Pavone', 'icon': '🦚'},
        'penguin': {'price': 500, 'type': 'skin', 'name': 'Pinguino', 'icon': '🐧'},
        'turkey': {'price': 50, 'type': 'skin', 'name': 'Tacchino', 'icon': '🦃'},
        'canary': {'price': 750, 'type': 'skin', 'name': 'Canarino', 'icon': '🐥'},
        'butterfly': {'price': 1000, 'type': 'skin', 'name': 'Farfalla', 'icon': '🦋'},
        'unicorn': {'price': 5000, 'type': 'skin', 'name': 'Unicorno', 'icon': '🦄'},
    }
    
    if item_id not in SHOP_ITEMS: return {'success': False, 'error': 'Item non valido'}, 400
    
    item = SHOP_ITEMS[item_id]
    user_coins = profile.coins or 0
    
    if user_coins < item['price']: return {'success': False, 'error': 'Monete insufficienti'}, 400
    
    try:
        unlocked = json.loads(profile.unlocked_skins or '["default"]')
    except (json.JSONDecodeError, TypeError):
        unlocked = ['default']
        profile.unlocked_skins = json.dumps(unlocked)
    
    if item_id in unlocked: return {'success': False, 'error': 'Già acquistato'}, 400
    
    profile.coins = user_coins - item['price']
    unlocked.append(item_id)
    profile.unlocked_skins = json.dumps(unlocked)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import traceback
        current_app.logger.error(f'Errore acquisto negozio: {e}\n{traceback.format_exc()}')
        return jsonify({'success': False, 'error': 'Errore nel salvataggio - riprovare'}), 500
    
    try:
        crea_notifica('skin_unlock', f'🛒 {get_nome_giocatore(current_user)} ha acquistato la skin {item["name"]}!', icon=item['icon'], send_push=True)
    except Exception as e:
        import traceback
        current_app.logger.error(f'Errore notifica acquisto: {e}\n{traceback.format_exc()}')
    
    return {
        'success': True,
        'purchased': item_id,
        'remaining_coins': profile.coins,
        'item_name': item['name'],
        'item_icon': item['icon']
    }
