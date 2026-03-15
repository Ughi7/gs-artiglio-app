import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import CashTransaction, Fine, User, db
from app.utils.fine_page_service import build_fine_stats_context, build_fines_page_context
from app.utils.fine_report_service import build_fine_change_details, build_fine_snapshot, log_fine_report_event
from app.utils.fine_workflow_service import (
    FineWorkflowError,
    approve_denuncia,
    cancel_denuncia_vote,
    cast_denuncia_vote,
    mark_fine_paid,
    reject_denuncia,
    start_denuncia_vote,
    submit_denuncia,
    update_vote_exclusions,
    withdraw_denuncia,
)
from app.utils.main_services import ValidationError, parse_fine_update_form, parse_new_fine_form
from app.utils.notifications import crea_notifica, get_nome_giocatore


fines_bp = Blueprint('fines', __name__)


def _redirect_to_fines():
    return redirect(url_for('fines.multe'))


@fines_bp.route('/denuncia_infrazione', methods=['POST'])
@login_required
def denuncia_infrazione():
    try:
        _, denunciato = submit_denuncia(current_user, request.form)
        flash(f'Denuncia inviata per {get_nome_giocatore(denunciato)}! In attesa di approvazione.', 'warning')
    except (ValidationError, FineWorkflowError) as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('roster.rosa'))


@fines_bp.route('/upload_regolamento', methods=['POST'])
@login_required
def upload_regolamento():
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    if 'regolamento_file' not in request.files:
        flash('Nessun file selezionato', 'danger')
        return _redirect_to_fines()

    file = request.files['regolamento_file']
    if file.filename == '':
        flash('Nessun file selezionato', 'warning')
        return _redirect_to_fines()

    if file and file.filename.lower().endswith('.pdf'):
        file.save(os.path.join(current_app.config['FILES_UPLOAD_FOLDER'], 'regolamento.pdf'))
        flash('Regolamento caricato con successo!', 'success')
    else:
        flash('Solo file PDF sono consentiti', 'danger')

    return _redirect_to_fines()


@fines_bp.route('/multe')
@login_required
def multe():
    filter_month = request.args.get('month', 'all')
    filter_person = request.args.get('person', 'all')
    context = build_fines_page_context(
        current_user,
        filter_month=filter_month,
        filter_person=filter_person,
        now=datetime.now(),
    )
    return render_template('multe.html', **context)


@fines_bp.route('/stats_multe')
@login_required
def stats_multe():
    return render_template('stats_multe.html', **build_fine_stats_context())


@fines_bp.route('/aggiungi_transazione', methods=['POST'])
@login_required
def aggiungi_transazione():
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    amount = float(request.form.get('amount'))
    description = request.form.get('description')
    transaction_type = request.form.get('transaction_type', 'uscita')
    date_str = request.form.get('date')
    trans_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.now()

    transaction = CashTransaction(
        amount=amount,
        description=description,
        date=trans_date,
        transaction_type=transaction_type,
        created_by_id=current_user.id,
    )
    db.session.add(transaction)
    db.session.commit()

    flash(f'{"Uscita" if transaction_type == "uscita" else "Entrata"} registrata: €{amount:.2f}', 'success')
    return _redirect_to_fines()


@fines_bp.route('/elimina_transazione/<int:trans_id>', methods=['POST'])
@login_required
def elimina_transazione(trans_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    transaction = db.session.get(CashTransaction, trans_id)
    if transaction:
        db.session.delete(transaction)
        db.session.commit()
        flash('Transazione eliminata.', 'success')

    return _redirect_to_fines()


@fines_bp.route('/aggiungi_multa', methods=['POST'])
@login_required
def aggiungi_multa():
    if not (current_user.is_admin or current_user.is_notaio):
        return _redirect_to_fines()

    try:
        fine_data = parse_new_fine_form(request.form)
    except ValidationError as exc:
        flash(str(exc), 'danger')
        return _redirect_to_fines()

    multato = fine_data['user']
    fine = Fine(
        user_id=multato.id,
        amount=fine_data['amount'],
        reason=fine_data['reason'],
        date=fine_data['date'],
        deadline=fine_data['deadline'],
    )
    db.session.add(fine)

    if multato:
        multato.current_streak = 0

    db.session.flush()
    log_fine_report_event(
        'add_fine',
        actor=current_user,
        fine=fine,
        target_user=multato,
        details={'after': build_fine_snapshot(fine)},
    )
    db.session.commit()

    crea_notifica(
        'multa',
        f"💸 {get_nome_giocatore(multato)} è stato multato. Motivazione: {fine_data['reason']}",
        icon='💸',
    )
    flash('Multa assegnata', 'success')
    return _redirect_to_fines()


@fines_bp.route('/modifica_multa', methods=['POST'])
@login_required
def modifica_multa():
    if not (current_user.is_admin or current_user.is_notaio):
        return _redirect_to_fines()

    try:
        fine_data = parse_fine_update_form(request.form)
    except ValidationError as exc:
        flash(str(exc), 'danger')
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_data['fine_id'])
    if not fine:
        flash('Multa non trovata.', 'danger')
        return _redirect_to_fines()

    target_user = db.session.get(User, fine.user_id)
    before_snapshot = build_fine_snapshot(fine)
    fine.amount = fine_data['amount']
    fine.reason = fine_data['reason']
    fine.paid = fine_data['paid']
    fine.payment_method = fine_data['payment_method']

    after_snapshot = build_fine_snapshot(fine)
    log_fine_report_event(
        'modify_fine',
        actor=current_user,
        fine=fine,
        target_user=target_user,
        details={
            'before': before_snapshot,
            'after': after_snapshot,
            'changes': build_fine_change_details(before_snapshot, after_snapshot),
        },
    )
    db.session.commit()
    flash('Multa aggiornata.', 'success')
    return _redirect_to_fines()


