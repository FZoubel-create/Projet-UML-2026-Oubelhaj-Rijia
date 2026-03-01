from flask import Blueprint, render_template, redirect, url_for, abort, request, flash
from flask_login import login_required, current_user
from app.models import Utilisateur, Formation, Inscription, Etablissement, RoleUtilisateur, EtatInscription, EtatFormation, ParametreGlobal, db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Dispatcher intelligent : redirige chaque rôle vers son tableau de bord spécifique.
    """
    if current_user.role == RoleUtilisateur.SUPER_ADMIN:
        return redirect(url_for('admin.super_dashboard'))
    elif current_user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        return redirect(url_for('admin.etablissement_dashboard'))
    elif current_user.role == RoleUtilisateur.COORDINATEUR:
        return redirect(url_for('admin.coordinateur_dashboard'))
    elif current_user.role == RoleUtilisateur.CANDIDAT:
        return redirect(url_for('inscriptions.dashboard'))
    else:
        abort(403)

@admin_bp.route('/super')
@login_required
def super_dashboard():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        
    # Stats Globales
    stats = {
        'users_count': Utilisateur.query.count(),
        'etablissements_count': Etablissement.query.count(),
        'formations_count': Formation.query.count(),
        'inscriptions_count': Inscription.query.count()
    }
    
    # Listes pour gestion
    users = Utilisateur.query.order_by(Utilisateur.date_creation.desc()).limit(10).all()
    etablissements = Etablissement.query.all()
    
    return render_template('admin/dashboard_super.html', stats=stats, users=users, etablissements=etablissements)

@admin_bp.route('/etablissement')
@login_required
def etablissement_dashboard():
    if current_user.role != RoleUtilisateur.ADMIN_ETABLISSEMENT:
        abort(403)
    
    # Filtrage strict par Établissement
    my_etab_id = current_user.etablissement_id
    
    formations = Formation.query.filter_by(etablissement_id=my_etab_id).all()
    
    # Inscriptions liées aux formations de l'établissement
    inscriptions_pending = Inscription.query.join(Formation).filter(
        Formation.etablissement_id == my_etab_id,
        Inscription.etat.in_([EtatInscription.DOSSIER_SOUMIS, EtatInscription.EN_VALIDATION])
    ).all()
    
    stats = {
        'formations_count': len(formations),
        'pending_count': len(inscriptions_pending),
        'admitted_count': Inscription.query.join(Formation).filter(
            Formation.etablissement_id == my_etab_id,
            Inscription.etat == EtatInscription.ACCEPTE
        ).count()
    }
    
    return render_template('admin/dashboard_etab.html', 
                         formations=formations, 
                         inscriptions_pending=inscriptions_pending,
                         stats=stats,
                         etablissement=Etablissement.query.get(my_etab_id))

@admin_bp.route('/coordination')
@login_required
def coordinateur_dashboard():
    if current_user.role != RoleUtilisateur.COORDINATEUR:
        abort(403)
        
    # Formations assignées
    my_formations = current_user.formations_coordonnees
    
    return render_template('admin/dashboard_coord.html', formations=my_formations)

# --- Management Routes (Super Admin) ---

@admin_bp.route('/etablissements/new', methods=['GET', 'POST'])
@login_required
def create_etablissement():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        

    
    if request.method == 'POST':
        nom = request.form.get('nom')
        code = request.form.get('code')
        ville = request.form.get('ville')
        
        if not nom or not code:
            flash('Nom et Code requis.', 'danger')
        else:
            new_etab = Etablissement(nom=nom, code=code, ville=ville)
            db.session.add(new_etab)
            db.session.commit()
            flash(f'Établissement {code} créé avec succès.', 'success')
            return redirect(url_for('admin.super_dashboard'))
            
    return render_template('admin/etab_form.html')

@admin_bp.route('/users')
@login_required
def manage_users():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
    
    users = Utilisateur.query.order_by(Utilisateur.role, Utilisateur.nom).all()
    return render_template('admin/users_list.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        

    from werkzeug.security import generate_password_hash
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        role_name = request.form.get('role')
        etablissement_id = request.form.get('etablissement_id')
        
        if Utilisateur.query.filter_by(email=email).first():
            flash('Cet email existe déjà.', 'danger')
        else:
            # Conversion du rôle string -> Enum
            try:
                role = RoleUtilisateur[role_name]
            except KeyError:
                flash('Rôle invalide.', 'danger')
                return redirect(request.url)

            new_user = Utilisateur(
                email=email,
                password_hash=generate_password_hash(password),
                nom=nom,
                prenom=prenom,
                role=role
            )
            
            # Si Admin Etab, on lie l'établissement
            if role == RoleUtilisateur.ADMIN_ETABLISSEMENT and etablissement_id:
                new_user.etablissement_id = int(etablissement_id)
                
            db.session.add(new_user)
            db.session.commit()
            flash(f'Utilisateur {email} ({role_name}) créé.', 'success')
            return redirect(url_for('admin.manage_users'))

    etablissements = Etablissement.query.all()
    # On passe l'enum RoleUtilisateur au template pour générer les options
    roles = [r.name for r in RoleUtilisateur]
    return render_template('admin/user_form.html', etablissements=etablissements, roles=roles)


@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        
    user = Utilisateur.query.get_or_404(id)

    from werkzeug.security import generate_password_hash
    
    if request.method == 'POST':
        user.nom = request.form.get('nom')
        user.prenom = request.form.get('prenom')
        user.email = request.form.get('email')
        role_name = request.form.get('role')
        etablissement_id = request.form.get('etablissement_id')
        
        # Update Role
        try:
            user.role = RoleUtilisateur[role_name]
        except KeyError:
            pass # Keep old role if error
            
        # Update Etab link
        if user.role == RoleUtilisateur.ADMIN_ETABLISSEMENT and etablissement_id:
            user.etablissement_id = int(etablissement_id)
        else:
            user.etablissement_id = None
            
        password = request.form.get('password')
        if password:
            user.password_hash = generate_password_hash(password)
            
        db.session.commit()
        flash(f'Utilisateur {user.email} mis à jour.', 'success')
        return redirect(url_for('admin.manage_users'))
        
    etablissements = Etablissement.query.all()
    roles = [r.name for r in RoleUtilisateur]
    return render_template('admin/user_edit.html', user=user, etablissements=etablissements, roles=roles)

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
    user = Utilisateur.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Impossible de se supprimer soi-même.', 'danger')
        return redirect(url_for('admin.manage_users'))
        
    db.session.delete(user)
    db.session.commit()
    flash('Utilisateur supprimé.', 'success')
    return redirect(url_for('admin.manage_users'))

# --- Establishment CRUD ---

@admin_bp.route('/etablissements')
@login_required
def manage_etablissements():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
    etablissements = Etablissement.query.all()
    return render_template('admin/etablissements_list.html', etablissements=etablissements)

@admin_bp.route('/etablissements/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_etablissement(id):
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
    etab = Etablissement.query.get_or_404(id)
    if request.method == 'POST':
        etab.nom = request.form.get('nom')
        etab.code = request.form.get('code')
        etab.ville = request.form.get('ville')
        db.session.commit()
        flash('Établissement mis à jour.', 'success')
        return redirect(url_for('admin.manage_etablissements'))
    return render_template('admin/etab_edit.html', etablissement=etab)

@admin_bp.route('/etablissements/<int:id>/delete', methods=['POST'])
@login_required
def delete_etablissement(id):
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
    etab = Etablissement.query.get_or_404(id)
    # Check if has users or formations? For now, raw delete (cascade might fail if not configured, but OK for dev)
    try:
        db.session.delete(etab)
        db.session.commit()
        flash('Établissement supprimé.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Impossible de supprimer : des formations ou utilisateurs y sont liés.', 'danger')
    return redirect(url_for('admin.manage_etablissements'))

# --- Global Inscriptions ---

@admin_bp.route('/inscriptions/all')
@login_required
def all_inscriptions():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
    inscriptions = Inscription.query.order_by(Inscription.date_creation.desc()).all()
    return render_template('admin/inscriptions_global.html', inscriptions=inscriptions)

@admin_bp.route('/parametres', methods=['GET', 'POST'])
@login_required
def manage_parametres():
    if current_user.role != RoleUtilisateur.SUPER_ADMIN:
        abort(403)
        
    if request.method == 'POST':
        key = request.form.get('key')
        value = request.form.get('value')
        description = request.form.get('description')
        
        # Simple Upsert
        param = ParametreGlobal.query.get(key)
        if param:
            param.value = value
            if description: param.description = description
        else:
            param = ParametreGlobal(key=key, value=value, description=description)
            db.session.add(param)
            
        db.session.commit()
        flash(f'Paramètre {key} mis à jour.', 'success')
        
    params = ParametreGlobal.query.all()
    return render_template('admin/parametres.html', params=params)
