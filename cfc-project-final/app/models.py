from app import db
from flask_login import UserMixin
from datetime import datetime
import enum

# --- ENUMERATIONS (Comme dans l'UML) ---

class RoleUtilisateur(enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN_ETABLISSEMENT = "ADMIN_ETABLISSEMENT"
    COORDINATEUR = "COORDINATEUR"
    CANDIDAT = "CANDIDAT"

class EtatFormation(enum.Enum):
    BROUILLON = "BROUILLON"
    PUBLIEE = "PUBLIEE"
    ARCHIVEE = "ARCHIVEE"

class EtatInscription(enum.Enum):
    PREINSCRIT = "Pré-inscrit"  # Juste le compte créé ou intent
    DOSSIER_SOUMIS = "Dossier Soumis" # Dossier envoyé
    EN_VALIDATION = "En cours de validation" # Admin regarde
    ACCEPTE = "Admis"
    REFUSE = "Refusé"
    INSCRIT = "INSCRIT"

# --- MODELES (TABLES) ---

class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    role = db.Column(db.Enum(RoleUtilisateur), default=RoleUtilisateur.CANDIDAT)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation Admin d'Etablissement -> Etablissement (1..* <-> 1)
    # Un admin appartient à un seul établissement (simplification UML)
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=True)
    
    # Relation Coordinateur -> Formations (0..* <-> 0..*)
    # Table d'association définie plus bas
    formations_coordonnees = db.relationship('Formation', secondary='coordination', backref=db.backref('coordinateurs', lazy=True))

    def __repr__(self):
        return f'<User {self.email} - {self.role.value}>'
    
# Table d'association pour Coordinateur <-> Formation
coordination = db.Table('coordination',
    db.Column('utilisateur_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('formation_id', db.Integer, db.ForeignKey('formations.id'), primary_key=True)
)


class Etablissement(db.Model):
    __tablename__ = 'etablissements'
    
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    ville = db.Column(db.String(100))
    image = db.Column(db.String(100), default="default_etab.png")
    
    # Relation : Un Etablissement a plusieurs Formations
    formations = db.relationship('Formation', backref='etablissement', lazy=True)


class Formation(db.Model):
    __tablename__ = 'formations'
    
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    categorie = db.Column(db.String(50), default="Divers")
    image = db.Column(db.String(100), default="default_formation.png")
    
    # Clé étrangère vers Etablissement
    etablissement_id = db.Column(db.Integer, db.ForeignKey('etablissements.id'), nullable=False)
    
    # Gestion du cycle de vie
    etat = db.Column(db.Enum(EtatFormation), default=EtatFormation.BROUILLON)
    
    # Dates d'ouverture/fermeture des INSCRIPTIONS
    date_ouverture = db.Column(db.DateTime, nullable=True)
    date_fermeture = db.Column(db.DateTime, nullable=True)
    
    inscriptions = db.relationship('Inscription', backref='formation', lazy=True)

    def est_ouverte(self):
        """Traduction directe de la règle métier UML"""
        now = datetime.utcnow()
        if self.etat != EtatFormation.PUBLIEE:
            return False
        if not self.date_ouverture or not self.date_fermeture:
            return False
        return self.date_ouverture <= now <= self.date_fermeture


class Inscription(db.Model):
    __tablename__ = 'inscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    etat = db.Column(db.Enum(EtatInscription), default=EtatInscription.PREINSCRIT)
    
    # Relations (Qui s'inscrit ? À quoi ?)
    candidat_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    formation_id = db.Column(db.Integer, db.ForeignKey('formations.id'), nullable=False)
    
    # Relation Dossier (One-to-One)
    dossier = db.relationship('Dossier', backref='inscription', uselist=False, cascade="all, delete-orphan")
    
    candidat = db.relationship('Utilisateur', backref='mes_inscriptions')


class Dossier(db.Model):
    __tablename__ = 'dossiers'
    
    id = db.Column(db.Integer, primary_key=True)
    inscription_id = db.Column(db.Integer, db.ForeignKey('inscriptions.id'), unique=True, nullable=False)
    
    # Chemins vers les fichiers (Pas les fichiers eux-mêmes en DB pour perf)
    cv_filename = db.Column(db.String(255))
    lettre_filename = db.Column(db.String(255))
    diplome_filename = db.Column(db.String(255))
    
    est_complet = db.Column(db.Boolean, default=False)

class ActionLog(db.Model):
    """
    Journal d'audit pour la traçabilité des actions critiques (Sécurité & Conformité)
    """
    __tablename__ = 'action_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Null if system
    action = db.Column(db.String(100), nullable=False) # ex: "VALIDATION_DOSSIER"
    target_type = db.Column(db.String(50)) # ex: "Inscription"
    target_id = db.Column(db.Integer)
    details = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('Utilisateur', backref=db.backref('logs', lazy=True))

class ParametreGlobal(db.Model):
    """
    Paramètres globaux du système (Année universitaire, etc.)
    Géré uniquement par le Super Admin.
    """
    __tablename__ = 'parametres'
    
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255))
    description = db.Column(db.String(255))
