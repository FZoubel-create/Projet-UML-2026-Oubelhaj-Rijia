from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import Formation, EtatFormation, Etablissement, db, RoleUtilisateur, Inscription, EtatInscription, ActionLog
from datetime import datetime
from app.utils.notifications import send_notification

formations_bp = Blueprint('formations', __name__, url_prefix='/formations')

# --- Middleware de vérification des droits ---
def check_permission(formation=None, etab_id=None):
    """
    Vérifie si l'utilisateur courant a le droit d'agir sur la ressource.
    Règles Strictes UML:
    - SuperAdmin : Tout
    - Admin Etab : Uniquement sur SON établissement
    - Coordinateur : Uniquement sur SES formations assignées
    """
    if current_user.role == RoleUtilisateur.SUPER_ADMIN:
        return True
        
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        # Si on vérifie une formation, elle doit appartenir à son étab
        if formation and formation.etablissement_id != current_user.etablissement_id:
            abort(403)
        # Si on vérifie un étab cible (création)
        if etab_id and etab_id != current_user.etablissement_id:
            abort(403)
        return True
        
    if current_user.role == RoleUtilisateur.COORDINATEUR:
        # Coordinateur ne peut agir que sur ses formations
        if formation and formation not in current_user.formations_coordonnees:
            abort(403)
        # Coordinateur ne peut JAMAIS créer de formation
        if not formation: 
            abort(403)
        return True
        
    # Candidat
    abort(403)

@formations_bp.route('/manage')
@login_required
def manage():
    # Application de la règle de visibilité "Mes Formations"
    query = Formation.query
    
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        query = query.filter_by(etablissement_id=current_user.etablissement_id)
    elif current_user.role == RoleUtilisateur.COORDINATEUR:
        # Join pour filtrer par la table d'association
        # Note: SQLAlchemy peut le faire via la relation, mais ici on filtre la query principale
        # Plus simple : on passe par la liste python si pas trop chargé, ou on fait un join propre
        return render_template('formations/manage.html', formations=current_user.formations_coordonnees)
    elif current_user.role == RoleUtilisateur.SUPER_ADMIN:
        pass # Tout voir
    else:
        abort(403)

    formations = query.all()
    return render_template('formations/manage.html', formations=formations)

@formations_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    # Règle UML: Admin Etab crée, pas Coordinateur
    if current_user.role not in [RoleUtilisateur.SUPER_ADMIN, RoleUtilisateur.ADMIN_ETABLISSEMENT]:
        abort(403)
    if request.method == 'POST':
        titre = request.form.get('titre')
        description = request.form.get('description')
        etablissement_id = request.form.get('etablissement_id')
        
        # Validation sommaire
        if not titre or not etablissement_id:
            flash('Titre et Établissement requis.', 'danger')
            return redirect(url_for('formations.create'))

        new_formation = Formation(
            titre=titre,
            description=description,
            etablissement_id=int(etablissement_id),
            etat=EtatFormation.BROUILLON
        )
        # Gestion des dates (Optionnel à la création)
        date_ouv = request.form.get('date_ouverture')
        date_ferm = request.form.get('date_fermeture')
        if date_ouv and date_ferm:
            try:
                new_formation.date_ouverture = datetime.strptime(date_ouv, '%Y-%m-%d')
                new_formation.date_fermeture = datetime.strptime(date_ferm, '%Y-%m-%d')
            except ValueError:
                pass # Ignorer si mal formé

        # Vérif permission sur l'étab cible
        # Vérif permission sur l'étab cible
        check_permission(etab_id=new_formation.etablissement_id)
        
        db.session.add(new_formation)
        db.session.commit()
        flash('Formation créée en brouillon.', 'success')
        return redirect(url_for('formations.manage'))

    # Pour le formulaire
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        # Ne voit que son étab
        etablissements = Etablissement.query.filter_by(id=current_user.etablissement_id).all()
    else:
        etablissements = Etablissement.query.all()
        
    return render_template('formations/edit.html', etablissements=etablissements)

