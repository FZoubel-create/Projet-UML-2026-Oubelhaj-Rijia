from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models import Utilisateur, db, RoleUtilisateur
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = Utilisateur.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Email ou mot de passe incorrect.', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        
        user_exists = Utilisateur.query.filter_by(email=email).first()
        if user_exists:
            flash('Cet email est déjà utilisé.', 'warning')
            return redirect(url_for('auth.register'))
            
        new_user = Utilisateur(
            email=email,
            password_hash=generate_password_hash(password),
            nom=nom,
            prenom=prenom,
            role=RoleUtilisateur.CANDIDAT
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Compte créé avec succès ! Connectez-vous.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('main.index'))