@fines_bp.route('/paga_multa/<int:fine_id>', methods=['POST'])
@login_required
def paga_multa(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non autorizzato', 'danger')
        return _redirect_to_fines()

    fine = db.get_or_404(Fine, fine_id)
    try:
        metodo = mark_fine_paid(fine, current_user, request.form.get('metodo'))
    except (ValidationError, FineWorkflowError) as exc:
        flash(str(exc), 'danger')
        return _redirect_to_fines()

    flash(f'Multa segnata come pagata ({metodo})', 'success')
    return _redirect_to_fines()


@fines_bp.route('/elimina_multa/<int:fine_id>')
@login_required
def elimina_multa(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_id)
    if fine:
        target_user = db.session.get(User, fine.user_id)
        log_fine_report_event(
            'delete_fine',
            actor=current_user,
            fine_id=fine.id,
            target_user=target_user,
            details={'before': build_fine_snapshot(fine)},
        )
        db.session.delete(fine)
        db.session.commit()

    return _redirect_to_fines()


@fines_bp.route('/approva_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def approva_denuncia(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_id)
    try:
        approve_denuncia(fine, current_user)
        flash('Denuncia approvata!', 'success')
    except FineWorkflowError as exc:
        flash(str(exc), 'warning')

    return _redirect_to_fines()


@fines_bp.route('/rifiuta_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def rifiuta_denuncia(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_id)
    try:
        reject_denuncia(fine, current_user)
        flash('Denuncia rifiutata e rimossa.', 'info')
    except FineWorkflowError as exc:
        flash(str(exc), 'warning')

    return _redirect_to_fines()


@fines_bp.route('/ritira_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def ritira_denuncia(fine_id):
    fine = db.session.get(Fine, fine_id)
    try:
        withdraw_denuncia(fine, current_user, request.form.get('note_ritiro', ''))
        flash('Denuncia ritirata con successo.', 'success')
    except FineWorkflowError as exc:
        flash(str(exc), 'danger')
    return _redirect_to_fines()


@fines_bp.route('/avvia_votazione/<int:fine_id>', methods=['POST'])
@login_required
def avvia_votazione(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_id)
    try:
        start_denuncia_vote(fine, current_user, now=datetime.now())
        flash('Votazione avviata! Scadrà tra 24 ore.', 'success')
    except FineWorkflowError as exc:
        flash(str(exc), 'warning')
    return _redirect_to_fines()


@fines_bp.route('/vota_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def vota_denuncia(fine_id):
    fine = db.session.get(Fine, fine_id)
    try:
        message, category = cast_denuncia_vote(fine, current_user, request.form.get('vote'), now=datetime.now())
        flash(message, category)
    except FineWorkflowError as exc:
        flash(str(exc), 'warning')

    return _redirect_to_fines()


@fines_bp.route('/modifica_impostazioni_votazione/<int:fine_id>', methods=['POST'])
@login_required
def modifica_impostazioni_votazione(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_id)
    try:
        excluded_count = update_vote_exclusions(fine, request.form.getlist('excluded_users'))
        flash(f'Impostazioni votazione aggiornate! {excluded_count} utenti esclusi.', 'success')
    except FineWorkflowError as exc:
        flash(str(exc), 'warning')
    return _redirect_to_fines()


@fines_bp.route('/elimina_votazione/<int:fine_id>', methods=['POST'])
@login_required
def elimina_votazione(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_fines()

    fine = db.session.get(Fine, fine_id)
    try:
        cancel_denuncia_vote(fine)
        flash('Votazione annullata. La denuncia è tornata in attesa di approvazione.', 'info')
    except FineWorkflowError as exc:
        flash(str(exc), 'warning')
    return _redirect_to_fines()