@formations_bp.route('/<int:id>/publish', methods=['POST'])
@login_required
def publish(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    
    # Règle : Seul Admin Etab (ou Super) publie. Le coord peut juste ouvrir/fermer ?
    # UML: "Admin Etab gère les formations (création/modification/publication)"
    if current_user.role == RoleUtilisateur.COORDINATEUR:
        abort(403) # Strict Access Control
    formation.etat = EtatFormation.PUBLIEE
    
    # Log
    log = ActionLog(user_id=current_user.id, action="PUBLICATION_FORMATION", target_type="Formation", target_id=formation.id)
    db.session.add(log)
    
    db.session.commit()
    flash(f'Formation "{formation.titre}" publiée.', 'success')
    return redirect(url_for('formations.manage'))

@formations_bp.route('/<int:id>/open-inscriptions', methods=['POST'])
@login_required
def open_inscriptions(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    # Coordinateur OK pour ça (UML: "Le Coordinateur peut ouvrir et fermer...")
    
    from app.utils.notifications import send_notification
    
    date_deb_str = request.form.get('date_ouverture')
    date_fin_str = request.form.get('date_fermeture')
    
    if formation.etat != EtatFormation.PUBLIEE:
        flash('La formation doit être publiée pour ouvrir les inscriptions.', 'warning')
        return redirect(url_for('formations.manage'))

    try:
        formation.date_ouverture = datetime.strptime(date_deb_str, '%Y-%m-%d')
        formation.date_fermeture = datetime.strptime(date_fin_str, '%Y-%m-%d')
        
        # Log
        log = ActionLog(user_id=current_user.id, action="OUVERTURE_INSCRIPTIONS", target_type="Formation", target_id=formation.id, details=f"{date_deb_str} > {date_fin_str}")
        db.session.add(log)
        
        db.session.commit()
        flash('Inscriptions ouvertes avec succès.', 'success')
        
        # Notification System (Simulation)
        # Notifier les admins ? ou juste log
        print(f"Formation {formation.titre} ouverte aux inscriptions du {date_deb_str} au {date_fin_str}.")
    except ValueError:
        flash('Format de date invalide.', 'danger')

    return redirect(url_for('formations.manage'))
    return redirect(url_for('formations.manage'))

@formations_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    
    # Règle UML : Admin Etab peut supprimer (sur son etab), SuperAdmin aussi
    # Règle UML : Admin Etab peut supprimer (sur son etab), SuperAdmin aussi.
    # Coordinateur INTERDIT de supprimer.
    if current_user.role not in [RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.SUPER_ADMIN]:
        abort(403)
        
    # Log (Before Delete, preserving ID or just logging metadata)
    log = ActionLog(user_id=current_user.id, action="SUPPRESSION_FORMATION", target_type="Formation", target_id=formation.id, details=formation.titre)
    db.session.add(log)
        
    db.session.delete(formation)
    db.session.commit()
    flash(f'Formation "{formation.titre}" supprimée.', 'success')
    return redirect(url_for('formations.manage'))  # Or dashboard logic, simpler to manage

@formations_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    
    # Règle : Admin Etab modifie
    if current_user.role not in [RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.SUPER_ADMIN]:
        abort(403)
        
    if request.method == 'POST':
        formation.titre = request.form.get('titre')
        formation.description = request.form.get('description')
        etablissement_id = request.form.get('etablissement_id')
        
        # Admin can change establishment? Usually only SuperAdmin, but let's allow if Admin changes it to another one they own (unlikely) or Super Admin.
        # For simplicity, if Super Admin, allow. If Admin Etab, force strict check or disable.
        if current_user.role == RoleUtilisateur.SUPER_ADMIN and etablissement_id:
             formation.etablissement_id = int(etablissement_id)
        
        # Dates
        date_ouv = request.form.get('date_ouverture')
        date_ferm = request.form.get('date_fermeture')
        
        if date_ouv:
             try:
                 formation.date_ouverture = datetime.strptime(date_ouv, '%Y-%m-%d')
             except ValueError: pass
        if date_ferm:
             try:
                 formation.date_fermeture = datetime.strptime(date_ferm, '%Y-%m-%d')
             except ValueError: pass
             
        db.session.commit()
        flash(f'Formation "{formation.titre}" mise à jour.', 'success')
        return redirect(url_for('formations.manage'))
    
    # GET
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        etablissements = Etablissement.query.filter_by(id=current_user.etablissement_id).all()
    else:
        etablissements = Etablissement.query.all()
        
    return render_template('formations/edit.html', formation=formation, etablissements=etablissements)

@formations_bp.route('/<int:id>/close-inscriptions', methods=['POST'])
@login_required
def close_inscriptions(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    
    # Coordinateur can close too
    
    formation.date_fermeture = datetime.now() # Immédiat
    
    # Log
    log = ActionLog(user_id=current_user.id, action="FERMETURE_INSCRIPTIONS_FORCEE", target_type="Formation", target_id=formation.id)
    db.session.add(log)
    
    db.session.commit()
    flash('Inscriptions fermées immédiatement.', 'warning')
    return redirect(url_for('formations.manage'))

@formations_bp.route('/<int:id>/notify', methods=['GET', 'POST'])
@login_required
def notify_candidates(id):
    formation = Formation.query.get_or_404(id)
    check_permission(formation=formation)
    
    # Get stats for badges
    count_preselect = Inscription.query.filter_by(formation_id=id, etat=EtatInscription.PRESELECTIONNE).count()
    count_waitlist = Inscription.query.filter_by(formation_id=id, etat=EtatInscription.LISTE_ATTENTE).count()
    count_admis = Inscription.query.filter_by(formation_id=id, etat=EtatInscription.ACCEPTE).count()
    
    if request.method == 'POST':
        target_status_name = request.form.get('target_status')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Filter Logic
        query = Inscription.query.filter_by(formation_id=id)
        if target_status_name != 'ALL':
            try:
                target_etat = EtatInscription[target_status_name]
                query = query.filter_by(etat=target_etat)
            except KeyError:
                pass
            
        recipients = query.all()
        
        # Simulation d'envoi
        count = 0
        print(f"--- ENVOI EMAILS MASSE [Semestre 1] ---")
        print(f"Sujet: {subject}")
        for inscr in recipients:
            # Simulation: send_email(inscr.candidat.email, subject, message)
            print(f" -> Envoi à {inscr.candidat.email}")
            count += 1
        print("---------------------------------------")
            
        flash(f'{count} emails ont été placés dans la file d\'envoi.', 'success')
        return redirect(url_for('formations.manage'))
        
    return render_template('admin/notify_candidates.html', formation=formation, 
                          count_preselect=count_preselect, count_waitlist=count_waitlist, count_admis=count_admis)
