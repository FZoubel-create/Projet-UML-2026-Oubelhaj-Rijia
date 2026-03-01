from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = 'dev-key-super-secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cfc_dev.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Upload Configuration
    import os
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Lier les extensions à l'app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Importation des modèles
    from .models import Utilisateur, Formation, Inscription, Etablissement, Dossier

    # User Loader
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))

    # Enregistrement des Blueprints
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.formations import formations_bp
    from .routes.inscriptions import inscriptions_bp
    from .routes.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(formations_bp)
    app.register_blueprint(inscriptions_bp)
    app.register_blueprint(admin_bp)

    # Configuration Scheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    
    # Init Scheduler
    from .scheduler import scheduler
    scheduler.init_app(app)
    
    # Preventing double start in debug mode or re-entrant calls
    if not scheduler.running:
        scheduler.start()
        # Add Job only if starting
        from .scheduler import close_expired_inscriptions
        try:
             # Remove if exists to be safe + add
            try:
                scheduler.remove_job('auto_close_job')
            except: pass
            scheduler.add_job(id='auto_close_job', func=close_expired_inscriptions, trigger='interval', minutes=60)
        except Exception as e:
            print(f"Scheduler Job Error: {e}")

    # Création automatique des tables
    with app.app_context():
        db.create_all()

    return app
