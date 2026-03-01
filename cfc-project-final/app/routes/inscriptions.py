from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import Inscription, Formation, EtatInscription, Dossier, db, RoleUtilisateur, ActionLog
from datetime import datetime
from app.utils.notifications import send_notification

inscriptions_bp = Blueprint('inscriptions', __name__, url_prefix='/inscriptions')

@inscriptions_bp.route('/create/<int:formation_id>', methods=['POST'])
@login_required
def create(formation_id):
    # Règle Métier : Seul un candidat peut s'inscrire
    if current_user.role != RoleUtilisateur.CANDIDAT:
        flash('Seuls les candidats peuvent postuler.', 'warning')
        return redirect(url_for('main.catalogue'))

    formation = Formation.query.get_or_404(formation_id)
    
    # Règle Métier : Vérification Dates & Publication
    if not formation.est_ouverte():
        flash('Les inscriptions sont fermées pour cette formation.', 'danger')
        return redirect(url_for('main.catalogue'))

    # Vérifier doublon
    existing = Inscription.query.filter_by(candidat_id=current_user.id, formation_id=formation.id).first()
    if existing:
        flash('Vous avez déjà commencé une inscription pour cette formation.', 'info')
        return redirect(url_for('inscriptions.mon_dossier', id=existing.id))

    # Création Inscription
    new_inscription = Inscription(
        candidat_id=current_user.id,
        formation_id=formation.id,
        etat=EtatInscription.PREINSCRIT
    )
    
    # Création Dossier Vide associé
    new_dossier = Dossier(inscription=new_inscription) # Lien via backref/uselist logic
    # Note: SQLAlchemy gère l'association si on ajoute à la session
    
    db.session.add(new_inscription)
    db.session.add(new_dossier) # SQLAlchemy might handle cascade, explicit is safer here
    db.session.commit()
    
    # Notification Candidat
    send_notification(
        to_email=current_user.email,
        subject="Confirmation de pré-inscription",
        message=f"Vous êtes pré-inscrit à la formation {formation.titre}. Veuillez compléter votre dossier."
    )
    
    flash('Pré-inscription réussie ! Veuillez compléter votre dossier.', 'success')
    return redirect(url_for('inscriptions.mon_dossier', id=new_inscription.id))

@inscriptions_bp.route('/dossier/<int:id>', methods=['GET', 'POST'])
@login_required
def mon_dossier(id):
    inscription = Inscription.query.get_or_404(id)
    
    # Sécurité : Seul le candidat concerné peut voir son dossier
    if inscription.candidat_id != current_user.id:
        abort(403)
        
    if request.method == 'POST':
        # Upload fichiers
        if 'cv_file' not in request.files:
            flash('Aucun fichier sélectionné', 'warning')
            return redirect(request.url)
            
        cv_file = request.files['cv_file']
        
        if cv_file.filename == '':
            flash('Aucun fichier sélectionné', 'warning')
            return redirect(request.url)
            
        if cv_file:
            from werkzeug.utils import secure_filename
            import os
            from flask import current_app
            
            filename = secure_filename(f"cv_{inscription.id}_{cv_file.filename}")
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            cv_file.save(save_path)
            
            inscription.dossier.cv_filename = filename
            
        # Si tout est rempli (logique simplifiée, on vérifie juste que le CV est là)
        if inscription.dossier.cv_filename: 
            inscription.dossier.est_complet = True
            inscription.etat = EtatInscription.DOSSIER_SOUMIS
            db.session.commit()
            
            # Notif Admin (Simplifié : on notifie log seulement car pas d'email admin direct facile sans query)
            send_notification(
                to_email="admin-etab@cfc.ma", 
                subject="Nouveau dossier soumis",
                message=f"Le candidat {current_user.nom} a soumis son dossier pour {inscription.formation.titre}."
            )
            
            flash('Dossier soumis pour validation !', 'success')
            return redirect(url_for('main.index'))
            
    return render_template('inscriptions/dossier.html', inscription=inscription)

@inscriptions_bp.route('/admin')
@login_required
def admin_dashboard():
    # Règle : Admin/Coord
    # Règle : Admin/Coord
    if current_user.role not in [RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.SUPER_ADMIN, RoleUtilisateur.COORDINATEUR]:
        abort(403)
        
    query = Inscription.query
    
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        # Join requis pour filtrer sur formation.etablissement_id
        query = query.join(Formation).filter(Formation.etablissement_id == current_user.etablissement_id)
        
    elif current_user.role == RoleUtilisateur.COORDINATEUR:
        # Filtrer uniquement sur les formations coordonnées
        query = query.filter(Inscription.formation_id.in_([f.id for f in current_user.formations_coordonnees]))
        
    inscriptions = query.order_by(Inscription.date_creation.desc()).all()
    return render_template('inscriptions/admin_list.html', inscriptions=inscriptions)

@inscriptions_bp.route('/<int:id>/review', methods=['GET', 'POST'])
@login_required
def review_dossier(id):
    """
    Étape de validation : Admin/Coord consulte le dossier.
    Transition : DOSSIER_SOUMIS -> EN_VALIDATION
    """
    inscription = Inscription.query.get_or_404(id)
    
    # 1. Permission Check
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        if inscription.formation.etablissement_id != current_user.etablissement_id: abort(403)
    elif current_user.role == RoleUtilisateur.COORDINATEUR:
        if inscription.formation not in current_user.formations_coordonnees: abort(403)
    elif current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        
    # 2. State Transition (Automatic on view)
    if inscription.etat == EtatInscription.DOSSIER_SOUMIS:
        inscription.etat = EtatInscription.EN_VALIDATION
        log = ActionLog(user_id=current_user.id, action="DOSSIER_OUVERT", target_type="Inscription", target_id=inscription.id)
        db.session.add(log)
        db.session.commit()
        flash('Dossier passé en statut "En cours de validation".', 'info')
        
    return render_template('inscriptions/admin_detail.html', inscription=inscription)

@inscriptions_bp.route('/<int:id>/decision', methods=['POST'])
@login_required
def decision(id):
    if current_user.role not in [RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.SUPER_ADMIN, RoleUtilisateur.COORDINATEUR]:
        abort(403)
        
    inscription = Inscription.query.get_or_404(id)
    
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        if inscription.formation.etablissement_id != current_user.etablissement_id:
            abort(403)
    elif current_user.role == RoleUtilisateur.COORDINATEUR:
        if inscription.formation not in current_user.formations_coordonnees:
            abort(403)

    # STRICT WORKFLOW: Decision allowed only if EN_VALIDATION (meaning it has been reviewed)
    if inscription.etat != EtatInscription.EN_VALIDATION:
        # Tolerance: Allow if already ACCEPTE/REFUSE (updates), but normally strictly sequential.
        # Strict "Cahier des charges": Dossier Soumis -> En Valid -> Decision.
        # If DOSSIER_SOUMIS, they must 'review' first.
        flash('Vous devez d\'abord consulter le dossier (En Validation) avant de décider.', 'warning')
        return redirect(url_for('inscriptions.review_dossier', id=inscription.id))

    action = request.form.get('action') # 'accepter' ou 'refuser'
    decision = request.form.get('action') # 'accepter' ou 'refuser'
    
    if decision == 'accept':
        # Enforce strict transition: Must be EN_VALIDATION to be Accepted (Theoretical, but admin can override)
        inscription.etat = EtatInscription.ACCEPTE
        # Log Action
        from app.models import ActionLog
        log = ActionLog(user_id=current_user.id, action="DECISION_ADMIS", target_type="Inscription", target_id=inscription.id)
        db.session.add(log)
        
        send_notification(inscription.candidat.email, "Félicitations - Admis", f"Votre dossier pour {inscription.formation.titre} a été accepté.")
        
    elif decision == 'refuse':
        inscription.etat = EtatInscription.REFUSE
        
        # Log Action
        from app.models import ActionLog
        log = ActionLog(user_id=current_user.id, action="DECISION_REFUS", target_type="Inscription", target_id=inscription.id)
        db.session.add(log)
        
        send_notification(inscription.candidat.email, "Réponse Candidature", f"Votre dossier pour {inscription.formation.titre} n'a pas été retenu.")
        
    else:
        flash('Décision invalide ou statut non autorisé.', 'danger')
        return redirect(url_for('inscriptions.admin_dashboard'))
        
    db.session.commit()
    flash(f'Candidature mise à jour : {inscription.etat.value}', 'success')
    return redirect(url_for('inscriptions.admin_dashboard'))

@inscriptions_bp.route('/export/<int:formation_id>')
@login_required
def export_csv(formation_id):
    # Droit : Admin Etab (sa formation) ou Super Admin. Coord ? Oui, utile pour eux.
    formation = Formation.query.get_or_404(formation_id)
    
    if current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        if formation.etablissement_id != current_user.etablissement_id: abort(403)
    elif current_user.role == RoleUtilisateur.COORDINATEUR:
        if formation not in current_user.formations_coordonnees: abort(403)
    elif current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        
    import csv
    from io import StringIO
    from flask import make_response
    
    si = StringIO()
    cw = csv.writer(si, delimiter=';') # Excel FR aime le point-virgule
    cw.writerow(['ID', 'Nom', 'Prénom', 'Email', 'Date Candidature', 'Statut'])
    
    inscriptions = Inscription.query.filter_by(formation_id=formation_id).order_by(Inscription.date_creation).all()
    
    for ins in inscriptions:
        cw.writerow([
            ins.id, 
            ins.candidat.nom, 
            ins.candidat.prenom, 
            ins.candidat.email,
            ins.date_creation.strftime('%Y-%m-%d'),
            ins.etat.value
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=export_{formation.code or 'formation'}_{datetime.now().strftime('%Y%m%d')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@inscriptions_bp.route('/dashboard')
@login_required
def dashboard():
    # Redirection des non-candidats vers leur vue appropriée
    if current_user.role != RoleUtilisateur.CANDIDAT:
        if current_user.role in [RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.SUPER_ADMIN]:
            return redirect(url_for('inscriptions.admin_dashboard'))
        return redirect(url_for('main.index'))

    # Récupération des candidatures du candidat
    my_inscriptions = Inscription.query.filter_by(candidat_id=current_user.id).order_by(Inscription.date_creation.desc()).all()
    
    # Statistiques Simples
    total = len(my_inscriptions)
    accepted = sum(1 for i in my_inscriptions if i.etat == EtatInscription.ACCEPTE)
    pending = sum(1 for i in my_inscriptions if i.etat in [EtatInscription.PREINSCRIT, EtatInscription.DOSSIER_SOUMIS, EtatInscription.EN_VALIDATION])
    
    return render_template('inscriptions/dashboard.html', 
                         inscriptions=my_inscriptions,
                         stats={'total': total, 'accepted': accepted, 'pending': pending})
